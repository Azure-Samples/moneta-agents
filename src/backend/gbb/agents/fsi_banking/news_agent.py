# CRM Agent 
from pydantic import BaseModel, Field
import json
import os
import logging
from gbb.genai_vanilla_agents.agent import Agent
from gbb.agents.fsi_banking.config import create_llm
from typing import List, Annotated, Optional
import requests
import pandas as pd
from requests_html import HTMLSession

news_agent = Agent(  
    id="News",
    system_message="""You are an assistant that fetch investement's news from the web for the client's portfolio positions.
        
        **Your Responsibilities:**
        - **Only respond to user requests that are relevant about investement's news and articles.**
        - Don't come up with information that are not coming from the provided function.
    
    """,  
    llm=create_llm(),  
    description="""Call this Agent if:
        - You need to search for investement's news or articles from the web relevant to specific portfolio positions.
        DO NOT CALL THIS AGENT IF:  
        - You need to search for specific client's data identified by a client name or id in the request
        - You need to search for investement offering or funds and etf information
        - You need to search for in-house views or reccomandations about investement strategies""",
)  


def get_source(url):
    """Return the source code for the provided URL. 
    Args: 
        url (string): URL of the page to scrape.
    Returns:
        response (object): HTTP response object from requests_html. 
    """

    try:
        session = HTMLSession()
        response = session.get(url)
        return response

    except requests.exceptions.RequestException as e:
        print(e)


def get_feed(response):
    """Return a Pandas dataframe containing the RSS feed contents.
    Args: 
        response (string): response from the get_source(URL)
    Returns:
        dataframe : of articles containing the RSS feed contents.
    """
    ms_list = []
    with response as r:
        items = r.html.find("item", first=False)
        #print(len(items))
        for item in items:        
            #print(item)
            if item is not None:
                try:
                    title = item.find('title', first=True).text
                    pubDate = item.find('pubDate', first=True).text
                    link = item.find('link', first=True).html
                    categoryItem = item.find('category', first=True)
                    if categoryItem is not None:    
                        category = item.find('category', first=True).text
                    else:
                        category = 'None'
                    author = item.find('author', first=True).text
                    description = item.find('description', first=True).text
                    
                    ms_list.append(
                        {
                            'Title': title,
                            'Description': description,
                            'Category':  category,
                            'Link' : link,
                            'Published On' : pubDate,
                            'Author' : author
                        }
                    )

                    ms_df = pd.DataFrame(ms_list)
                except Exception as e:
                    print("Cannot parse or extract text from the HTML item...")    
                #print(f"Article title: {title}, 'description': {description}, 'link': {link}, 'category': {category}, 'published on': {pubDate}, 'author': {author}")

    return ms_df


@news_agent.register_tool(description="Search for investement's news from the web for the client's portfolio positions")
def fetch_news(positions:Annotated[List[str],"The positions of the client's portfolio"]) -> str:
    """
    Search the web for investement's news for the specific for each of the positions passed as input into a pandas DataFrame.

    Parameters:
    positions List(str): the positions to search news for

    Returns:
    pd.DataFrame: DataFrame containing the news found
    """
    try:
        url = 'https://www.morningstar.co.uk/uk/news/rss.aspx?lang=en-GB'
        response = get_source(url)
        news = get_feed(response)
        #logging.info(f"News: {news}")
        return json.dumps(news.values.tolist())        
    except Exception as e:
        logging.error(f"An unexpected error occurred in the 'fetch_news' function of the 'news_agent': {e}") 
