# NJUPT-SAST-Python-WoC-2025

这是 NJUPT SAST 2025 年 Python 方向 WoC 仓库。

点击 [这里](https://njupt-sast.feishu.cn/wiki/GS5Vw6IDNiieVIkcf9MczzHInVf) 查看题目详情和提交要求。

## 分支说明

- `爬虫一号`：原 `dev` 分支（对应 `woc` 方案）。
- `爬虫2号`：当前 `woc2` 方案分支。

`爬虫2号` 相比 `爬虫一号` 的主要差异如下：

1. 豆瓣 Task1 重新实现为移动端 JSON 接口抓取。  
   原因是近期复测时发现旧方案更容易触发风控（大量 403），因此改为 `m.douban.com` 接口并调整请求头、超时设计方案。
2. Task2 在原有三种实现基础上新增 `scrapy + selenium` 方案.
3. 报告内容已按当前实现与实测结果重写，明确记录各方案脚本、输出文件和耗时对比。
