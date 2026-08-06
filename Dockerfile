FROM python:3.11-slim

# Install minimal helper packages
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser and let it automatically download correct system dependencies
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium

# Copy application files
COPY . .

# Create downloads folder for PDF storage
RUN mkdir -p downloads

# Run the app on the port provided by Railway, defaulting to 8501
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
