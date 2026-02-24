import csv
import logging
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')

BASE_URL = 'http://bang.dangdang.com/books/bestsellers/01.00.00.00.00.00-recent7-0-0-1-{}'
MAX_PAGES = 5
WORKERS = 3
MAX_RETRIES = 3
DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
CSV_FILE = DATA_DIR / 'dangdang_selenium.csv'
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
    """创建并返回配置好的无头 Chrome WebDriver 实例。"""
    opts = Options()
    opts.add_argument('--headless=new')                          # 无头模式，不弹出浏览器窗口
    opts.add_argument('--blink-settings=imagesEnabled=false')    # 禁止加载图片，加快加载速度
    opts.add_argument('--disable-gpu')                           # 禁用 GPU 加速，避免无头环境渲染报错
    opts.add_argument('--disable-extensions')                    # 禁用扩展，加快加载速度
    opts.add_argument('--disable-background-networking')         # 禁止后台网络请求
    opts.add_argument('--disable-renderer-backgrounding')        # 防止渲染进程被降级，保证页面正常渲染
    opts.add_argument('--no-sandbox')                            # 关闭沙箱
    opts.add_argument('--disable-dev-shm-usage')                 
    #不用 /dev/shm是Linux里的一个内存文件系统目录，通常用来做共享内存。很多浏览器进程会用它存放临时共享数据。，避免容器内存不足崩溃
    #Chrome 跑起来后如果太依赖它，可能会因为共享内存不够而崩掉。
    opts.add_argument('--window-size=1280,720')                  # 设定虚拟窗口尺寸，确保页面布局与桌面版一致
    opts.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 Chrome/122.0.0.0')     # 伪装成普通桌面 Chrome，防止被识别为爬虫
    opts.page_load_strategy = 'eager'                            # DOM 就绪即返回，不等待图片等资源，提升速度

    # 优先使用项目虚拟环境中的 chromedriver，否则回退到系统 PATH
    driver_path = Path(__file__).resolve().parents[2] / '.venv' / 'Scripts' / 'chromedriver.exe'
    if driver_path.exists():
        browser = webdriver.Chrome(service=Service(str(driver_path)), options=opts)
    else:
        browser = webdriver.Chrome(options=opts)

    browser.implicitly_wait(0)          # 关闭隐式等待，改用显式 WebDriverWait，避免超时叠加
    browser.set_page_load_timeout(15)   # 页面加载超时 15 秒，防止卡死
    return browser


def scrape_index(browser, page):
    url = BASE_URL.format(page)
    logging.info('开始抓取页面：%s', url)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            browser.get(url)
            WebDriverWait(browser, 6).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'ul.bang_list li'))
            )
            return
        except Exception:
            logging.warning('第 %d 页第 %d/%d 次抓取失败',
                            page, attempt, MAX_RETRIES, exc_info=True)
            if attempt < MAX_RETRIES:
                time.sleep(1)
    raise RuntimeError(f'第 {page} 页连续失败 {MAX_RETRIES} 次')


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

            # rating
            ct = _safe_text(li, 'div.star a')
            m = re.search(r'(\d+)', ct)
            comments = int(m.group(1)) if m else 0
            recommendation = _safe_text(li, 'span.tuijian')

            # price
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
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_FILE.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(books)
    logging.info('已保存 %d 条记录到 %s', len(books), CSV_FILE)


def run_pages(pages):
    browser = get_browser()
    page_books = {}
    try:
        for page in pages:
            try:
                scrape_index(browser, page)
                books = list(parse_index(browser))
                logging.info('第 %d 页抓取到 %d 本书', page, len(books))
                page_books[page] = books
            except Exception:
                logging.error('第 %d 页处理失败，已跳过', page, exc_info=True)
                page_books[page] = []
    finally:
        browser.quit()
    return page_books


if __name__ == '__main__':
    logging.info('开始抓取当当畅销榜，共 %d 页', MAX_PAGES)
    t_start = time.time()
    page_books = {}
    all_books = []
    # 将页码按轮询方式分配给各 Worker，例如 5 页 3 Worker 时：
    #   Worker 0 → [1, 4]，Worker 1 → [2, 5]，Worker 2 → [3]
    # 目的：每个进程复用同一个 Chrome 实例抓完分配给它的所有页，
    # 将浏览器启动次数控制在 WORKERS 次，而非每页单独创建/销毁一次。
    page_groups = [
        list(range(index, MAX_PAGES + 1, WORKERS))
        for index in range(1, WORKERS + 1)
    ]
    # 进程池并发调度：每个 Worker 组作为一个任务提交
    with ProcessPoolExecutor(max_workers=min(WORKERS, MAX_PAGES)) as executor:
        futures = [
            executor.submit(run_pages, pages)   # 每个进程运行 run_pages，内部共享一个 Chrome
            for pages in page_groups
        ]
        # 哪个进程先完成先取结果，不必等所有进程结束
        for future in as_completed(futures):
            page_books.update(future.result())
    for page in range(1, MAX_PAGES + 1):
        all_books.extend(page_books.get(page, []))
    elapsed = time.time() - t_start
    logging.info('Selenium 抓取完成，共 %d 本书，耗时 %.2f 秒', len(all_books), elapsed)
    save_data(all_books[:100])
