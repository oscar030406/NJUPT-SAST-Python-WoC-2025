import csv
import logging
import os
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')

# Dangdang bestseller books - Selenium headless scraper

BASE_URL = 'http://bang.dangdang.com/books/bestsellers/01.00.00.00.00.00-recent7-0-0-1-{}'
MAX_PAGES = 5
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
CSV_FILE = os.path.join(DATA_DIR, 'dangdang_selenium.csv')
CSV_FIELDS = ['rank', 'title', 'author', 'publisher', 'date',
              'price', 'original_price', 'discount', 'comments',
              'recommendation', 'url']


def _safe_float(text):
    try:
        return float(text) if text else 0.0
    except ValueError:
        return 0.0


def _safe_text(element, css, attr=None):
    try:
        el = element.find_element(By.CSS_SELECTOR, css)
        if attr:
            return el.get_attribute(attr) or el.text.strip()
        return el.text.strip()
    except Exception:
        return ''


def get_browser():
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--blink-settings=imagesEnabled=false')
    opts.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 Chrome/122.0.0.0')
    opts.page_load_strategy = 'eager'
    browser = webdriver.Chrome(options=opts)
    browser.implicitly_wait(5)
    return browser


def scrape_index(browser, page):
    url = BASE_URL.format(page)
    logging.info('scraping %s...', url)
    browser.get(url)


def parse_index(browser):
    items = browser.find_elements(By.CSS_SELECTOR, 'ul.bang_list li')
    if not items:
        return

    for li in items:
        try:
            # rank
            rank_text = _safe_text(li, 'div[class^=list_num]')
            rank = int(re.sub(r'\D', '', rank_text) or 0)

            # title and link
            title = _safe_text(li, 'div.name a', attr='title')
            url = _safe_text(li, 'div.name a', attr='href')

            # publisher info
            pub_divs = li.find_elements(By.CSS_SELECTOR, 'div.publisher_info')
            author = pub_date = publisher = ''
            if pub_divs:
                author = _safe_text(pub_divs[0], 'a', attr='title')
                if not author:
                    author = pub_divs[0].text.strip()
            if len(pub_divs) >= 2:
                pub_date = _safe_text(pub_divs[1], 'span')
                publisher = _safe_text(pub_divs[1], 'a')

            # rating info
            ct = _safe_text(li, 'div.star a')
            m = re.search(r'(\d+)', ct)
            comments = int(m.group(1)) if m else 0
            recommendation = _safe_text(li, 'span.tuijian')

            # price info
            price = _safe_float(_safe_text(li, 'span.price_n').lstrip('¥￥'))
            original_price = _safe_float(_safe_text(li, 'span.price_r').lstrip('¥￥'))
            discount = _safe_text(li, 'span.price_s')

            yield {
                'rank': rank, 'title': title, 'author': author,
                'publisher': publisher, 'date': pub_date,
                'price': price, 'original_price': original_price,
                'discount': discount, 'comments': comments,
                'recommendation': recommendation, 'url': url,
            }
        except Exception:
            continue


def save_data(books):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(books)
    logging.info('saved %d records -> %s', len(books), CSV_FILE)


def main(browser, page):
    scrape_index(browser, page)
    books = list(parse_index(browser))
    logging.info('page %d: got %d books', page, len(books))
    return books


if __name__ == '__main__':
    logging.info('Dangdang bestseller scrape, %d pages', MAX_PAGES)
    t_start = time.time()
    browser = get_browser()
    all_books = []
    try:
        for page in range(1, MAX_PAGES + 1):
            books = main(browser, page)
            all_books.extend(books)
    finally:
        browser.quit()
    elapsed = time.time() - t_start
    logging.info('Selenium scraping done: %d books, elapsed %.2fs', len(all_books), elapsed)
    save_data(all_books[:100])
