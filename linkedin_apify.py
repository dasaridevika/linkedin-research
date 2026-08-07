import requests
import logging
import time

logger = logging.getLogger(__name__)

def scrape_profile_apify(profile_url: str, apify_token: str) -> dict:
    """
    Runs the Apify LinkedIn Profile Scraper actor and returns the structured JSON dataset.
    Uses Apify's run-sync endpoint to wait for results (timeout 60 seconds).
    
    Actor used: 'apify/linkedin-profile-scraper' (or equivalent community scraper).
    """
    if not apify_token:
        logger.error("Apify API Token is missing.")
        return {"error": "Apify API Token is missing"}

    # Clean the profile URL
    profile_url = profile_url.strip()
    if not profile_url.startswith("http"):
        profile_url = f"https://www.linkedin.com/in/{profile_url}"

    # Apify API endpoint for running an actor synchronously and getting dataset items
    # Actor: 'dtrungtin/linkedin-profile-scraper' or 'bebity/linkedin-profile-scraper' are popular,
    # but the standard actor is 'apify/linkedin-profile-scraper' (requires a premium proxy proxy or standard login).
    # Let's use the popular and reliable 'bebity/linkedin-profile-scraper' or 'curious_coder/linkedin-profile-scraper' 
    # which works well on free/trial tiers.
    actor_id = "leadsman~linkedin-profile-scraper"
    url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Payload configuring the scraper to target the profile
    payload = {
        "urls": [profile_url],
        "proxyConfiguration": {
            "useApifyProxy": True
        }
    }
    
    params = {
        "token": apify_token,
        "timeout": 60 # 60 second timeout for synchronous execution
    }

    try:
        logger.info(f"Triggering Apify LinkedIn Scraper for URL: {profile_url}")
        response = requests.post(url, json=payload, headers=headers, params=params, timeout=70)
        
        if response.status_code == 201 or response.status_code == 200:
            dataset_items = response.json()
            if isinstance(dataset_items, list) and len(dataset_items) > 0:
                # The response is a list of scraped profiles, return the first one
                profile_data = dataset_items[0]
                logger.info("Successfully fetched profile data from Apify.")
                return _parse_apify_profile(profile_data)
            else:
                logger.warning("Apify completed but returned an empty dataset.")
                return {"error": "Empty dataset returned from scraper"}
        else:
            logger.error(f"Apify API returned error status {response.status_code}: {response.text}")
            return {"error": f"Apify error {response.status_code}: {response.text}"}
            
    except Exception as e:
        logger.error(f"Failed to query Apify API: {str(e)}")
        return {"error": f"Apify query failed: {str(e)}"}

def _parse_apify_profile(raw_data: dict) -> dict:
    """
    Standardizes Apify's JSON layout to match the expected schema in our PDF/Gemini synthesizers.
    """
    # Extract experiences
    experiences = []
    for exp in raw_data.get("positions", raw_data.get("experience", [])):
        company_name = exp.get("companyName", exp.get("company", ""))
        title = exp.get("title", "")
        start_date = exp.get("startDate", {})
        end_date = exp.get("endDate", {})
        
        start_year = start_date.get("year", "") if isinstance(start_date, dict) else ""
        end_year = end_date.get("year", "Present") if isinstance(end_date, dict) else "Present"
        period = f"{start_year} - {end_year}" if start_year else ""
        
        experiences.append({
            "title": title,
            "company": company_name,
            "period": period,
            "description": exp.get("description", "")
        })

    # Extract education
    education = []
    for edu in raw_data.get("education", []):
        education.append({
            "school": edu.get("schoolName", ""),
            "degree_name": edu.get("degreeName", ""),
            "field_of_study": edu.get("fieldOfStudy", "")
        })

    # Standardize output profile schema
    return {
        "full_name": raw_data.get("name", raw_data.get("fullName", "")),
        "first_name": raw_data.get("firstName", ""),
        "last_name": raw_data.get("lastName", ""),
        "headline": raw_data.get("headline", ""),
        "summary": raw_data.get("summary", ""),
        "experiences": experiences,
        "education": education,
        "skills": [s.get("name", s) for s in raw_data.get("skills", [])][:10],
        "city": raw_data.get("location", {}).get("city", "") if isinstance(raw_data.get("location"), dict) else raw_data.get("location", "")
    }
