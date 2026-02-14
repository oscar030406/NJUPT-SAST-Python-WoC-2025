import json
import os
import re
import time
import logging
from os import makedirs
from os.path import exists

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')

BASE_URL = 'https://movie.douban.com/top250'
TOTAL_PAGE = 10
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://movie.douban.com/',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'douban_top250')
exists(RESULTS_DIR) or makedirs(RESULTS_DIR)


def scrape_page(url, params=None):
    logging.info('scraping %s...', url)
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.text
        logging.error('get invalid status code %s while scraping %s',
                      response.status_code, url)
    except requests.RequestException:
        logging.error('error occurred while scraping %s', url, exc_info=True)


def scrape_index(page):
    start = (page - 1) * 25
    return scrape_page(BASE_URL, params={'start': start})


def parse_index(html):
    """Parse Douban Top250 page HTML and extract movie info.

    Args:
        html: HTML source of a Douban Top250 listing page.

    Yields:
        dict with keys: rank, title, director, actors, year,
        country, genre, rating, votes, quote, url.
    """
    soup = BeautifulSoup(html, 'lxml')
    items = soup.find_all('div', class_='item')
    if not items:
        return 
    director_pattern = re.compile(r'导演:\s*(.+?)(?:\s+主演:|$)')
    actors_pattern = re.compile(r'主演:\s*(.+)')
    for item in items:
        hd = item.find('div', class_='hd')
        bd = item.find('div', class_='bd')
        pic = item.find('div', class_='pic')

        rank_em = pic.find('em') if pic else None
        rank = rank_em.get_text(strip=True) if rank_em else None

        link = hd.find('a') if hd else None
        url = link['href'] if link else None

        title_span = hd.find('span', class_='title') if hd else None
        title = title_span.get_text(strip=True) if title_span else None

        info_p = bd.find('p') if bd else None
        info_text = info_p.get_text('\n', strip=True) if info_p else ''
        lines = [l.strip() for l in info_text.split('\n') if l.strip()]

        director = actors = year = country = genre = None
        if lines:
            first = lines[0]
            m = re.search(director_pattern, first)
            if m:
                director = m.group(1).strip().rstrip('...')
            m2 = re.search(actors_pattern, first)
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

        rating_span = bd.find('span', class_='rating_num') if bd else None
        rating = float(rating_span.get_text(strip=True)) if rating_span else None

        votes = None
        if bd:
            for span in bd.find_all('span'):
                if '人评价' in span.get_text():
                    votes = span.get_text(strip=True).replace('人评价', '')
                    break

        quote_p = bd.find('p', class_='quote') if bd else None
        quote_span = quote_p.find('span') if quote_p else None
        quote = quote_span.get_text(strip=True) if quote_span else None

        yield {
            'rank': rank, 'title': title, 'director': director,
            'actors': actors, 'year': year, 'country': country,
            'genre': genre, 'rating': rating, 'votes': votes,
            'quote': quote, 'url': url
        }


def save_data(data):
    name = data.get('title')
    data_path = f'{RESULTS_DIR}/{name}.json'
    json.dump(data, open(data_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)


def main(page):
    index_html = scrape_index(page)
    if not index_html:
        return
    movies = parse_index(index_html)
    for movie in movies:
        logging.info('get movie data %s', movie)
        logging.info('saving data to json file')
        save_data(movie)
        logging.info('data saved successfully')


if __name__ == '__main__':
    t_start = time.time()
    for page in range(1, TOTAL_PAGE + 1):
        main(page)
        time.sleep(1)
    elapsed = time.time() - t_start
    logging.info('serial scraping done: %d pages, elapsed %.2fs',
                 TOTAL_PAGE, elapsed)
