FROM python:3.9-slim

# Install system dependencies for pyudev
RUN apt-get update && apt-get install -y \
    libudev-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir pyudev redis

# Create non-root user and add to cdrom group
RUN useradd -m appuser && usermod -a -G cdrom appuser

# Set working directory
WORKDIR /app

# Copy the script
COPY drive_watcher.py /app/drive_watcher.py

# Switch to non-root user
USER appuser

# Run the script
CMD ["python", "/app/drive_watcher.py"]