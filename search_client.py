import requests
import json
import logging
from config import get_config

logger = logging.getLogger(__name__)

def web_search(query: str, max_results: int = 5) -> list:
    """
    Performs a web search using Tavily API (preferred) or Serper API depending on keys.
    Returns a list of dicts: [{'title': str, 'url': str, 'content': str}]
    """
    tavily_key = get_config("TAVILY_API_KEY")
    serper_key = get_config("SERPER_API_KEY")

    if not tavily_key and not serper_key:
        logger.warning("No search API keys found. Returning empty list.")
        return []

    # Try Tavily first
    if tavily_key:
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": tavily_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_images": False
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", item.get("snippet", ""))
                    })
                return results
            else:
                logger.error(f"Tavily search failed: Status {response.status_code}, {response.text}")
        except Exception as e:
            logger.error(f"Error calling Tavily API: {str(e)}")

    # Fallback to Serper
    if serper_key:
        try:
            url = "https://google.serper.dev/search"
            payload = {
                "q": query,
                "num": max_results
            }
            headers = {
                "X-API-KEY": serper_key,
                "Content-Type": "application/json"
            }
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                results = []
                # Organic results
                for item in data.get("organic", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "content": item.get("snippet", "")
                    })
                # Add answer box if present
                if "answerBox" in data:
                    ab = data["answerBox"]
                    results.insert(0, {
                        "title": ab.get("title", "Direct Answer"),
                        "url": ab.get("link", ""),
                        "content": ab.get("answer", ab.get("snippet", ""))
                    })
                return results
            else:
                logger.error(f"Serper search failed: Status {response.status_code}, {response.text}")
        except Exception as e:
            logger.error(f"Error calling Serper API: {str(e)}")

    return []
