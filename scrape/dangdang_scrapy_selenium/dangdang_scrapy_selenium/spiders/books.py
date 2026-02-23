import re
from scrapy import Request, Spider
from dangdang_scrapy_selenium.items import DangdangBookItem


class DangdangBooksSpider(Spider):
    name = 'dangdang_books'
    allowed_domains = ['bang.dangdang.com']
    base_url = 'http://bang.dangdang.com/books/bestsellers/01.00.00.00.00.00-recent7-0-0-1-{}'
    max_pages = 5

    def start_requests(self):
        for page in range(1, self.max_pages + 1):
            url = self.base_url.format(page)
            self.logger.info('开始抓取页面：%s', url)
            yield Request(
                url=url,
                callback=self.parse_index,
                cb_kwargs={'page': page},
                meta={'wait_for': 'ul.bang_list li'},
            )

    def parse_index(self, response, page):
        items = response.css('ul.bang_list li')
        self.logger.info('第 %s 页抓取到 %s 本书', page, len(items))
        for item in items:
            yield self.parse_item(item)

    # 静态方法：不依赖实例(self)，只做纯数据解析
    @staticmethod
    def parse_item(node):
        publisher_nodes = node.css('div.publisher_info')
        author = ''
        publish_date = ''
        publisher = ''
        if publisher_nodes:
            author = (
                publisher_nodes[0].css('a::attr(title)').get()
            )
        if len(publisher_nodes) >= 2:
            publish_date = publisher_nodes[1].css('span::text').get(default='').strip()
            publisher = publisher_nodes[1].css('a::text').get(default='').strip()

        return DangdangBookItem(
            rank=DangdangBooksSpider.extract_int(node.css('div[class*=list_num]::text').get()),
            title=node.css('div.name a::attr(title)').get()
            or node.css('div.name a::text').get(default='').strip(),
            author=author,
            publisher=publisher,
            date=publish_date,
            price=DangdangBooksSpider.extract_price(node.css('span.price_n::text').get()),
            original_price=DangdangBooksSpider.extract_price(node.css('span.price_r::text').get()),
            discount=node.css('span.price_s::text').get(default='').strip(),
            comments=DangdangBooksSpider.extract_int(node.css('div.star a::text').get()),
            recommendation=node.css('div.star span.tuijian::text').get(default='').strip(),
            url=node.css('div.name a::attr(href)').get(default=''),
        )

    # 静态方法：从字符串提取整数，与爬虫实例状态无关
    @staticmethod
    def extract_int(text):
        if not text:
            return 0
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else 0

    # 静态方法：从字符串提取浮点数作为价格，与爬虫实例状态无关
    @staticmethod
    def extract_price(text):
        if not text:
            return 0.0
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        return float(match.group(1)) if match else 0.0
