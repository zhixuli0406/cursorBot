# CursorBot Dockerfile
# Use official Python 3.12 image (Debian Bookworm based)
FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    RUNNING_IN_DOCKER=true \
    # Set default workspace path in container
    DOCKER_WORKSPACE_PATH=/workspace

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright, development tools, and common utilities
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
    # Development tools
    git \
    openssh-client \
    # Build tools (for npm packages that require compilation)
    build-essential \
    # General utilities
    curl \
    wget \
    unzip \
    zip \
    jq \
    tree \
    htop \
    procps \
    nano \
    vim-tiny \
    # Network utilities
    iputils-ping \
    dnsutils \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x LTS (for npm/node commands)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest && \
    rm -rf /var/lib/apt/lists/*

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

# Copy skills directory (for custom agent skills)
COPY skills/ ./skills/

# Copy env.example as reference
COPY env.example .

# Create data directory for persistence
RUN mkdir -p /app/data

# Ensure skills directory exists with proper permissions
RUN mkdir -p /app/skills/agent

# Create workspace directory with proper permissions
# This will be the mount point for user's projects
RUN mkdir -p /workspace && chmod 777 /workspace

# Create non-root user for security with proper home directory
RUN useradd -m -u 1000 -s /bin/bash cursorbot && \
    chown -R cursorbot:cursorbot /app && \
    # Allow cursorbot to write to workspace
    chown cursorbot:cursorbot /workspace && \
    # Setup git config for cursorbot user
    mkdir -p /home/cursorbot/.config && \
    chown -R cursorbot:cursorbot /home/cursorbot

# Switch to non-root user
USER cursorbot

# Set git safe directory (for mounted volumes)
RUN git config --global --add safe.directory '*'

# Set default shell environment
ENV HOME=/home/cursorbot \
    SHELL=/bin/bash

# Expose port for API server (if needed)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command
CMD ["python", "-m", "src.main"]
