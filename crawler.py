import asyncio
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Try to import crawl4ai
CRAWL4AI_AVAILABLE = False
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    logger.info("Crawl4ai is not installed. Will default to raw Playwright for crawling.")

async def _crawl_with_crawl4ai(url: str) -> str:
    """Crawls using the crawl4ai library."""
    if not CRAWL4AI_AVAILABLE:
        raise ImportError("crawl4ai is not available")
        
    logger.info(f"Crawling with Crawl4ai: {url}")
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        # Crawl4ai returns result object with .markdown or .extracted_content
        if hasattr(result, "markdown") and result.markdown:
            return result.markdown
        elif hasattr(result, "html") and result.html:
            return result.html
        return str(result)

async def _crawl_with_playwright(url: str) -> str:
    """Fallback crawler using raw async Playwright to extract page text."""
    logger.info(f"Crawling with raw Playwright fallback: {url}")
    async with async_playwright() as p:
        try:
            # Launch headless chromium
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Go to the url with a reasonable timeout (30 seconds)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait a short moment to let dynamic content render
            await page.wait_for_timeout(2000)
            
            # Extract main readable text
            text_content = await page.evaluate("() => document.body.innerText")
            
            await browser.close()
            return text_content
        except Exception as e:
            logger.error(f"Raw Playwright crawling failed for {url}: {str(e)}")
            raise e

async def crawl_url(url: str) -> str:
    """
    Main entry point for crawling a webpage.
    Attempts Crawl4ai first, falls back to raw Playwright.
    """
    if not url:
        return ""
        
    # Attempt crawl4ai if installed
    if CRAWL4AI_AVAILABLE:
        try:
            return await _crawl_with_crawl4ai(url)
        except Exception as e:
            logger.warning(f"Crawl4ai execution failed: {str(e)}. Falling back to raw Playwright.")
            
    # Fallback to raw Playwright
    try:
        return await _crawl_with_playwright(url)
    except Exception as e:
        logger.error(f"All crawling methods failed for {url}: {str(e)}")
        return f"Error: Could not crawl page due to: {str(e)}"

# Helper sync wrapper to easily execute in sync code (like Streamlit callbacks)
def crawl_url_sync(url: str) -> str:
    try:
        # Check if there is an existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already running in a loop (e.g. within an async framework),
            # we need to execute it as a task or run in a thread/executor.
            # However, in Streamlit context, usually we run on standard threads.
            # We can use a helper to run it safely.
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(crawl_url(url))
        else:
            return loop.run_until_complete(crawl_url(url))
    except RuntimeError:
        # No event loop exists in this thread, create a new one
        return asyncio.run(crawl_url(url))
