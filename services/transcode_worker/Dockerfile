FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3 \
    python3-pip \
    libva-drm2 \
    libva2 \
    mesa-va-drivers \
    vainfo \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash transcode

# Set working directory
WORKDIR /app

# Copy script
COPY transcode_worker.py /app/

# Install Python dependencies
RUN pip3 install redis

# Switch to non-root user
USER transcode

# Environment variables
ENV ENABLE_TRANSCODE=true
ENV VAAPI_PROFILE=hevc_vaapi
ENV TRANSCODE_PROFILE=high
ENV ENHANCED_OUTPUT_DIR=/data/enhanced
ENV TRANSCODED_OUTPUT_DIR=/data/transcoded
ENV CPU_FALLBACK=false
ENV AUDIO_FORMAT=aac

# Run the script
CMD ["python3", "/app/transcode_worker.py"]