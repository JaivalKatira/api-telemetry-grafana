# Recipe for building the API's container image.
# A small official Python image as the starting point
FROM python:3.12-slim

# Don't write .pyc files, and print logs straight away (no buffering)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first: Docker caches this layer, so rebuilding after a code
# change is fast as long as requirements.txt didn't change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy the application code
COPY main.py .

# Don't run as root inside the container
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Docker checks this every 30s; "docker ps" shows healthy/unhealthy
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
