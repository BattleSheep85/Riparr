import redis
import json
import os
import sys
import shutil
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if service is enabled
enable = os.getenv('ENABLE_BLACKHOLE', 'false').lower() == 'true'
if not enable:
    logger.info("Blackhole Integration disabled, exiting.")
    sys.exit(0)

# Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
r = redis.from_url(redis_url, decode_responses=True)

# Config
blackhole_path = os.getenv('BLACKHOLE_PATH', '/media/plex')
os.makedirs(blackhole_path, exist_ok=True)

def create_sidecar_nfo(metadata: Dict[str, Any], target_dir: str) -> str:
    nfo_path = os.path.join(target_dir, f"{metadata['normalized_title']}.nfo")
    with open(nfo_path, 'w') as f:
        f.write(f"Title: {metadata['normalized_title']}\n")
        f.write(f"Original File: {metadata['original_file']}\n")
        f.write(f"Job ID: {metadata['job_id']}\n")
    return nfo_path

def process_metadata_complete(job_id: str, metadata_list: List[Dict[str, Any]]) -> None:
    moved_files = []
    for metadata in metadata_list:
        original_file = metadata['original_file']
        directory = metadata['directory']
        file_pattern = metadata['file_pattern']
        
        # Create target directory
        target_dir = os.path.join(blackhole_path, directory.lstrip('/'))
        os.makedirs(target_dir, exist_ok=True)
        
        # Move file
        target_file = os.path.join(target_dir, file_pattern)
        shutil.move(original_file, target_file)
        moved_files.append(target_file)
        
        # Create side-car .nfo
        create_sidecar_nfo(metadata, target_dir)
    
    # Publish complete
    complete_msg = {
        "job_id": job_id,
        "moved_files": moved_files
    }
    r.xadd('blackhole_events', {'event': 'complete', 'data': json.dumps(complete_msg)})
    logger.info(f"Published blackhole.complete for job {job_id}")

def process_metadata_event(data: Dict[str, Any]) -> None:
    if data.get('event') == 'complete':
        job_id = data['job_id']
        metadata_list = data['metadata']
        
        # Publish start
        start_msg = {
            "job_id": job_id,
            "metadata": metadata_list
        }
        r.xadd('blackhole_events', {'event': 'start', 'data': json.dumps(start_msg)})
        logger.info(f"Published blackhole.start for job {job_id}")
        
        # Process
        process_metadata_complete(job_id, metadata_list)

def main() -> None:
    last_id = '0'
    while True:
        try:
            messages = r.xread({'metadata_events': last_id}, block=1000)
            for stream, msgs in messages:
                for msg_id, msg in msgs:
                    last_id = msg_id
                    data = json.loads(msg['data'])
                    process_metadata_event(data)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis connection error: {e}")
            import time
            time.sleep(1)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            import time
            time.sleep(1)
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            import time
            time.sleep(1)

if __name__ == '__main__':
    logger.info("Blackhole Integration started, waiting for metadata events...")
    main()