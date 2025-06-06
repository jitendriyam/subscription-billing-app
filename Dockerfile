# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Install system dependencies including Redis server
RUN apt-get update && apt-get install -y \
    redis-server \
    redis-tools \
    curl \
    build-essential \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements files
COPY pyproject.toml ./

# Install uv
RUN pip install uv

# Use uv to export requirements and install with pip (more reliable)
RUN uv export --format requirements-txt > requirements.txt && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Create startup script
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo '# Start Redis server in background' >> /app/start.sh && \
    echo 'redis-server --daemonize yes' >> /app/start.sh && \
    echo 'sleep 2' >> /app/start.sh && \
    echo 'case "${SERVICE:-fastapi}" in' >> /app/start.sh && \
    echo '  "fastapi")' >> /app/start.sh && \
    echo '    echo "Starting FastAPI server..."' >> /app/start.sh && \
    echo '    uvicorn app.main:app --host 0.0.0.0 --port 8000' >> /app/start.sh && \
    echo '    ;;' >> /app/start.sh && \
    echo '  "celery-worker")' >> /app/start.sh && \
    echo '    echo "Starting Celery worker..."' >> /app/start.sh && \
    echo '    celery -A app.celery_worker.celery_app worker -l info --pool=solo' >> /app/start.sh && \
    echo '    ;;' >> /app/start.sh && \
    echo '  "celery-beat")' >> /app/start.sh && \
    echo '    echo "Starting Celery beat..."' >> /app/start.sh && \
    echo '    celery -A app.celery_worker.celery_app beat -l info' >> /app/start.sh && \
    echo '    ;;' >> /app/start.sh && \
    echo '  "celery-combined")' >> /app/start.sh && \
    echo '    echo "Starting Celery worker and beat..."' >> /app/start.sh && \
    echo '    celery -A app.celery_worker.celery_app worker -l info --pool=solo --beat' >> /app/start.sh && \
    echo '    ;;' >> /app/start.sh && \
    echo '  *)' >> /app/start.sh && \
    echo '    echo "Unknown service: ${SERVICE}"' >> /app/start.sh && \
    echo '    echo "Available: fastapi, celery-worker, celery-beat, celery-combined"' >> /app/start.sh && \
    echo '    exit 1' >> /app/start.sh && \
    echo '    ;;' >> /app/start.sh && \
    echo 'esac' >> /app/start.sh

# Make the script executable
RUN chmod +x /app/start.sh

# Expose port for FastAPI
EXPOSE 8000

# Default command
CMD ["/app/start.sh"]