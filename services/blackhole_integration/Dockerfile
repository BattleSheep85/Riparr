FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash blackhole

# Set working directory
WORKDIR /app

# Copy script
COPY blackhole_integration.py /app/

# Install Python dependencies
RUN pip3 install redis

# Switch to non-root user
USER blackhole

# Environment variables
ENV ENABLE_BLACKHOLE=true
ENV BLACKHOLE_PATH=/media/plex
ENV CLEANUP=true

# Volumes for blackhole output
VOLUME ["/media/plex"]

# Run the script
CMD ["python3", "/app/blackhole_integration.py"]