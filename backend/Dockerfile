# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app
COPY ./migrations ./migrations

# Create non-root user and uploads directory with proper permissions
RUN adduser --disabled-password --gecos "" --home /app appuser \
    && mkdir -p /app/uploads /app/media \
    && chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port (documentation only — Railway injects $PORT at runtime)
EXPOSE 8000

# Run the application. Shell-form CMD so ${PORT} expands at runtime:
# Railway injects $PORT; locally it falls back to 8000.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
