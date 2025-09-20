"""Transcode Worker service.

Monitors enhance events and processes video transcoding using FFmpeg with VAAPI.
"""
import json
import os
import sys
import subprocess
import threading
import time
import re

import redis

# Check if service is enabled
enable = os.getenv('ENABLE_TRANSCODE', 'false').lower() == 'true'
if not enable:
    print("Transcode Worker disabled, exiting.")
    sys.exit(0)

# Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
r = redis.from_url(redis_url, decode_responses=True)

# Config
vaapi_profile = os.getenv('VAAPI_PROFILE', 'hevc_vaapi')
transcode_profile = os.getenv('TRANSCODE_PROFILE', 'high')  # high, medium, low
enhanced_output_dir = os.getenv('ENHANCED_OUTPUT_DIR', '/data/enhanced')
transcoded_output_dir = os.getenv('TRANSCODED_OUTPUT_DIR', '/data/transcoded')
cpu_fallback = os.getenv('CPU_FALLBACK', 'false').lower() == 'true'
audio_format = os.getenv('AUDIO_FORMAT', 'aac')  # aac or opus for stereo

# Profile mappings
profile_settings = {
    'high': {'global_quality': 28, 'qp': 22},
    'medium': {'global_quality': 25, 'qp': 20},
    'low': {'global_quality': 22, 'qp': 18}
}

settings = profile_settings.get(transcode_profile, profile_settings['high'])

def get_audio_info(file_path):
    """Get audio stream information from a media file using ffprobe."""
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        data = json.loads(result.stdout)
        audio_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
        return audio_streams
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error probing {file_path}: {e}")
        return []

def build_ffmpeg_cmd(input_file, output_file, audio_streams):
    """Build FFmpeg command for transcoding with appropriate audio and video settings."""
    cmd = ['ffmpeg', '-y']
    if not cpu_fallback:
        cmd.extend(['-hwaccel', 'vaapi', '-hwaccel_device', '/dev/dri/renderD128'])
        cmd.extend(['-i', input_file])
        cmd.extend([
            '-c:v', vaapi_profile, '-global_quality', str(settings['global_quality']),
            '-qp', str(settings['qp'])
        ])
    else:
        cmd.extend(['-i', input_file])
        cmd.extend(['-c:v', 'libx265', '-crf', str(settings['global_quality'])])  # Approximate CRF

    # Audio mapping
    audio_filters = []
    for i, stream in enumerate(audio_streams):
        channels = stream.get('channels', 2)
        if channels > 2:
            # Surround: EAC3
            cmd.extend([f'-c:a:{i}', 'eac3'])
            if channels > 6:
                audio_filters.append(
                    f'[0:a:{i}]pan=5.1|c0=c0|c1=c1|c2=c2|c3=c3|c4=c4|c5=c5[a{i}]'
                )
        else:
            # Stereo: AAC or OPUS
            codec = 'libopus' if audio_format == 'opus' else 'aac'
            cmd.extend([f'-c:a:{i}', codec])

    if audio_filters:
        cmd.extend(['-filter_complex', ','.join(audio_filters)])

    cmd.append(output_file)
    return cmd

def transcode_file(input_file, output_file, job_id):
    """Transcode a media file using FFmpeg and report progress."""
    try:
        with subprocess.Popen(
            build_ffmpeg_cmd(input_file, output_file, get_audio_info(input_file)),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        ) as process:
            duration = None
            # Get duration first
            try:
                probe_data = json.loads(
                    subprocess.run(
                        [
                            'ffprobe', '-v', 'quiet', '-print_format', 'json',
                            '-show_format', input_file
                        ],
                        capture_output=True, text=True, check=False
                    ).stdout
                )
                duration = float(probe_data['format']['duration'])
            except OSError:
                duration = None

            last_progress = 0
            for line in iter(process.stderr.readline, ''):
                if duration and 'time=' in line:
                    time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                    if time_match:
                        h, m, s = map(float, time_match.groups())
                        current_time = h * 3600 + m * 60 + s
                        progress = int((current_time / duration) * 100)
                        if progress >= last_progress + 10:  # Update every 10%
                            r.xadd(
                                'transcode_events',
                                {'event': 'progress', 'data': json.dumps({
                                    "job_id": job_id,
                                    "percentage": progress
                                })}
                            )
                            print(f"Transcode progress: {progress}% for job {job_id}")
                            last_progress = progress
            process.communicate()
        return process.returncode == 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"Error transcoding {input_file}: {e}")
        return False

def process_enhance_complete(job_id, enhanced_files):
    """Process enhanced files by transcoding them and publishing completion event."""
    transcoded_files = []
    for enhanced_file in enhanced_files:
        rel_path = os.path.relpath(enhanced_file, enhanced_output_dir)
        output_file = os.path.join(transcoded_output_dir, rel_path)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        if transcode_file(enhanced_file, output_file, job_id):
            transcoded_files.append(output_file)
        else:
            transcoded_files.append(enhanced_file)  # Fallback

    # Publish complete
    complete_msg = {
        "job_id": job_id,
        "transcoded_files": transcoded_files
    }
    r.xadd('transcode_events', {'event': 'complete', 'data': json.dumps(complete_msg)})
    print(f"Published transcode.complete for job {job_id}")

def process_enhance_event(data):
    """Process an enhance event by starting transcoding for completed jobs."""
    if data.get('event') == 'complete':
        job_id = data['job_id']
        enhanced_files = data['enhanced_files']

        # Publish start
        start_msg = {
            "job_id": job_id,
            "input_files": enhanced_files
        }
        r.xadd('transcode_events', {'event': 'start', 'data': json.dumps(start_msg)})
        print(f"Published transcode.start for job {job_id}")

        threading.Thread(target=process_enhance_complete, args=(job_id, enhanced_files)).start()

def main():
    """Main event loop: listen for enhance events and process them."""
    last_id = '0'
    while True:
        try:
            messages = r.xread({'enhance_events': last_id}, block=1000)
            for _, msgs in messages:
                for msg_id, msg in msgs:
                    last_id = msg_id
                    data = json.loads(msg['data'])
                    process_enhance_event(data)
        except OSError as e:
            print(f"Error reading stream: {e}")
            time.sleep(1)

if __name__ == '__main__':
    print("Transcode Worker started, waiting for enhance events...")
    main()
