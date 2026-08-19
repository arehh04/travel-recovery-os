# Stage 1: Build frontend
FROM node:20.18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime with built frontend
FROM python:3.12.8-slim
WORKDIR /app

# Build metadata (Phase 10)
ARG BUILD_VERSION=0.10.0
ARG COMMIT_SHA=unknown
LABEL org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.revision="${COMMIT_SHA}" \
      org.opencontainers.image.title="TR-OS Mission API" \
      org.opencontainers.image.description="AI-powered travel disruption recovery API" \
      maintainer="TR-OS Team"

# Create non-root user
RUN useradd -m -r appuser

# Create data directory for SQLite
RUN mkdir -p /app/data && chown appuser:appuser /app/data

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY tros/ tros/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist /app/static

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

# Graceful shutdown
STOPSIGNAL SIGTERM

# Environment
ENV TR_OS_API_HOST=0.0.0.0
ENV TR_OS_API_PORT=8000
ENV TR_OS_BUILD_VERSION=${BUILD_VERSION}
ENV TR_OS_COMMIT_SHA=${COMMIT_SHA}

# Run
CMD ["uvicorn", "tros.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
