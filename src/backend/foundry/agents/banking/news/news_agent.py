"""
News Agent for Moneta Banking - Fetches investment news for portfolio positions.
Uses web scraping to retrieve real-time news from financial websites.
"""

from .news_functions import news_functions

# Agent configuration
NEWS_AGENT_CONFIG = {
    "name": "moneta-news-agent",
    "instructions": (
        "You are a News specialist for Moneta Banking. "
        "You fetch and analyze the latest investment news for specific stock positions. "
        "Use the fetch_news function to retrieve news for stock ticker symbols. "
        "When presenting news, summarize the key headlines and their potential impact on the portfolio."
    ),
    "description": "News Agent - fetches investment news for portfolio positions",
    "tools": news_functions
}
