# 爬虫任务报告
## 1. 任务概述

本次作业包含两个任务：
- **Task1（豆瓣）**：使用 `requests` 抓取豆瓣 Top250 电影信息，保存并记录耗时，并给出优化版本。
- **Task2（电商）**：选择电商平台，使用三种及以上不同库抓取商品信息并保存。

目标平台：
- Task1：豆瓣 Top250（`m.douban.com` JSON 接口）
- Task2：当当网图书畅销榜 TOP100（近7日，5页）

## 2. Task1：豆瓣电影信息抓取与优化

### 2.1 抓取字段

- `rank`：排名
- `title`：电影名
- `director`：导演
- `actors`：主演
- `year`：年份
- `country`：国家/地区
- `genre`：类型
- `rating`：评分
- `votes`：评价人数
- `quote`：短评
- `url`：详情页链接

### 2.2 方案1：`requests`（串行基线）

脚本：`scrape/douban_scrape.py`  
输出：`data/douban_top250/*.json`

连续运行 3 次结果：

- 第1次：12.44s
- 第2次：12.11s
- 第3次：12.72s
- **平均：12.42s**

### 2.3 方案2：`aiohttp + asyncio`

脚本：`scrape/douban_scrape_optimized.py`  
输出：`data/douban_movies_optimized.csv`

连续运行 3 次结果：

- 第1次：1.16s
- 第2次：1.08s
- 第3次：1.05s
- **平均：1.10s**

说明：Task1 两个版本均可稳定连续运行并抓满 250 条数据；优化版相对串行基线平均约 11.3x 提速，满足“加快一半以上”要求。

## 3. Task2：当当网商品信息抓取

### 3.1 抓取字段

- `rank`：排名
- `title`：书名
- `author`：作者
- `publisher`：出版社
- `date`：出版日期
- `price`：现价
- `original_price`：原价
- `discount`：折扣
- `comments`：评论数
- `recommendation`：推荐度
- `url`：商品链接

### 3.2 方案1：`requests + BeautifulSoup + ThreadPoolExecutor`

脚本：`scrape/books_requests.py`  
输出：`data/dangdang_requests.csv`

连续运行 3 次结果：

- 第1次：0.80s
- 第2次：0.49s
- 第3次：0.69s
- **平均：0.66s**

### 3.3 方案2：`aiohttp + lxml`

脚本：`scrape/books_aiohttp.py`  
输出：`data/dangdang_aiohttp.csv`

连续运行 3 次结果：

- 第1次：0.44s
- 第2次：0.41s
- 第3次：0.71s
- **平均：0.52s**

### 3.4 方案3：`selenium + ProcessPoolExecutor`

脚本：`scrape/books_selenium.py`  
输出：`data/dangdang_selenium.csv`

连续运行 3 次结果：

- 第1次：7.04s
- 第2次：7.70s
- 第3次：7.66s
- **平均：7.47s**

### 3.5 方案4：`scrapy + selenium`

脚本目录：`scrape/dangdang_scrapy_selenium/`  
命令：`scrapy crawl dangdang_books`  
输出：`data/dangdang_scrapy_selenium.csv`

连续运行 3 次结果：

- 第1次：3.61s
- 第2次：2.55s
- 第3次：2.58s
- **平均：2.91s**

说明：Task2 四种方案均可稳定连续运行并抓满 100 条数据。

## 4. 最终数据文件
- `data/douban_top250/*.json`（250）
- `data/douban_movies_optimized.csv`（250）
- `data/dangdang_requests.csv`（100）
- `data/dangdang_aiohttp.csv`（100）
- `data/dangdang_selenium.csv`（100）
- `data/dangdang_scrapy_selenium.csv`（100）
