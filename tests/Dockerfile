FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    redis-tools \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /tests

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy test files
COPY . .

# Environment variables
ENV PYTHONPATH=/tests
ENV REDIS_URL=redis://redis:6379

# Run tests
CMD ["pytest", "-v", "--tb=short"]