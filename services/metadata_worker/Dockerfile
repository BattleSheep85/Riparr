FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash metadata

# Set working directory
WORKDIR /app

# Copy script
COPY metadata_worker.py /app/

# Install Python dependencies
RUN pip3 install redis ollama

# Switch to non-root user
USER metadata

# Environment variables
ENV ENABLE_METADATA=true
ENV OLLAMA_MODEL=llama2
ENV METADATA_DIR=/data/metadata

# Volumes for metadata output
VOLUME ["/data/metadata"]

# Run the script
CMD ["python3", "/app/metadata_worker.py"]