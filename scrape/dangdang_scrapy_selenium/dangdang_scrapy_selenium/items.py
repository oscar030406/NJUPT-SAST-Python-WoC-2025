from scrapy.item import Field, Item


class DangdangBookItem(Item):
    rank = Field()
    title = Field()
    author = Field()
    publisher = Field()
    date = Field()
    price = Field()
    original_price = Field()
    discount = Field()
    comments = Field()
    recommendation = Field()
    url = Field()
