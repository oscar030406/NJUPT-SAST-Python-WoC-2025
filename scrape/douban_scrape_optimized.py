import asyncio
import csv
import logging
import os
import re
import time
import aiohttp
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')

# Douban Top250 optimized scraper - aiohttp concurrent version

BASE_URL = 'https://movie.douban.com/top250'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://movie.douban.com/',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}
CONCURRENCY = 5  
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CSV_FILE = os.path.join(DATA_DIR, 'douban_movies_optimized.csv')
CSV_FIELDS = ['rank', 'title', 'director', 'actors', 'year', 'country',
              'genre', 'rating', 'votes', 'quote', 'url']

DIRECTOR_PATTERN = re.compile(r'导演:\s*(.+?)(?:\s+主演:|$)')
ACTORS_PATTERN = re.compile(r'主演:\s*(.+)')


def parse_item(item):
    hd = item.find('div', class_='hd')
    bd = item.find('div', class_='bd')

    pic = item.find('div', class_='pic')
    rank_em = pic.find('em') if pic else None
    rank = rank_em.get_text(strip=True) if rank_em else ''

    link = hd.find('a') if hd else None
    url = link['href'] if link else ''
    title_span = hd.find('span', class_='title') if hd else None
    title = title_span.get_text(strip=True) if title_span else ''

    info_p = bd.find('p') if bd else None
    info_text = info_p.get_text('\n', strip=True) if info_p else ''
    lines = [l.strip() for l in info_text.split('\n') if l.strip()]

    director = actors = year = country = genre = None
    if lines:
        first = lines[0]
        m = re.search(DIRECTOR_PATTERN, first)
        if m:
            director = m.group(1).strip().rstrip('...')
        m2 = re.search(ACTORS_PATTERN, first)
        if m2:
            actors = m2.group(1).strip().rstrip('...')

    if len(lines) > 1:
        parts = [p.strip() for p in lines[-1].split('/')]
        if parts:
            year = re.sub(r'[^\d]', '', parts[0])
        if len(parts) > 1:
            country = parts[1].strip()
        if len(parts) > 2:
            genre = parts[2].strip()

    star_div = bd.find('div', class_='star') if bd else None
    rating_span = star_div.find('span', class_='rating_num') if star_div else None
    rating = float(rating_span.get_text(strip=True)) if rating_span else None

    votes = None
    if star_div:
        for span in star_div.find_all('span'):
            if '人评价' in span.get_text():
                votes = span.get_text(strip=True).replace('人评价', '')
                break

    quote_span = bd.find('span', class_='inq') if bd else None
    quote = quote_span.get_text(strip=True) if quote_span else None

    return {
        'rank': rank, 'title': title, 'director': director,
        'actors': actors, 'year': year, 'country': country,
        'genre': genre, 'rating': rating, 'votes': votes,
        'quote': quote, 'url': url
    }


async def fetch_page(session, start, sem):
    """Fetch a single page asynchronously."""
    url = f'{BASE_URL}?start={start}'
    async with sem:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                html = await resp.text()
                soup = BeautifulSoup(html, 'lxml')
                items = soup.find_all('div', class_='item')
                logging.info('[async] start=%s fetched %d items', start, len(items))
                await asyncio.sleep(0.15)
                return [parse_item(it) for it in items]
        except Exception:
            logging.error('[async] start=%s request failed', start, exc_info=True)
            return []


async def scrape_all():
    """Concurrently scrape all 10 pages."""
    sem = asyncio.Semaphore(CONCURRENCY)
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tasks = [fetch_page(session, start, sem) for start in range(0, 250, 25)]
        results = await asyncio.gather(*tasks)
    movies = []
    for page_movies in results:
        movies.extend(page_movies)
    movies.sort(key=lambda x: int(x['rank']) if x['rank'].isdigit() else 999)
    return movies


def save_csv(movies, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(movies)
    logging.info('saved %d records -> %s', len(movies), filepath)


async def main():
    logging.info('Douban Top250 optimized scraper starting...')
    t_start = time.time()
    movies = await scrape_all()
    async_elapsed = time.time() - t_start
    logging.info('concurrent scraping done: %d movies, elapsed %.2fs', len(movies), async_elapsed)
    save_csv(movies, CSV_FILE)


if __name__ == '__main__':
    asyncio.run(main())
