import redis
import json
import uuid
import os
import sys
import subprocess
import threading
import time
import re
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if service is enabled
enable = os.getenv('ENABLE_ENHANCE', 'false').lower() == 'true'
if not enable:
    logger.info("Enhance Worker disabled, exiting.")
    sys.exit(0)

# Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
r = redis.from_url(redis_url, decode_responses=True)

# Config
esrgan_profile = os.getenv('ESRGAN_PROFILE', 'amd-4x-med-vram4')
gpu_vendor = os.getenv('GPU_VENDOR', 'amd')  # amd or nvidia
mkv_output_dir = os.getenv('MKV_OUTPUT_DIR', '/data/rips')
enhanced_output_dir = os.getenv('ENHANCED_OUTPUT_DIR', '/data/enhanced')
models_dir = os.getenv('MODELS_DIR', '/models')
use_cpu_fallback = os.getenv('CPU_FALLBACK', 'false').lower() == 'true'

def parse_profile(profile: str) -> Tuple[str, int, str, int]:
    """Parse ESRGAN profile string into components."""
    parts = profile.split('-')
    if len(parts) >= 4:
        vendor = parts[0]
        scale = int(parts[1].replace('x', ''))
        quality = parts[2]
        vram = int(parts[3].replace('vram', ''))
        return vendor, scale, quality, vram
    return 'amd', 4, 'med', 4

vendor, scale, quality, vram = parse_profile(esrgan_profile)

# Model selection based on quality
MODEL_MAP = {
    'low': 'realesr-animevideov3-x2',
    'med': 'realesr-animevideov3-x4',
    'high': 'realesrgan-x4plus-anime'
}
model = MODEL_MAP.get(quality, 'realesr-animevideov3-x4')

def is_hdr_file(file_path):
    # Use ffprobe to check for HDR
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                color_primaries = stream.get('color_primaries', '')
                if 'bt2020' in color_primaries.lower() or 'hdr' in str(stream).lower():
                    return True
        return False
    except Exception as e:
        print(f"Error checking HDR for {file_path}: {e}")
        return False

def enhance_file(input_file, output_file, job_id):
    # Determine if GPU or CPU
    if gpu_vendor == 'amd' and not use_cpu_fallback:
        binary = 'realesrgan-ncnn-vulkan'
        cmd = [binary, '-i', input_file, '-o', output_file, '-m', os.path.join(models_dir, model), '-s', str(scale), '-g', '0']
    else:
        binary = 'realesrgan-ncnn'
        cmd = [binary, '-i', input_file, '-o', output_file, '-m', os.path.join(models_dir, model), '-s', str(scale)]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Publish progress (simplified, as realesrgan may not have progress)
        progress_msg = {
            "job_id": job_id,
            "percentage": 50  # Mid progress
        }
        r.xadd('enhance_events', {'event': 'progress', 'data': json.dumps(progress_msg)})
        print(f"Enhancing {input_file} to {output_file}")

        process.wait()
        if process.returncode == 0:
            return True
        else:
            print(f"Enhance failed for {input_file}")
            return False
    except Exception as e:
        print(f"Error enhancing {input_file}: {e}")
        return False

def process_rip_complete(job_id, output_files):
    enhanced_files = []
    for mkv_file in output_files:
        if not mkv_file.endswith('.mkv'):
            continue
        if is_hdr_file(mkv_file):
            print(f"Skipping HDR file: {mkv_file}")
            enhanced_files.append(mkv_file)  # Pass through
            continue

        # Create output path
        rel_path = os.path.relpath(mkv_file, mkv_output_dir)
        output_file = os.path.join(enhanced_output_dir, rel_path)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        if enhance_file(mkv_file, output_file, job_id):
            enhanced_files.append(output_file)
        else:
            enhanced_files.append(mkv_file)  # Fallback to original

    # Publish complete
    complete_msg = {
        "job_id": job_id,
        "enhanced_files": enhanced_files
    }
    r.xadd('enhance_events', {'event': 'complete', 'data': json.dumps(complete_msg)})
    print(f"Published enhance.complete for job {job_id}")

def process_rip_event(data):
    if data.get('event') == 'complete':
        job_id = data['job_id']
        output_files = data['output_files']

        # Publish start
        start_msg = {
            "job_id": job_id,
            "input_files": output_files
        }
        r.xadd('enhance_events', {'event': 'start', 'data': json.dumps(start_msg)})
        print(f"Published enhance.start for job {job_id}")

        threading.Thread(target=process_rip_complete, args=(job_id, output_files)).start()

def main():
    last_id = '0'
    while True:
        try:
            messages = r.xread({'rip_events': last_id}, block=1000)
            for stream, msgs in messages:
                for msg_id, msg in msgs:
                    last_id = msg_id
                    data = json.loads(msg['data'])
                    process_rip_event(data)
        except Exception as e:
            print(f"Error reading stream: {e}")
            time.sleep(1)

if __name__ == '__main__':
    print("Enhance Worker started, waiting for rip events...")
    main()