import json
import logging
import requests
from config import get_config
from crawler import crawl_url_sync

logger = logging.getLogger(__name__)

def perform_full_research(lead_username: str, lead_email: str) -> dict:
    """
    Main orchestrator that conducts research based on lead_username and lead_email.
    Queries the Cloudflare Worker to perform web search queries, crawls identified URLs
    using Crawl4ai/Playwright, and uses Cloudflare Workers AI to synthesize the data.
    """
    logger.info(f"Starting research on username: {lead_username}, email: {lead_email}")

    worker_url = get_config("CLOUDFLARE_WORKER_URL")
    tavily_key = get_config("TAVILY_API_KEY")
    serper_key = get_config("SERPER_API_KEY")

    search_hits = []

    # 1. Query Cloudflare Worker for search index aggregation
    if worker_url:
        try:
            logger.info(f"Querying Cloudflare Worker API: {worker_url}")
            headers = {"Content-Type": "application/json"}
            if tavily_key:
                headers["X-Tavily-Key"] = tavily_key
            if serper_key:
                headers["X-Serper-Key"] = serper_key

            payload = {
                "username": lead_username,
                "email": lead_email
            }
            
            response = requests.post(worker_url, json=payload, headers=headers, timeout=25)
            if response.status_code == 200:
                data = response.json()
                search_hits = data.get("results", [])
                logger.info(f"Cloudflare Worker returned {len(search_hits)} results.")
            else:
                logger.error(f"Cloudflare Worker returned status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Failed to fetch search results from Cloudflare Worker: {str(e)}")

    # 2. Local Fallback Search API (for local developer sandbox or backup)
    if not search_hits:
        logger.info("Worker URL not configured or returned empty. Running local fallback search API queries.")
        from search_client import web_search
        
        # Query 1: LinkedIn search
        search_query_1 = f'"{lead_username}" {lead_email} LinkedIn profile'.strip()
        search_hits.extend(web_search(search_query_1, max_results=4))
        
        # Query 2: General mentions
        if lead_email and "@" in lead_email:
            domain = lead_email.split("@")[-1]
            if domain not in ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]:
                search_query_2 = f'"{lead_username}" "{domain.split(".")[0]}"'
                search_hits.extend(web_search(search_query_2, max_results=3))

    # 3. Locate LinkedIn URL and scrape via Enrichment APIs if keys exist
    apify_token = get_config("APIFY_TOKEN")
    proxycurl_key = get_config("PROXYCURL_API_KEY")
    scrapingdog_key = get_config("SCRAPINGDOG_API_KEY")
    linkedin_url = ""
    raw_linkedin_profile = {}

    if apify_token or proxycurl_key or scrapingdog_key:
        # Determine LinkedIn URL from input or search hits
        if "linkedin.com/in/" in lead_username:
            linkedin_url = lead_username
        else:
            # Look in search hits first
            for hit in search_hits:
                hit_url = hit.get("url") or hit.get("link") or ""
                if "linkedin.com/in/" in hit_url:
                    linkedin_url = hit_url
                    break
            
            # Heuristic fallback if not found in hits
            if not linkedin_url:
                clean_username = lead_username.strip().strip("/")
                linkedin_url = f"https://linkedin.com/in/{clean_username}"

        try:
            logger.info(f"Triggering LinkedIn profile enrichment for: {linkedin_url}")
            from linkedin_apify import scrape_profile_enrichment
            profile_data = scrape_profile_enrichment(
                profile_url=linkedin_url,
                apify_token=apify_token,
                proxycurl_key=proxycurl_key,
                scrapingdog_key=scrapingdog_key
            )
            if profile_data and "error" not in profile_data:
                raw_linkedin_profile = profile_data
                logger.info("Successfully fetched and resolved LinkedIn profile via enrichment.")
            else:
                logger.warning(f"Enrichment scraper returned empty or error profile data: {profile_data}")
        except Exception as e:
            logger.error(f"LinkedIn profile enrichment execution failed: {str(e)}")

    # 4. Crawl other non-LinkedIn webpages using Playwright/Crawl4ai
    crawled_pages = []
    candidate_urls = []
    for hit in search_hits:
        url = hit.get("url") or hit.get("link")
        if url and "linkedin.com" not in url and not url.endswith((".pdf", ".jpg", ".png")):
            candidate_urls.append(url)

    # Crawl the top 3 unique URLs
    for url in list(set(candidate_urls))[:3]:
        try:
            logger.info(f"Crawling URL: {url}")
            page_text = crawl_url_sync(url)
            if page_text and not page_text.startswith("Error"):
                crawled_pages.append({
                    "url": url,
                    "content": page_text[:8000]
                })
        except Exception as e:
            logger.error(f"Failed to crawl {url}: {str(e)}")

    # 5. Synthesize with Cloudflare Workers AI
    research_context = {
        "search_hits": search_hits,
        "crawled_pages": crawled_pages,
        "raw_linkedin_profile": raw_linkedin_profile
    }

    return _synthesize_with_worker_ai(lead_username, lead_email, research_context)

def _synthesize_with_worker_ai(lead_username: str, lead_email: str, context: dict) -> dict:
    """
    Sends search logs and page content to the Cloudflare Worker to synthesize using Workers AI.
    """
    worker_url = get_config("CLOUDFLARE_WORKER_URL")
    if not worker_url:
        raise ValueError("CLOUDFLARE_WORKER_URL is not configured in your Railway environment variables.")

    try:
        payload = {
            "action": "synthesize",
            "context": json.dumps(context, indent=2)
        }
        headers = {"Content-Type": "application/json"}
        
        logger.info(f"Requesting Cloudflare Workers AI synthesis: {worker_url}")
        response = requests.post(worker_url, json=payload, headers=headers, timeout=45)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(f"Cloudflare Worker returned error {response.status_code}: {response.text}")
            
    except Exception as e:
        logger.error(f"Cloudflare Workers AI synthesis call failed: {str(e)}")
        raise e

def _generate_fallback_report(lead_username: str, lead_email: str, context: dict) -> dict:
    """
    Fallback method in case Gemini is unavailable.
    """
    # Extract basic name/domain
    resolved_name = lead_username.split("/")[-1].replace("-", " ").title()
    company_name = "Detected Company"
    if lead_email and "@" in lead_email:
        domain = lead_email.split("@")[-1]
        if domain not in ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]:
            company_name = domain.split(".")[0].title()

    # Simple insights list from search hits
    web_insights = []
    for hit in context.get("search_hits", [])[:3]:
        web_insights.append(f"{hit.get('title')}: {hit.get('content')[:120]}... ({hit.get('url')})")

    return {
        "lead_name": resolved_name,
        "lead_email": lead_email,
        "company_name": company_name,
        "linkedin_url": f"https://www.linkedin.com/in/{lead_username.split('/')[-1]}",
        "summary": f"Professional dossier compiled for {resolved_name} using web indices.",
        "skills": ["Management", "Strategic Planning", "Business Development"],
        "experience": [
            {
                "title": "Professional Role",
                "company": company_name,
                "period": "Active",
                "description": "Details pending live LLM synthesis."
            }
        ],
        "company_details": {
            "name": company_name,
            "website": f"https://www.{company_name.lower().replace(' ', '')}.com",
            "industry": "Consulting / Technology",
            "size": "N/A",
            "description": "Information collected from search queries."
        },
        "web_insights": web_insights
    }
