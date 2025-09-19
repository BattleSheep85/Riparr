import redis
import json
import uuid
import os
import sys
import subprocess
import threading
import time

# Check if service is enabled
enable = os.getenv('ENABLE_RIP', 'false').lower() == 'true'
if not enable:
    print("Rip Worker disabled, exiting.")
    sys.exit(0)

# Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
r = redis.from_url(redis_url, decode_responses=True)


# Config
mkv_output_dir = os.getenv('MKV_OUTPUT_DIR', '/data/rips')
title_selection = os.getenv('TITLE_SELECTION', 'all')  # 'all' or specific title number
subtitle_policy = os.getenv('SUBTITLE_POLICY', 'retain')  # retain or discard
audio_policy = os.getenv('AUDIO_POLICY', 'retain')  # retain or discard

def process_drive_insert(drive_id, device):
    job_id = str(uuid.uuid4())
    output_dir = os.path.join(mkv_output_dir, job_id)

    # Ensure output dir exists
    os.makedirs(output_dir, exist_ok=True)

    # Publish rip.start
    start_msg = {
        "job_id": job_id,
        "drive_id": drive_id,
        "device": device,
        "output_dir": output_dir
    }
    r.xadd('rip_events', {'event': 'start', 'data': json.dumps(start_msg)})
    print(f"Published rip.start for job {job_id}")

    # Run MakeMKV
    cmd = ['makemkvcon', 'mkv', f'dev:{device}', title_selection, output_dir]
    if subtitle_policy == 'discard':
        cmd.append('--nosubtitles')
    if audio_policy == 'discard':
        cmd.append('--noaudio')

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Parse progress from stderr
        for line in iter(process.stderr.readline, ''):
            if line.startswith('PRGV:'):
                parts = line.split(',')
                if len(parts) >= 3:
                    current = int(parts[0].split(':')[1])
                    total = int(parts[1])
                    if total > 0:
                        percentage = int((current / total) * 100)
                        progress_msg = {
                            "job_id": job_id,
                            "percentage": percentage
                        }
                        r.xadd('rip_events', {'event': 'progress', 'data': json.dumps(progress_msg)})
                        print(f"Progress: {percentage}% for job {job_id}")

        process.wait()

        if process.returncode == 0:
            # Find output files
            output_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.mkv')]
            complete_msg = {
                "job_id": job_id,
                "output_files": output_files
            }
            r.xadd('rip_events', {'event': 'complete', 'data': json.dumps(complete_msg)})
            print(f"Published rip.complete for job {job_id}")
        else:
            print(f"MakeMKV failed for job {job_id}")

    except Exception as e:
        print(f"Error processing job {job_id}: {e}")

def main():
    last_id = '0'
    while True:
        try:
            messages = r.xread({'drive_events': last_id}, block=1000)
            for stream, msgs in messages:
                for msg_id, msg in msgs:
                    last_id = msg_id
                    data = json.loads(msg['data'])
                    if data.get('event') == 'insert':
                        threading.Thread(target=process_drive_insert, args=(data['drive_id'], data['device'])).start()
        except Exception as e:
            print(f"Error reading stream: {e}")
            time.sleep(1)

if __name__ == '__main__':
    print("Rip Worker started, waiting for drive events...")
    main()