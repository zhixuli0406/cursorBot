# CursorBot Dockerfile
# Use official Python 3.12 image (Debian Bookworm based)
FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For Playwright
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    # General utilities
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install Playwright browsers (chromium only for smaller size)
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy application code
COPY src/ ./src/

# Copy env.example as reference
COPY env.example .

# Create data directory for persistence
RUN mkdir -p /app/data

# Create non-root user for security
RUN useradd -m -u 1000 cursorbot && \
    chown -R cursorbot:cursorbot /app
USER cursorbot

# Expose port for API server (if needed)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command
CMD ["python", "-m", "src.main"]
