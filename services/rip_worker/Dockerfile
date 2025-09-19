FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Add MakeMKV repository (assuming it's available)
# Note: MakeMKV requires manual license setup
RUN wget -q -O - https://www.makemkv.com/download/makemkv.gpg | apt-key add - && \
    echo "deb https://www.makemkv.com/download/ubuntu jammy main" >> /etc/apt/sources.list.d/makemkv.list && \
    apt-get update && apt-get install -y makemkv-bin makemkv-oss && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash ripper && \
    usermod -a -G cdrom ripper

# Set working directory
WORKDIR /app

# Copy script
COPY rip_worker.py /app/

# Install Python and redis
RUN apt-get update && apt-get install -y python3 python3-pip && \
    pip3 install redis pyudev && \
    rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER ripper

# Environment variables
ENV ENABLE_RIP=true
ENV MKV_OUTPUT_DIR=/data/rips
ENV TITLE_SELECTION=all
ENV SUBTITLE_POLICY=retain
ENV AUDIO_POLICY=retain

# Run the script
CMD ["python3", "/app/rip_worker.py"]