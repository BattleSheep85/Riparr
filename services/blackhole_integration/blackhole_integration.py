import redis
import json
import os
import sys
import shutil

# Check if service is enabled
enable = os.getenv('ENABLE_BLACKHOLE', 'false').lower() == 'true'
if not enable:
    print("Blackhole Integration disabled, exiting.")
    sys.exit(0)

# Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
r = redis.from_url(redis_url, decode_responses=True)

# Config
blackhole_path = os.getenv('BLACKHOLE_PATH', '/media/plex')
cleanup = os.getenv('CLEANUP', 'true').lower() == 'true'
os.makedirs(blackhole_path, exist_ok=True)

def create_sidecar_nfo(metadata, target_dir):
    nfo_path = os.path.join(target_dir, f"{metadata['normalized_title']}.nfo")
    with open(nfo_path, 'w') as f:
        f.write(f"Title: {metadata['normalized_title']}\n")
        f.write(f"Original File: {metadata['original_file']}\n")
        f.write(f"Job ID: {metadata['job_id']}\n")
    return nfo_path

def process_metadata_complete(job_id, metadata_list):
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
        
        # Cleanup if enabled
        if cleanup:
            # Original file already moved, but if there are other files like metadata JSON, could clean them
            pass
    
    # Publish complete
    complete_msg = {
        "job_id": job_id,
        "moved_files": moved_files
    }
    r.xadd('blackhole_events', {'event': 'complete', 'data': json.dumps(complete_msg)})
    print(f"Published blackhole.complete for job {job_id}")

def process_metadata_event(data):
    if data.get('event') == 'complete':
        job_id = data['job_id']
        metadata_list = data['metadata']
        
        # Publish start
        start_msg = {
            "job_id": job_id,
            "metadata": metadata_list
        }
        r.xadd('blackhole_events', {'event': 'start', 'data': json.dumps(start_msg)})
        print(f"Published blackhole.start for job {job_id}")
        
        # Process
        process_metadata_complete(job_id, metadata_list)

def main():
    last_id = '0'
    while True:
        try:
            messages = r.xread({'metadata_events': last_id}, block=1000)
            for stream, msgs in messages:
                for msg_id, msg in msgs:
                    last_id = msg_id
                    data = json.loads(msg['data'])
                    process_metadata_event(data)
        except Exception as e:
            print(f"Error reading stream: {e}")
            import time
            time.sleep(1)

if __name__ == '__main__':
    print("Blackhole Integration started, waiting for metadata events...")
    main()