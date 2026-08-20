# CWE-494 (intentional review finding): unpinned mutable 'latest' base image.
FROM python:latest

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lead_tracker_api ./lead_tracker_api

# CWE-250 (intentional review finding): no non-root USER directive declared, so
# the container runs as root by default.
EXPOSE 8000
CMD ["python", "-m", "lead_tracker_api.main"]
