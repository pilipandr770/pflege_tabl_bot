# Use Python 3.10 as base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies including Chrome for Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver (webdriver-manager will handle this dynamically)
# But we still need the Chrome binary to be present

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code files
COPY bot.py scraper.py config-example.py ./
COPY .env* ./

# Create directories for screenshots and results
RUN mkdir -p screenshots

# Set environment variables
ENV SELENIUM_HEADLESS=true

# You can also use a .env file which will be read by python-dotenv
# When using this container, you should either:
# 1. Mount a volume with your .env file: -v /path/to/.env:/app/.env
# 2. Pass environment variables directly: -e BOT_TOKEN=your_bot_token_here

# Command to run the bot
CMD ["python", "bot.py"]
