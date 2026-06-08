FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (including pg_isready dependencies if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY src/backend/requirements.txt /app/src/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/src/backend/requirements.txt

# Copy source files (including backend src folder)
COPY src /app/src

EXPOSE 8000

# Run uvicorn starting from root folder
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
