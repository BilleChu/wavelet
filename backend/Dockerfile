# OpenFinance Backend Dockerfile
# Multi-stage build for optimized production image with debug support

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY pyproject.toml requirements.txt* ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt 2>/dev/null || \
    pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings email-validator \
    langchain langgraph langchain-openai langchain-community \
    redis psycopg2-binary sqlalchemy alembic \
    httpx aiohttp websockets python-multipart \
    pytest pytest-asyncio pytest-cov debugpy

# ============================================
# Stage 2: Development (with debug tools)
# ============================================
FROM python:3.11-slim as development

WORKDIR /app

# Install system dependencies and debug tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    vim \
    less \
    procps \
    net-tools \
    iputils-ping \
    gdb \
    python3-dbg \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install additional development tools
RUN pip install --no-cache-dir \
    debugpy \
    ipython \
    ipdb \
    watchfiles \
    rich

# Set environment variables for development
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV DEBUG=1

# Create directories
RUN mkdir -p /app/logs /app/data

# Copy application code
COPY . .

# Expose ports
# 19100: Application
# 5678: Debugpy debugger
# 9001: Prometheus metrics
EXPOSE 19100 5678 9001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:19100/api/health || exit 1

# Development entrypoint with debug support
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", \
     "-m", "uvicorn", "openfinance.api.main:app", "--host", "0.0.0.0", "--port", "19100", "--reload"]

# ============================================
# Stage 3: Production
# ============================================
FROM python:3.11-slim as production

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV DEBUG=0

# Create directories and set permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 19100

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:19100/api/health || exit 1

# Production entrypoint
CMD ["uvicorn", "openfinance.api.main:app", "--host", "0.0.0.0", "--port", "19100", \
     "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]
