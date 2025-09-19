FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    docker \
    pyyaml \
    redis

# Set working directory
WORKDIR /app

# Copy the orchestrator script
COPY orchestrator.py .

# Default config path
ENV CONFIG_PATH=/config/config.yaml

# Run the orchestrator
CMD ["python", "orchestrator.py"]