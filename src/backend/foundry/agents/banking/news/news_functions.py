"""
News functions for fetching investment news from financial websites.
This module provides web scraping capabilities for retrieving news related to stock positions.
"""

import json
import logging
from typing import Annotated, Any, Callable
from pathlib import Path

import pandas as pd
from requests_html import HTMLSession

# Import tracing utilities from backend root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from tracing import get_tracing_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsSearchFunctions:
    """
    News Search Functions for fetching investment news from financial websites.
    Uses web scraping to retrieve latest news for specific stock positions.
    """
    
    def __init__(self):
        """Initialize the News Search Functions."""
        self.session = HTMLSession()
        self.base_url = "https://finviz.com/quote.ashx"
    
    def fetch_news(
        self, 
        position: Annotated[str, "The position (ticker) of the client's portfolio"]
    ) -> Annotated[str, "The output in JSON format"]:
        """
        Search the web for investment news for the specific position passed as input.

        Parameters:
            position (str): The stock ticker symbol to search news for (e.g., 'AAPL', 'MSFT')

        Returns:
            str: JSON string containing the news found with ticker, date, time, headline, and link
        """
        tracing_manager = get_tracing_manager()
        
        try:
            with tracing_manager.trace_function_call(
                "fetch_news",
                parameters={
                    "position": position,
                    "source": "finviz.com"
                }
            ):
                url = f'{self.base_url}?t={position}'
                
                response = self.session.get(url)
                
                # Find the news table
                news_table = response.html.find('table.fullview-news-outer', first=True)
                
                # Check if the news_table was found
                if news_table:
                    # Find all news entries
                    news_rows = news_table.find('tr')
                    logger.info(f"Found {len(news_rows)} news entries for {position}.")
                    
                    # List to store the news data
                    news_list = []
                    last_date = None  # To keep track of the date when only time is provided

                    # Extract data for the first 5 news entries
                    for i, row in enumerate(news_rows[:5]):  # Limit to first 5 entries
                        # Extract date and time
                        date_data = row.find('td', first=True).text.strip()
                        date_parts = date_data.split()
                        
                        if len(date_parts) == 2:
                            # Both date and time are provided
                            news_date = date_parts[0]
                            news_time = date_parts[1]
                            last_date = news_date  # Update last_date
                        else:
                            # Only time is provided
                            news_date = last_date
                            news_time = date_parts[0]
                        
                        # Extract headline and link
                        headline_tag = row.find('a', first=True)
                        if headline_tag:
                            news_headline = headline_tag.text
                            news_link = headline_tag.attrs.get('href', '')
                            
                            # Append the news data to the list
                            news_list.append({
                                'Ticker': position,
                                'Date': news_date,
                                'Time': news_time,
                                'Headline': news_headline,
                                'Link': news_link
                            })
                    
                    # Create a DataFrame for better visualization
                    df = pd.DataFrame(news_list)
                    logger.info(f"Retrieved {len(news_list)} news items for {position}")
                    
                    return json.dumps({
                        "status": "success",
                        "ticker": position,
                        "news_count": len(news_list),
                        "news": news_list
                    }, indent=2)
                else:
                    logger.warning(f"News table not found for {position}")
                    return json.dumps({
                        "status": "error",
                        "ticker": position,
                        "error": "News table not found",
                        "news": []
                    })
                    
        except Exception as e:
            logger.error(f"An unexpected error occurred in fetch_news for '{position}': {e}")
            return json.dumps({
                "status": "error",
                "ticker": position,
                "error": str(e),
                "news": []
            })


# Global instance will be initialized when first used
_news_search_functions = None


def get_news_search_functions():
    """Get or create the global news search functions instance."""
    global _news_search_functions
    if _news_search_functions is None:
        _news_search_functions = NewsSearchFunctions()
    return _news_search_functions


# Wrapper function for agent execution
def fetch_news(position: str) -> str:
    """
    Wrapper function for agent execution.
    Fetches investment news for a specific stock ticker.
    
    Args:
        position: The stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')
        
    Returns:
        JSON string containing news articles for the ticker
    """
    return get_news_search_functions().fetch_news(position)


# Export functions for agent registration
news_functions: list[Callable[..., Any]] = [fetch_news]
