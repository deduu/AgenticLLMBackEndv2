import requests
import logging
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Optional
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

CUSTOM_SEARCH_API_KEY = "AIzaSyA-3hLyaM97E6k9YpIxf_XxzmJJKQ-TIAI"

CX_CODE = "109deb25d29b2499c"


async def google_search(query: str, num_results: str = "3") -> Optional[List[Dict[str, str]]]:
    """
    Perform a Google search using the Custom Search JSON API.

    Args:
        query: The search query string.
        num_results: The number of results to fetch as a string. Defaults to "10".

    Returns:
        Optional: A list of dictionaries containing the title and link of each search result.
        Returns None if an error occurs or no results are found.
    """
    if not query:
        logger.error("Search query is empty.")
        return None

    try:
        # Convert num_results to an integer
        num_results_int = int(num_results)
        if num_results_int > 10:
            logger.warning("Google Custom Search API supports a maximum of 10 results per request.")
            num_results_int = 10
        elif num_results_int < 1:
            logger.warning("num_results must be at least 1. Setting it to 1.")
            num_results_int = 1
    except ValueError:
        logger.error("Invalid value for num_results. Must be a valid integer string.")
        return None

    # Define the URL and parameters
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": CUSTOM_SEARCH_API_KEY,
        "cx": CX_CODE,
        "q": query,
        "num": num_results_int,
    }
    # print(CUSTOM_SEARCH_API_KEY)
    # print(CX_CODE)
    try:
        # Make the HTTP request
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)  # Properly encode query parameters

        # Process the response
        if response.status_code == 200:
            results = response.json()
            items = results.get("items", [])
      
            return [{"title": item["title"], "link": item["link"], "snippet": item["snippet"]} for item in items] 

        else:
            logger.error(f"Google Search API error: {response.status_code} - {response.text}")
            return None

    except httpx.RequestError as e:
        logger.error("A network error occurred while performing the Google search.")
        logger.error(f"Error details: {e}")
        return None
    
async def main():
    query = """Find flight ticket from Jakarta to Medan on 05/02/2025. I want to know the flight's baggage allowances """

    results = await google_search(query)
    print(results)

if __name__ == "__main__":
    asyncio.run(main())