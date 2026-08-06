# LinkedIn Lead Research Test Unit

A premium, single-service Streamlit application to research individual email IDs and usernames across web searches (aggregated via a **Cloudflare Worker**), crawl relevant pages using **Playwright/Crawl4ai**, and generate a beautiful executive intelligence PDF report.

This application is ready for local execution and single-service deployment on **Railway**.

---

## Technical Architecture

The system operates on a serverless + container hybrid architecture:
1. **Cloudflare Worker** (`worker/index.js`): A lightweight, globally distributed search API proxy. It receives the lead's username and email, securely executes search engine queries (Tavily/Serper), and returns unified snippets.
2. **Streamlit App (Railway)**: The main user interface and processing core. It calls the Cloudflare Worker to fetch search logs, uses **Playwright** locally to crawl details, synthesizes the payload using **Google Gemini**, and compiles the PDF.

---

## 1. Cloudflare Worker Deployment

To deploy the search proxy worker:
1. Navigate to the `worker/` directory:
   ```bash
   cd worker
   ```
2. Deploy wrangler using your Cloudflare account (or run locally):
   ```bash
   npx wrangler deploy
   ```
3. Set your search engine API keys in your Cloudflare dashboard (under Workers Settings > Variables) or set them in wrangler secrets:
   ```bash
   npx wrangler secret put TAVILY_API_KEY
   # or
   npx wrangler secret put SERPER_API_KEY
   ```
4. Note your deployed worker URL (e.g. `https://search-proxy.username.workers.dev`).

---

## 2. Streamlit Local Setup

### Installation
Ensure you have **Python 3.10+** installed:
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
python -m playwright install chromium
python -m playwright install-deps chromium
```

### Environment Variables (`.env`)
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your-gemini-api-key
CLOUDFLARE_WORKER_URL=https://your-worker-url.workers.dev
APIFY_TOKEN=your-apify-token  # Optional: For active LinkedIn scraping (Free $5/month)
```

### Launch
```bash
streamlit run app.py
```

---

## 3. Railway Deployment

This app deploys as a **single service** containing both the Streamlit UI and the Playwright web crawler runtime.

1. **Git Commit**: Initialize a Git repository and commit your files:
   ```bash
   git init
   git add .
   git commit -m "feat: setup lead research worker integration"
   ```
2. **Deploy on Railway**: Create a new project pointing to your GitHub repository.
3. **Configure Railway Variables**:
   - `GEMINI_API_KEY`
   - `CLOUDFLARE_WORKER_URL`
   - `APIFY_TOKEN` (Optional: Enables profile scraping)
   - `PORT` (Provided by Railway automatically)
