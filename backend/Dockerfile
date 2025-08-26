# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Prevent interactive prompts
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies (Python build deps, git, curl, etc.)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      git \
      curl \
      build-essential \
 && rm -rf /var/lib/apt/lists/*


RUN curl -fsSL https://deb.nodesource.com/setup_23.x | bash - \
 && apt-get install -y nodejs \
 && npm install -g npm@10.9.2 \
 && npm install -g @openai/codex@0.1.2505172129


# Create non-root user
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

ENV PATH="/opt/venv/bin:${PATH}"

# Copy the rest of the project
COPY . .

# Ensure logs directory exists
RUN mkdir -p /app/logs \
 && chown -R appuser:appuser /app

EXPOSE 8000
USER appuser

# Healthcheck (TCP check on port 8000)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 8000)); s.close()" || exit 1

# Default environment (workers configurable at runtime)
ENV UVICORN_WORKERS=1

# Start FastAPI app (main:app is assumed; override if needed)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1}"]
