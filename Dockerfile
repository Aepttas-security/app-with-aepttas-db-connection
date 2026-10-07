FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY caller_backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY caller_backend/ /app/caller_backend/
WORKDIR /app/caller_backend

EXPOSE 5000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
