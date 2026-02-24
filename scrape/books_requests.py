import csv
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')

BASE_URL = 'http://bang.dangdang.com/books/bestsellers/01.00.00.00.00.00-recent7-0-0-1-{}'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36'
}
MAX_PAGES = 5
WORKERS = 5
MAX_RETRIES = 3
DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
CSV_FILE = DATA_DIR / 'dangdang_requests.csv'
CSV_FIELDS = ['rank', 'title', 'author', 'publisher', 'date',
              'price', 'original_price', 'discount', 'comments',
              'recommendation', 'url']


def _safe_float(text):
    try:
        return float(text) if text else 0.0
    except ValueError:
        return 0.0


# 复用 HTTP 会话和底层连接，减少重复建立 TCP/TLS 连接的开销
session = requests.Session()
session.headers.update(HEADERS)


def scrape_page(url):
    logging.info('开始抓取页面：%s', url)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                response.encoding = 'gb2312'
                return response.text
            logging.warning('第 %d/%d 次请求返回状态码 %s，页面：%s',
                            attempt, MAX_RETRIES, response.status_code, url)
        except requests.RequestException:
            logging.warning('第 %d/%d 次抓取失败，页面：%s',
                            attempt, MAX_RETRIES, url, exc_info=True)
        if attempt < MAX_RETRIES:
            time.sleep(0.5 * attempt)
    logging.error('页面抓取连续失败 %d 次：%s', MAX_RETRIES, url)
    return None


def scrape_index(page):
    url = BASE_URL.format(page)
    return scrape_page(url)


def parse_index(html):
    soup = BeautifulSoup(html, 'lxml')
    bang = soup.find('ul', class_='bang_list')
    if not bang:
        return

    items = bang.find_all('li')
    for li in items:
        # rank
        num_div = li.find('div', class_=re.compile(r'list_num'))
        rank_text = num_div.get_text(strip=True) if num_div else '0'
        rank = int(re.sub(r'\D', '', rank_text) or 0)

        # title and link
        name_div = li.find('div', class_='name')
        a_tag = name_div.find('a') if name_div else None
        title = a_tag.get('title', a_tag.get_text(strip=True)) if a_tag else ''
        url = a_tag.get('href', '') if a_tag else ''

        # publisher
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

        yield {
            'rank': rank, 'title': title, 'author': author,
            'publisher': publisher, 'date': pub_date,
            'price': price, 'original_price': original_price,
            'discount': discount, 'comments': comments,
            'recommendation': recommendation, 'url': url,
        }


def save_data(books):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_FILE.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(books)
    logging.info('已保存 %d 条记录到 %s', len(books), CSV_FILE)


def main(page):
    index_html = scrape_index(page)
    if not index_html:
        return []
    books = list(parse_index(index_html))
    logging.info('第 %d 页抓取到 %d 本书', page, len(books))
    return books


if __name__ == '__main__':
    logging.info('开始抓取，共 %d 页', MAX_PAGES)
    t_start = time.time()
    page_books = {}
    # 创建线程池，线程数不超过设定值，也不超过实际要抓取的页数。
    with ThreadPoolExecutor(max_workers=min(WORKERS, MAX_PAGES)) as executor:
        futures = {
            # 把 main(page) 交给线程池执行，返回 future 句柄。
            executor.submit(main, page): page
            for page in range(1, MAX_PAGES + 1)
        }
        # 按任务实际完成的先后顺序依次取回结果，而不是按页码顺序等待。
        for future in as_completed(futures):
            page = futures[future]
            page_books[page] = future.result()

    all_books = []
    for page in range(1, MAX_PAGES + 1):
        all_books.extend(page_books.get(page, []))
    elapsed = time.time() - t_start
    logging.info('抓取完成，共 %d 本书，耗时 %.2f 秒', len(all_books), elapsed)
    save_data(all_books)
