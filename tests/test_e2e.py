import pytest
import redis
import json
import time
import requests
import subprocess
import os
from docker.errors import DockerException

def wait_for_service(url, timeout=30):
    """
    Wait for a service to become available.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False

def simulate_disc_insert(redis_client, drive_id="test_drive", device="/dev/sr0"):
    """
    Simulate inserting a physical disc.
    """
    event_data = {
        'event': 'insert',
        'drive_id': drive_id,
        'device': device
    }
    redis_client.xadd('drive_events', {'data': json.dumps(event_data)})

def monitor_pipeline_events(redis_client, timeout=300):
    """
    Monitor all pipeline events from start to finish.
    """
    streams = ['drive_events', 'rip_events', 'enhance_events', 'transcode_events', 'metadata_events', 'blackhole_events']
    events = {stream: [] for stream in streams}

    start_time = time.time()
    last_ids = {stream: '0' for stream in streams}

    while time.time() - start_time < timeout:
        try:
            # Read from all streams
            stream_dict = {stream: last_ids[stream] for stream in streams}
            messages = redis_client.xread(stream_dict, block=1000)

            if messages:
                for stream_name, msg_list in messages:
                    for msg_id, msg in msg_list:
                        event_data = json.loads(msg['data'])
                        events[stream_name].append(event_data)
                        last_ids[stream_name] = msg_id

                        # Check for completion
                        if event_data.get('event') == 'complete' and stream_name == 'blackhole_events':
                            return events  # Pipeline complete

        except Exception as e:
            print(f"Error monitoring events: {e}")
            break

    return events

def test_full_pipeline():
    """
    Execute the full pipeline from ingestion to UI display.
    """
    r = redis.from_url('redis://localhost:6379', decode_responses=True)

    # Clear all streams
    streams = ['drive_events', 'rip_events', 'enhance_events', 'transcode_events', 'metadata_events', 'blackhole_events', 'logs']
    for stream in streams:
        r.delete(stream)

    # Start services (assuming docker-compose is running)
    # In a real test, this would start the services

    # Wait for UI gateway
    ui_available = wait_for_service('http://localhost:8080')
    assert ui_available, "UI Gateway not available"

    # Simulate disc insert
    simulate_disc_insert(r)

    # Monitor pipeline
    events = monitor_pipeline_events(r, timeout=600)  # 10 minutes timeout

    # Verify all stages emitted events
    required_events = {
        'rip_events': ['start', 'progress', 'complete'],
        'enhance_events': ['start', 'progress', 'complete'],
        'transcode_events': ['start', 'progress', 'complete'],
        'metadata_events': ['start', 'complete'],
        'blackhole_events': ['complete']
    }

    for stream, expected_events in required_events.items():
        stream_events = events.get(stream, [])
        event_types = [e.get('event') for e in stream_events]
        for expected in expected_events:
            assert expected in event_types, f"Missing {expected} event in {stream}"

    print("E2E test passed: All pipeline stages completed successfully")

def test_ui_status_display():
    """
    Verify UI shows live logs, job status, and final media.
    """
    # Check UI endpoints
    response = requests.get('http://localhost:8080/api/status')
    assert response.status_code == 200, "Status API failed"

    status_data = response.json()
    assert 'jobs' in status_data, "No jobs in status response"
    assert len(status_data['jobs']) > 0, "No active jobs found"

    # Check logs
    response = requests.get('http://localhost:8080/api/logs')
    assert response.status_code == 200, "Logs API failed"

    # Verify final file appears in target library
    # This would check the blackhole directory
    blackhole_path = "/media/plex"  # From config
    assert os.path.exists(blackhole_path), "Blackhole path does not exist"

    # Check for media files
    media_files = []
    for root, dirs, files in os.walk(blackhole_path):
        for file in files:
            if file.endswith(('.mkv', '.mp4', '.m4v')):
                media_files.append(os.path.join(root, file))

    assert len(media_files) > 0, "No media files found in blackhole"

    print("UI test passed: Status and logs displayed correctly")

def test_media_playability():
    """
    Verify final file is playable.
    """
    # Use ffprobe to check media integrity
    blackhole_path = "/media/plex"
    media_files = []
    for root, dirs, files in os.walk(blackhole_path):
        for file in files:
            if file.endswith(('.mkv', '.mp4', '.m4v')):
                media_files.append(os.path.join(root, file))

    assert len(media_files) > 0, "No media files to test"

    for media_file in media_files:
        # Check with ffprobe
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-show_format', '-show_streams', media_file
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Media file corrupted: {media_file}"
        assert 'duration' in result.stdout, f"No duration info for {media_file}"

    print("Media test passed: Files are playable")

def test_error_handling():
    """
    Test pipeline error handling and recovery.
    """
    # Test with invalid disc or corrupted input
    # This would simulate error conditions
    pytest.skip("Error handling tests require specific failure scenarios")

    # Assertions for error recovery
    # - Pipeline should not crash
    # - Errors should be logged
    # - UI should show error status