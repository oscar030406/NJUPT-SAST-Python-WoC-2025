import json
import logging
import time
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')
#%(asctime)s：时间
#%(levelname)s：日志级别，比如 DEBUG、INFO、WARNING、ERROR
#%(message)s：日志内容

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
RESULTS_DIR = Path(__file__).resolve().parent.parent / 'data' / 'douban_top250'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# 复用 HTTP 会话和底层连接，减少重复建立 TCP/TLS 连接的开销
session = requests.Session()
session.headers.update(HEADERS)


def scrape_page(url, params=None):
    logging.debug('开始请求接口：%s', url)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, params=params, timeout=TIMEOUT)
            if response.status_code == 200:
                return response.json()
            logging.warning('第 %d/%d 次请求返回状态码 %s，接口：%s',
                            attempt, MAX_RETRIES, response.status_code, url)
        except requests.RequestException:
            logging.warning('第 %d/%d 次请求失败，接口：%s',
                            attempt, MAX_RETRIES, url, exc_info=True)
        if attempt < MAX_RETRIES:
            time.sleep(0.5 * attempt) 
    logging.error('接口连续失败 %d 次：%s', MAX_RETRIES, url)
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
   # 将 Windows 文件名中不允许的字符替换为下划线。
    safe_name = ''.join('_' if char in '\\/:*?"<>|' else char for char in name)
    data_path = RESULTS_DIR / f'{safe_name}.json'
    with data_path.open('w', encoding='utf-8') as f:
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
    logging.info('串行爬取完成，共 %d 页，耗时 %.2f 秒',
                 TOTAL_PAGE, elapsed)
