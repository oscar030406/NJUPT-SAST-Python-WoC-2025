# 爬虫向任务报告

## 1. 任务概述

本次作业包含两个任务：

- **Task1（豆瓣）**：使用 `requests` 获取豆瓣 Top250 电影信息，保存并记录耗时；在此基础上优化代码，使爬取速度提升 50% 以上。
- **Task2（电商）**：选择平台，使用三种以上不同库爬取商品信息并保存。本项目选择 **当当网图书畅销榜** 作为目标，实现三种抓取方式。

---

## 2. Task1：豆瓣 Top250 电影信息抓取与优化

### 2.1 抓取目标与字段设计

抓取对象：豆瓣电影 Top250 列表（共 10 页，每页 25 条，总计 250 条）。

字段：

- `rank`：排名
- `title`：电影名
- `director`：导演
- `actors`：主演
- `year`：上映年份
- `country`：国家/地区
- `genre`：类型
- `rating`：评分
- `votes`：评价人数
- `quote`：短评
- `url`：详情页链接

保存方式：基础版保存为 JSON，优化版保存为 CSV。

### 2.2 基础版（requests 串行）

脚本：`scrape/douban_scrape.py`

实测结果（本次提交数据）：
- 抓取并保存 250 部电影
- 串行耗时：**约16.38s**

### 2.3 优化版（aiohttp + asyncio 并发）

脚本：`scrape/douban_scrape_optimized.py`

优化思路：
- 抓取分页属于 **I/O 密集型任务**，瓶颈主要是等待网络响应
- 使用 `aiohttp` 并发请求不同分页，在等待期间可处理其它请求，从而降低总耗时

实测结果：
- 并发耗时：**约1.68s**
- 加速比：**约9.75x（16.38s / 1.68s）**，

---

## 3. Task2：当当网图书畅销榜爬取

### 3.1 平台选择与字段设计

平台：**当当网**（dangdang.com）

目标：**图书畅销榜 TOP100**（近7日，每页20本 × 5页）
URL：`http://bang.dangdang.com/books/bestsellers/01.00.00.00.00.00-recent7-0-0-1-{page}`

字段：

| 字段 | 说明 |
|------|------|
| `rank` | 排名 |
| `title` | 书名 |
| `author` | 作者 |
| `publisher` | 出版社 |
| `date` | 出版日期 |
| `price` | 现价（元） |
| `original_price` | 原价（元） |
| `discount` | 折扣 |
| `comments` | 评论数 |
| `recommendation` | 推荐度 |
| `url` | 商品链接 |

### 3.2 数据存储方案

统一使用 **CSV 文件** 存储，每种方案生成独立的 CSV：

- `data/dangdang_requests.csv`（requests 方案）
- `data/dangdang_aiohttp.csv`（aiohttp 方案）
- `data/dangdang_selenium.csv`（Selenium 方案）

### 3.3 不同库实现

#### 方案1：requests + BeautifulSoup（同步串行）

脚本：`scrape/books_requests.py`
存储：`data/dangdang_requests.csv`

实测结果：
- **100 条**商品
- 耗时：**约7.77s**

#### 方案2：aiohttp + BeautifulSoup（异步并发）

脚本：`scrape/books_aiohttp.py`
存储：`data/dangdang_aiohttp.csv`

实现要点：
- `aiohttp.ClientSession` 异步 HTTP 客户端
- `asyncio.Semaphore(5)` 控制并发度
- `BeautifulSoup` + `lxml` 解析（与方案1 共用解析逻辑，但请求层换为异步）
- 手动 `resp.read()` + `decode('gb2312')` 处理编码

实测结果：
- **100 条**商品
- 耗时：**约2.32s**

#### 方案3：Selenium（无头渲染）

脚本：`scrape/books_selenium.py`
存储：`data/dangdang_selenium.csv`

实测结果：
- **100 条**商品
- 耗时：**约39.36s**

## 4. 数据文件与提交内容

### 4.1 数据文件（data/）

| 文件 | 数量 | 说明 |
|------|------|------|
| `douban_top250/*.json` | 250 | 豆瓣 Top250 基础版，每部电影一个 JSON |
| `douban_movies_optimized.csv` | 250 | 豆瓣 Top250 优化版，CSV 格式 |
| `dangdang_requests.csv` | 100 | 当当畅销榜 requests 版 |
| `dangdang_aiohttp.csv` | 100 | 当当畅销榜 aiohttp 版 |
| `dangdang_selenium.csv` | 100 | 当当畅销榜 Selenium 版 |
