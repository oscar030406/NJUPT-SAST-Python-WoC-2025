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

# Dangdang bestseller books - async scraper (aiohttp + bs4)

BASE_URL = 'http://bang.dangdang.com/books/bestsellers/01.00.00.00.00.00-recent7-0-0-1-{}'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36'
}
MAX_PAGES = 5
CONCURRENCY = 5
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CSV_FILE = os.path.join(DATA_DIR, 'dangdang_aiohttp.csv')
CSV_FIELDS = ['rank', 'title', 'author', 'publisher', 'date',
              'price', 'original_price', 'discount', 'comments',
              'recommendation', 'url']



def _safe_float(text):
    try:
        return float(text) if text else 0.0
    except ValueError:
        return 0.0


def parse_item(li):
    # rank
    num_div = li.find('div', class_=re.compile(r'list_num'))
    rank_text = num_div.get_text(strip=True) if num_div else '0'
    rank = int(re.sub(r'\D', '', rank_text) or 0)

    # title and link
    name_div = li.find('div', class_='name')
    a_tag = name_div.find('a') if name_div else None
    title = a_tag.get('title', a_tag.get_text(strip=True)) if a_tag else ''
    url = a_tag.get('href', '') if a_tag else ''

    # publisher info
    pub_divs = li.find_all('div', class_='publisher_info')
    author = pub_date = publisher = ''
    if pub_divs:
        first_a = pub_divs[0].find('a')
        if first_a and first_a.has_attr('title'):
            author = first_a['title']
        else:
            author = pub_divs[0].get_text(strip=True)
    if len(pub_divs) >= 2:
        span = pub_divs[1].find('span')
        pub_date = span.get_text(strip=True) if span else ''
        pa = pub_divs[1].find('a')
        publisher = pa.get_text(strip=True) if pa else ''

    # rating info
    star_div = li.find('div', class_='star')
    comments = 0
    recommendation = ''
    if star_div:
        comment_a = star_div.find('a')
        if comment_a:
            m = re.search(r'(\d+)', comment_a.get_text(strip=True))
            comments = int(m.group(1)) if m else 0
        tj = star_div.find('span', class_='tuijian')
        recommendation = tj.get_text(strip=True) if tj else ''

    # price info
    price_div = li.find('div', class_='price')
    price = original_price = 0.0
    discount = ''
    if price_div:
        pn = price_div.find('span', class_='price_n')
        price = _safe_float(pn.get_text(strip=True).lstrip('¥￥')) if pn else 0.0
        pr = price_div.find('span', class_='price_r')
        original_price = _safe_float(pr.get_text(strip=True).lstrip('¥￥')) if pr else 0.0
        ps = price_div.find('span', class_='price_s')
        discount = ps.get_text(strip=True) if ps else ''

    return {
        'rank': rank, 'title': title, 'author': author,
        'publisher': publisher, 'date': pub_date,
        'price': price, 'original_price': original_price,
        'discount': discount, 'comments': comments,
        'recommendation': recommendation, 'url': url,
    }


async def fetch_page(session, page, sem):
    url = BASE_URL.format(page)
    async with sem:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                resp.raise_for_status()
                raw = await resp.read()
                html = raw.decode('gb2312', errors='replace')
                soup = BeautifulSoup(html, 'lxml')
                bang = soup.find('ul', class_='bang_list')
                items = bang.find_all('li') if bang else []
                books = [parse_item(li) for li in items]
                logging.info('page=%s fetched %d books', page, len(books))
                await asyncio.sleep(0.15)
                return books
        except Exception:
            logging.error('page=%s request failed', page, exc_info=True)
            return []


async def scrape_all():
    sem = asyncio.Semaphore(CONCURRENCY)
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tasks = [fetch_page(session, p, sem) for p in range(1, MAX_PAGES + 1)]
        results = await asyncio.gather(*tasks)
    books = []
    for page_books in results:
        books.extend(page_books)
    return books[:100]


def save_csv(books, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(books)
    logging.info('saved %d records -> %s', len(books), filepath)


async def main():
    logging.info('Dangdang bestseller async scrape, %d pages', MAX_PAGES)
    t_start = time.time()
    books = await scrape_all()
    elapsed = time.time() - t_start
    logging.info('async scraping done: %d books, elapsed %.2fs', len(books), elapsed)
    save_csv(books, CSV_FILE)


if __name__ == '__main__':
    asyncio.run(main())
