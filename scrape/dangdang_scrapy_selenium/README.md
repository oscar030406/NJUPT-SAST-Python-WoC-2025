# Dangdang Scrapy + Selenium

Run from this directory:

```bash
..\..\..\.venv\Scripts\activate
scrapy crawl dangdang_books
```

Output:

- `../../data/dangdang_scrapy_selenium.csv`

Notes:

- This method uses Selenium + Chrome.
- Default driver path is `..\..\..\.venv\Scripts\chromedriver.exe`.
- If needed, override in `settings.py` via `SELENIUM_DRIVER_EXECUTABLE_PATH`.
