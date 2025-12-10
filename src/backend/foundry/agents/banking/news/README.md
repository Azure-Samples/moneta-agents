# News Agent

The News Agent is responsible for fetching investment news for portfolio positions from financial websites.

## Features

- Fetches latest news for stock ticker symbols
- Retrieves news from finviz.com
- Returns structured JSON with headline, date, time, and link
- Limits results to most recent 5 news items per ticker

## Functions

### `fetch_news(position: str) -> str`

Fetches investment news for a specific stock ticker.

**Parameters:**
- `position`: The stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')

**Returns:**
- JSON string containing:
  - `status`: 'success' or 'error'
  - `ticker`: The requested ticker symbol
  - `news_count`: Number of news items retrieved
  - `news`: Array of news items with:
    - `Ticker`: Stock symbol
    - `Date`: Publication date
    - `Time`: Publication time
    - `Headline`: News headline
    - `Link`: URL to full article

## Usage Example

```python
from news.news_functions import fetch_news

# Fetch news for Apple stock
result = fetch_news("AAPL")
print(result)
```

## Dependencies

- `requests-html`: For web scraping
- `pandas`: For data handling
- `tracing_utils`: For observability

## Data Source

News is scraped from [finviz.com](https://finviz.com), a popular financial visualization website.
