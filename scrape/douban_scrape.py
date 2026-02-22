import json
import logging
import os
import time

import requests

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')

BASE_URL = 'https://m.douban.com/rexxar/api/v2/subject_collection/movie_top250/items'
TOTAL_PAGE = 10
PAGE_SIZE = 25
TIMEOUT = 8
MAX_RETRIES = 3
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.douban.com/subject_collection/movie_top250',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept': 'application/json, text/plain, */*',
}

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'douban_top250')
os.makedirs(RESULTS_DIR, exist_ok=True)

# 复用 TCP 连接，避免每次请求都重新进行 DNS 查询和 TCP/TLS 握手
session = requests.Session()
session.headers.update(HEADERS)


def scrape_page(url, params=None):
    logging.debug('scraping %s...', url)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, params=params, timeout=TIMEOUT)
            if response.status_code == 200:
                return response.json()
            logging.warning('attempt %d/%d: status %s for %s',
                            attempt, MAX_RETRIES, response.status_code, url)
        except requests.RequestException:
            logging.warning('attempt %d/%d: request failed for %s',
                            attempt, MAX_RETRIES, url, exc_info=True)
        if attempt < MAX_RETRIES:
            time.sleep(0.5 * attempt)  # 指数退避，避免连续失败时频繁请求
    logging.error('all %d attempts failed for %s', MAX_RETRIES, url)
    return None


def scrape_index(page):
    start = (page - 1) * PAGE_SIZE
    return scrape_page(BASE_URL, params={'start': start, 'count': PAGE_SIZE})


def parse_index(data):
    items = data.get('subject_collection_items') or []
    if not items:
        return

    for item in items:
        subtitle = item.get('card_subtitle', '')
        parts = [part.strip() for part in subtitle.split('/') if part.strip()]
        rating_info = item.get('rating') or {}
        year = parts[0] if len(parts) > 0 else ''
        country = parts[1] if len(parts) > 1 else ''
        genre = parts[2] if len(parts) > 2 else ''
        director = parts[3] if len(parts) > 3 else ''
        actors = parts[4] if len(parts) > 4 else ''

        yield {
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
            'url': item.get('url', ''),
        }


def save_data(data):
    name = data.get('title') or data.get('rank') or 'movie'
    # Replace invalid Windows filename characters.
    safe_name = ''.join('_' if char in '\\/:*?"<>|' else char for char in name)
    data_path = f'{RESULTS_DIR}/{safe_name}.json'
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main(page):
    index_data = scrape_index(page)
    if not index_data:
        return
    movies = parse_index(index_data)
    for movie in movies:
        save_data(movie)


if __name__ == '__main__':
    t_start = time.perf_counter()
    for page in range(1, TOTAL_PAGE + 1):
        main(page)
    elapsed = time.perf_counter() - t_start
    logging.info('serial scraping done: %d pages, elapsed %.2fs',
                 TOTAL_PAGE, elapsed)
