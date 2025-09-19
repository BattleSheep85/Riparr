FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    ffmpeg \
    python3 \
    python3-pip \
    vulkan-tools \
    mesa-vulkan-drivers \
    && rm -rf /var/lib/apt/lists/*

# Download Real-ESRGAN NCNN Vulkan binary
RUN wget -O /usr/local/bin/realesrgan-ncnn-vulkan https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/download/v0.2.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip \
    && unzip /usr/local/bin/realesrgan-ncnn-vulkan.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/realesrgan-ncnn-vulkan \
    && rm /usr/local/bin/realesrgan-ncnn-vulkan.zip

# Download CPU version
RUN wget -O /usr/local/bin/realesrgan-ncnn https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/download/v0.2.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip \
    && unzip /usr/local/bin/realesrgan-ncnn.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/realesrgan-ncnn \
    && rm /usr/local/bin/realesrgan-ncnn.zip

# Download models
RUN mkdir -p /models && \
    wget -O /models/models.zip https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-models.zip \
    && unzip /models/models.zip -d /models/ \
    && rm /models/models.zip

# Create non-root user
RUN useradd -m -s /bin/bash enhancer

# Set working directory
WORKDIR /app

# Copy script
COPY enhance_worker.py /app/

# Install Python dependencies
RUN pip3 install redis

# Switch to non-root user
USER enhancer

# Environment variables
ENV ENABLE_ENHANCE=true
ENV ESRGAN_PROFILE=amd-4x-med-vram4
ENV GPU_VENDOR=amd
ENV MKV_OUTPUT_DIR=/data/rips
ENV ENHANCED_OUTPUT_DIR=/data/enhanced
ENV MODELS_DIR=/models
ENV CPU_FALLBACK=false

# Run the script
CMD ["python3", "/app/enhance_worker.py"]