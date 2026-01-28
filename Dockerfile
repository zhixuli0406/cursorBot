# CursorBot Dockerfile - v0.4
# Multi-stage build for optimized image size
# Stage 1: Build dependencies
# Stage 2: Runtime image

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.12-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.12-slim-bookworm AS runtime

LABEL maintainer="CursorBot Team"
LABEL version="0.4.0"
LABEL description="CursorBot - Multi-platform AI Assistant"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RUNNING_IN_DOCKER=true \
    DOCKER_WORKSPACE_PATH=/workspace \
    PATH="/opt/venv/bin:$PATH" \
    # Python optimization
    PYTHONOPTIMIZE=1

WORKDIR /app

# Install only runtime dependencies (smaller footprint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For Playwright (minimal set)
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
    # Essential tools
    git \
    openssh-client \
    curl \
    jq \
    # Process tools
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Install Node.js 20.x LTS (minimal)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g npm@latest && \
    rm -rf /var/lib/apt/lists/* \
    && npm cache clean --force

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Install Playwright browsers (chromium only)
RUN playwright install chromium && \
    playwright install-deps chromium && \
    rm -rf /root/.cache

# Create directories
RUN mkdir -p /app/data /app/logs /app/skills/agent /workspace

# Copy application code
COPY src/ ./src/
COPY skills/ ./skills/
COPY env.example .
COPY CHANGELOG.md README.md ./

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash cursorbot && \
    chown -R cursorbot:cursorbot /app /workspace && \
    mkdir -p /home/cursorbot/.config && \
    chown -R cursorbot:cursorbot /home/cursorbot

# Switch to non-root user
USER cursorbot

# Configure git
RUN git config --global --add safe.directory '*' && \
    git config --global user.name "CursorBot" && \
    git config --global user.email "bot@cursorbot.local"

# Set home environment
ENV HOME=/home/cursorbot \
    SHELL=/bin/bash

# Expose API port
EXPOSE 8000

# Health check - v0.4 enhanced
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# Default command
CMD ["python", "-m", "src.main"]

# ============================================
# Build Info
# ============================================
# Build: docker build -t cursorbot:0.4.0 .
# Run:   docker run -d --name cursorbot -p 8000:8000 --env-file .env cursorbot:0.4.0
# Size:  ~1.2GB (with Playwright)
# 
# Without Playwright (smaller ~600MB):
# docker build --build-arg INSTALL_PLAYWRIGHT=false -t cursorbot:0.4.0-slim .
