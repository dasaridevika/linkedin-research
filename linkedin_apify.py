import requests
import logging
import json

logger = logging.getLogger(__name__)

def scrape_profile_enrichment(profile_url: str, apify_token: str = None, scrapingdog_key: str = None) -> dict:
    """
    Orchestrates LinkedIn profile enrichment.
    Tries active keys in order of reliability:
    1. Scrapingdog (LinkedIn Scraper API)
    2. Apify (Fallback browser automation)
    """
    # Clean the profile URL
    profile_url = profile_url.strip().rstrip("/")
    if "www.linkedin.com" in profile_url:
        profile_url = profile_url.replace("www.linkedin.com", "linkedin.com")
    elif not profile_url.startswith("http"):
        profile_url = f"https://linkedin.com/in/{profile_url}"

    # 1. Try Scrapingdog
    if scrapingdog_key:
        try:
            logger.info(f"Querying Scrapingdog for URL: {profile_url}")
            params = {
                "api_key": scrapingdog_key,
                "type": "profile",
                "url": profile_url
            }
            response = requests.get("https://api.scrapingdog.com/linkedin", params=params, timeout=25)
            
            if response.status_code == 200:
                logger.info("Successfully fetched profile data from Scrapingdog.")
                return _parse_scrapingdog_profile(response.json())
            else:
                logger.error(f"Scrapingdog API returned status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Failed to query Scrapingdog API: {str(e)}")

    # 3. Fallback to Apify
    if apify_token:
        try:
            logger.info(f"Fallback: Triggering Apify data-slayer LinkedIn Scraper for URL: {profile_url}")
            actor_id = "data-slayer~linkedin-profile-scraper"
            url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
            
            headers = {"Content-Type": "application/json"}
            payload = {
                "urls": [profile_url],
                "proxyConfiguration": {
                    "useApifyProxy": True
                }
            }
            params = {
                "token": apify_token,
                "timeout": 60
            }
            
            response = requests.post(url, json=payload, headers=headers, params=params, timeout=70)
            
            if response.status_code in [200, 201]:
                dataset_items = response.json()
                if isinstance(dataset_items, list) and len(dataset_items) > 0:
                    logger.info("Successfully fetched profile data from Apify.")
                    return _parse_apify_profile(dataset_items[0])
                else:
                    logger.warning("Apify completed but returned an empty dataset.")
            else:
                logger.error(f"Apify API returned error status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Failed to query Apify API: {str(e)}")

    return {"error": "All enrichment integrations failed or keys were missing"}


def _parse_scrapingdog_profile(raw_data: dict) -> dict:
    """
    Parses Scrapingdog JSON response structure.
    """
    experiences = []
    # Scrapingdog usually returns list of experiences
    for exp in raw_data.get("experience", []):
        period = f"{exp.get('startDate', '')} - {exp.get('endDate', 'Present')}"
        experiences.append({
            "title": exp.get("title", ""),
            "company": exp.get("companyName", ""),
            "period": period.strip(" -"),
            "description": exp.get("description", "")
        })
        
    education = []
    for edu in raw_data.get("education", []):
        education.append({
            "school": edu.get("schoolName", ""),
            "degree_name": edu.get("degreeName", ""),
            "field_of_study": edu.get("fieldOfStudy", "")
        })
        
    return {
        "full_name": raw_data.get("fullName", ""),
        "first_name": "",
        "last_name": "",
        "headline": raw_data.get("headline", ""),
        "summary": raw_data.get("about", ""),
        "experiences": experiences,
        "education": education,
        "skills": raw_data.get("skills", [])[:10],
        "city": raw_data.get("location", "")
    }

def _parse_apify_profile(raw_data: dict) -> dict:
    """
    Parses Apify's JSON response structure.
    """
    experiences = []
    for exp in raw_data.get("positions", raw_data.get("experiences", raw_data.get("experience", []))):
        company_name = exp.get("companyName", exp.get("company", exp.get("company_name", "")))
        title = exp.get("title", "")
        start_date = exp.get("startDate", {})
        end_date = exp.get("endDate", {})
        
        start_year = start_date.get("year", start_date) if isinstance(start_date, dict) else (start_date or "")
        end_year = end_date.get("year", end_date) if isinstance(end_date, dict) else (end_date or "Present")
        period = f"{start_year} - {end_year}" if start_year else ""
        
        experiences.append({
            "title": title,
            "company": company_name,
            "period": period,
            "description": exp.get("description", "")
        })

    education = []
    for edu in raw_data.get("education", []):
        education.append({
            "school": edu.get("schoolName", ""),
            "degree_name": edu.get("degreeName", ""),
            "field_of_study": edu.get("fieldOfStudy", "")
        })

    return {
        "full_name": raw_data.get("name", raw_data.get("fullName", raw_data.get("full_name", ""))),
        "first_name": raw_data.get("firstName", ""),
        "last_name": raw_data.get("lastName", ""),
        "headline": raw_data.get("headline", ""),
        "summary": raw_data.get("summary", raw_data.get("about", "")),
        "experiences": experiences,
        "education": education,
        "skills": [s.get("name", s) if isinstance(s, dict) else s for s in raw_data.get("skills", [])][:10],
        "city": raw_data.get("location", {}).get("city", "") if isinstance(raw_data.get("location"), dict) else raw_data.get("location", "")
    }
