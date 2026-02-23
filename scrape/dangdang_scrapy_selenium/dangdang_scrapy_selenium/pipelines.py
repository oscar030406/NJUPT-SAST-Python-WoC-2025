import csv
from pathlib import Path

from itemadapter import ItemAdapter


class DangdangCsvPipeline:
    def open_spider(self, spider):
        output_csv = Path(spider.settings.get('OUTPUT_CSV'))
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        self.fields = list(spider.settings.getlist('CSV_FIELDS'))
        self.fp = output_csv.open('w', newline='', encoding='utf-8-sig')
        self.writer = csv.DictWriter(self.fp, fieldnames=self.fields)
        self.writer.writeheader()
        spider.logger.info('CSV 输出文件：%s', output_csv)

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        row = {field: adapter.get(field, '') for field in self.fields}
        self.writer.writerow(row)
        return item

    def close_spider(self, spider):
        # 爬虫结束时关闭文件句柄
        if hasattr(self, 'fp') and not self.fp.closed:
            self.fp.close()
