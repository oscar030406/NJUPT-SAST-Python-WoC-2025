from pathlib import Path

BOT_NAME = 'dangdang_scrapy_selenium'

SPIDER_MODULES = ['dangdang_scrapy_selenium.spiders']
NEWSPIDER_MODULE = 'dangdang_scrapy_selenium.spiders'

ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 1
DOWNLOAD_TIMEOUT = 20
LOG_LEVEL = 'INFO'
FEED_EXPORT_ENCODING = 'utf-8'

ITEM_PIPELINES = {
    'dangdang_scrapy_selenium.pipelines.DangdangCsvPipeline': 300,
}

DOWNLOADER_MIDDLEWARES = {
    'dangdang_scrapy_selenium.middlewares.SeleniumMiddleware': 543,
}
SELENIUM_WAIT_TIMEOUT = 8

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VENV_CHROMEDRIVER = PROJECT_ROOT.parent / '.venv' / 'Scripts' / 'chromedriver.exe'
if VENV_CHROMEDRIVER.exists():
    SELENIUM_DRIVER_EXECUTABLE_PATH = str(VENV_CHROMEDRIVER)
else:
    SELENIUM_DRIVER_EXECUTABLE_PATH = ''

SELENIUM_DRIVER_ARGUMENTS = [
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--blink-settings=imagesEnabled=false',
    'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
]

OUTPUT_CSV = str(PROJECT_ROOT / 'data' / 'dangdang_scrapy_selenium.csv')
CSV_FIELDS = [
    'rank', 'title', 'author', 'publisher', 'date',
    'price', 'original_price', 'discount', 'comments',
    'recommendation', 'url',
]
