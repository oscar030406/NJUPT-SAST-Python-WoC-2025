import asyncio
import csv
import logging
import os
import time
import aiohttp

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')

BASE_URL = 'https://m.douban.com/rexxar/api/v2/subject_collection/movie_top250/items'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.douban.com/subject_collection/movie_top250',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept': 'application/json, text/plain, */*',
}
CONCURRENCY = 12
PAGE_SIZE = 25
MAX_RETRIES = 3
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CSV_FILE = os.path.join(DATA_DIR, 'douban_movies_optimized.csv')
CSV_FIELDS = ['rank', 'title', 'director', 'actors', 'year', 'country',
              'genre', 'rating', 'votes', 'quote', 'url']


def parse_item(item):
    subtitle = item.get('card_subtitle', '')
    parts = [part.strip() for part in subtitle.split('/') if part.strip()]
    rating_info = item.get('rating') or {}

    director = parts[3] if len(parts) > 3 else ''
    actors = parts[4] if len(parts) > 4 else ''
    year = parts[0] if len(parts) > 0 else ''
    country = parts[1] if len(parts) > 1 else ''
    genre = parts[2] if len(parts) > 2 else ''

    return {
        'rank': str(item.get('rank', '')),
        'title': item.get('title', ''),
        'director': director,
        'actors': actors,
        'year': year,
        'country': country,
        'genre': genre,
        'rating': rating_info.get('value'),
        'votes': rating_info.get('count'),
        'quote': item.get('description', ''),
        'url': item.get('url', '')
    }


async def fetch_page(session, start, sem):
    async with sem:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with session.get(
                    BASE_URL,
                    params={'start': start, 'count': PAGE_SIZE},
                    timeout=aiohttp.ClientTimeout(total=6)
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    items = data.get('subject_collection_items') or []
                    logging.debug('start=%s fetched %d items', start, len(items))
                    return [parse_item(item) for item in items]
            except Exception:
                logging.warning('attempt %d/%d: start=%s failed',
                                attempt, MAX_RETRIES, start, exc_info=True)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(0.3 * attempt)
        logging.error('all %d attempts failed for start=%s', MAX_RETRIES, start)
        return []


async def scrape_all():
    # 信号量：限制同时运行的并发协程数，防止过多请求触发限流
    sem = asyncio.Semaphore(CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=6)
    # TCP 连接池：全局及单主机最大连接数均为 CONCURRENCY，DNS 缓存 300 秒
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, limit_per_host=CONCURRENCY, ttl_dns_cache=300)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout, connector=connector) as session:
        tasks = [fetch_page(session, start, sem) for start in range(0, 250, PAGE_SIZE)]
        # 并发调度所有任务，等待全部完成
        results = await asyncio.gather(*tasks)
    movies = []
    for page_movies in results:
        movies.extend(page_movies)
    # 按 rank 字段升序排序；非纯数字的异常值排到末尾
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
    t_start = time.perf_counter()
    movies = await scrape_all()
    async_elapsed = time.perf_counter() - t_start
    logging.info('concurrent scraping done: %d movies, elapsed %.2fs', len(movies), async_elapsed)
    save_csv(movies, CSV_FILE)


if __name__ == '__main__':
    asyncio.run(main())
