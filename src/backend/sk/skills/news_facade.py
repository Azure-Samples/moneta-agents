from pydantic import BaseModel, Field
import json
import os
import logging
from typing import Annotated, Any, Callable, Set, Dict, List, Optional
import requests
import pandas as pd
from requests_html import HTMLSession

from semantic_kernel.functions import kernel_function

class NewsFacade:
    def __init__(self):
        pass  


    @kernel_function(
        name="search_news", 
        description="Search for investement's news and articles from the web for the client's portfolio position specified: the ticker"
    )
    def fetch_news(self, position:Annotated[str,"The position (ticker) of the client's portfolio"]) -> Annotated[str, "The output in JSON format"]:
        """
        Search the web for investement's news for the specific position passed as input into a pandas DataFrame.

        Parameters:
        positions List(str): the position to search news for

        Returns:
        pd.DataFrame: DataFrame containing the news found
        """
        try:
            url = f'https://finviz.com/quote.ashx?t={position}'
    
            session = HTMLSession()
            response = session.get(url)
            with response as r:
                # Find the news table
                news_table = r.html.find('table.fullview-news-outer', first=True)
                
                # Check if the news_table was found
                if news_table:
                    # Find all news entries
                    news_rows = news_table.find('tr')
                    print(f"Found {len(news_rows)} news entries.")
                    
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
                        news_headline = headline_tag.text
                        news_link = headline_tag.attrs['href']
                        
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
                    print(df)
                else:
                    print("News table not found.")
            
                return json.dumps(df.values.tolist())  
        except:
            logging.error(f"An unexpected error occurred in the 'search_news' function of the 'news_agent': {e}") 
            return 

    #Statically defined user functions for fast reference
    news_functions: Set[Callable[..., Any]] = {
        fetch_news,
    }