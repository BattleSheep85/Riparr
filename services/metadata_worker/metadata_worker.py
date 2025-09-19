import redis
import json
import os
import sys
import ollama

# Check if service is enabled
enable = os.getenv('ENABLE_METADATA', 'false').lower() == 'true'
if not enable:
    print("Metadata Worker disabled, exiting.")
    sys.exit(0)

# Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
r = redis.from_url(redis_url, decode_responses=True)

# Config
ollama_model = os.getenv('OLLAMA_MODEL', 'llama2')
metadata_dir = os.getenv('METADATA_DIR', '/data/metadata')
os.makedirs(metadata_dir, exist_ok=True)

def normalize_title(filename):
    # Extract title from filename
    title = os.path.splitext(filename)[0]
    
    # Call Ollama
    prompt = f"Normalize this movie title: '{title}'. Provide a clean title, year if available, directory structure like /Movies/Title (Year)/, and file pattern like Title (Year).mkv. Respond in JSON format with keys: normalized_title, directory, file_pattern."
    
    try:
        response = ollama.chat(model=ollama_model, messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content']
        # Parse JSON
        metadata = json.loads(content)
        return metadata
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return {
            'normalized_title': title,
            'directory': '/Movies/',
            'file_pattern': f"{title}.mkv"
        }

def process_transcode_complete(job_id, transcoded_files):
    metadata_list = []
    for file_path in transcoded_files:
        filename = os.path.basename(file_path)
        metadata = normalize_title(filename)
        metadata['original_file'] = file_path
        metadata['job_id'] = job_id
        metadata_list.append(metadata)
        
        # Create side-car JSON
        json_path = os.path.join(metadata_dir, f"{job_id}_{filename}.json")
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    # Publish complete
    complete_msg = {
        "job_id": job_id,
        "metadata": metadata_list
    }
    r.xadd('metadata_events', {'event': 'complete', 'data': json.dumps(complete_msg)})
    print(f"Published metadata.complete for job {job_id}")

def process_transcode_event(data):
    if data.get('event') == 'complete':
        job_id = data['job_id']
        transcoded_files = data['transcoded_files']
        
        # Publish start
        start_msg = {
            "job_id": job_id,
            "input_files": transcoded_files
        }
        r.xadd('metadata_events', {'event': 'start', 'data': json.dumps(start_msg)})
        print(f"Published metadata.start for job {job_id}")
        
        # Process
        process_transcode_complete(job_id, transcoded_files)

def main():
    last_id = '0'
    while True:
        try:
            messages = r.xread({'transcode_events': last_id}, block=1000)
            for stream, msgs in messages:
                for msg_id, msg in msgs:
                    last_id = msg_id
                    data = json.loads(msg['data'])
                    process_transcode_event(data)
        except Exception as e:
            print(f"Error reading stream: {e}")
            import time
            time.sleep(1)

if __name__ == '__main__':
    print("Metadata Worker started, waiting for transcode events...")
    main()