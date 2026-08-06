import json
import logging
import requests
import google.generativeai as genai
from config import get_config
from crawler import crawl_url_sync

logger = logging.getLogger(__name__)

def perform_full_research(lead_username: str, lead_email: str) -> dict:
    """
    Main orchestrator that conducts research based on lead_username and lead_email.
    Queries the Cloudflare Worker to perform web search queries, crawls identified URLs
    using Crawl4ai/Playwright, and uses Gemini to synthesize the data.
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

    # 3. Crawl webpages using Playwright/Crawl4ai
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

    # 4. Synthesize with Gemini
    research_context = {
        "search_hits": search_hits,
        "crawled_pages": crawled_pages
    }

    return _synthesize_with_gemini(lead_username, lead_email, research_context)

def _synthesize_with_gemini(lead_username: str, lead_email: str, context: dict) -> dict:
    """
    Sends search logs and page content to Gemini to extract name, company, history, and insights.
    """
    gemini_key = get_config("GEMINI_API_KEY") or get_config("GOOGLE_API_KEY")
    if not gemini_key:
        logger.warning("Gemini API key not found. Returning a basic parsed structure.")
        return _generate_fallback_report(lead_username, lead_email, context)

    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        system_prompt = """
You are an expert sales intelligence assistant. Your job is to analyze search results (titles, snippets, URLs) and crawled webpage texts about a lead (identified by their username and email), resolve their professional details, and compile a structured JSON report.

Your JSON output MUST match this exact schema:
{
  "lead_name": "Full name of the lead (resolve from search results/crawled content. Fallback to username)",
  "lead_email": "Email address of the lead",
  "company_name": "Name of the company they work at (resolve from search results)",
  "linkedin_url": "Resolved LinkedIn profile URL (resolve from search results)",
  "summary": "A 3-5 sentence executive summary of the lead, their professional focus, expertise, and current role.",
  "skills": ["List of 5-8 key professional skills"],
  "experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "period": "Start - End Date (e.g., 2021 - Present)",
      "description": "Short description of responsibilities/accomplishments"
    }
  ],
  "company_details": {
    "name": "Official Company Name",
    "website": "Company website URL",
    "industry": "Industry description",
    "size": "Estimated company size (e.g. 50-200 employees)",
    "description": "A detailed 3-4 sentence paragraph about what the company does, its main products/services, and target market."
  },
  "web_insights": [
    "3 to 5 bullet points containing specific insights about the person or company found on the web (e.g. speaking engagements, articles written, GitHub activity, recent company press releases, funding rounds, product launches)."
  ]
}

Analyze the search snippets and crawled web pages carefully. Identify the lead's real name (e.g., matching the username or email), their job title, current employer, and details about that employer. 
Do not invent facts. If certain fields (e.g. experience details, skills) are not present in the context, write a reasonable summary based on the available web search snippets.
"""

        user_content = f"""
Target Lead Details:
- Username: {lead_username}
- Email: {lead_email}

Context Collected:
{json.dumps(context, indent=2)}

Synthesize the above context into the requested JSON schema.
"""

        response = model.generate_content(
            contents=user_content,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.2
            },
            system_instruction=system_prompt
        )

        return json.loads(response.text)

    except Exception as e:
        logger.error(f"Gemini synthesis failed: {str(e)}. Using fallback parsing.")
        return _generate_fallback_report(lead_username, lead_email, context)

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
