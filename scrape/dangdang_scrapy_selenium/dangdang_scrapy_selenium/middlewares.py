import logging

from scrapy import signals
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


class SeleniumMiddleware:
    def __init__(self, timeout, arguments, driver_executable_path):
        options = Options()
        for argument in arguments:
            options.add_argument(argument)
        self.timeout = timeout
        self.driver_executable_path = driver_executable_path
        if self.driver_executable_path:
            # 若配置了驱动路径，则通过 Service 显式指定 chromedriver 可执行文件位置
            service = Service(executable_path=self.driver_executable_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        else:
            # 未配置驱动路径时，依赖系统 PATH 或 Selenium Manager 自动管理 chromedriver
            self.driver = webdriver.Chrome(options=options)

    # @classmethod 将此方法标记为类方法，第一个参数为类本身（cls）而非实例。
    # Scrapy 实例化中间件时会自动调用 from_crawler，将 crawler 对象传入，
    # 从而可以通过 crawler.settings 读取配置，再用这些配置调用 cls(...) 构造并返回中间件实例。
    @classmethod
    def from_crawler(cls, crawler):
        timeout = crawler.settings.getint('SELENIUM_WAIT_TIMEOUT', 6)
        arguments = crawler.settings.getlist('SELENIUM_DRIVER_ARGUMENTS')
        driver_executable_path = crawler.settings.get('SELENIUM_DRIVER_EXECUTABLE_PATH', '')
        middleware = cls(
            timeout=timeout,
            arguments=arguments,
            driver_executable_path=driver_executable_path,
        )
        logger.info('Selenium 驱动路径：%s', driver_executable_path or 'auto')
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def process_request(self, request, spider):
        self.driver.get(request.url)
        wait_for = request.meta.get('wait_for')
        if wait_for:
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
            )
        html = self.driver.page_source
        return HtmlResponse(
            url=request.url,
            body=html,
            request=request,
            encoding='utf-8',
            status=200,
        )

    def spider_closed(self):
        if self.driver:
            self.driver.quit()
