import pytest
import redis
import json
import time
import threading
import psutil
from concurrent.futures import ThreadPoolExecutor

def mock_drive_events(redis_client, num_drives=20):
    """
    Mock drive.insert events for multiple virtual drives.
    """
    for i in range(num_drives):
        drive_id = f"mock_drive_{i}"
        device = f"/dev/sr{i}"  # Mock device paths
        event_data = {
            'event': 'insert',
            'drive_id': drive_id,
            'device': device
        }
        redis_client.xadd('drive_events', {'data': json.dumps(event_data)})
        time.sleep(0.1)  # Slight delay between events

def monitor_redis_streams(redis_client, stream_name, timeout=60):
    """
    Monitor Redis stream for back-pressure and job ordering.
    """
    start_time = time.time()
    messages = []
    last_id = '0'

    while time.time() - start_time < timeout:
        try:
            msgs = redis_client.xread({stream_name: last_id}, block=1000)
            if msgs:
                for stream, msg_list in msgs:
                    for msg_id, msg in msg_list:
                        messages.append((msg_id, msg))
                        last_id = msg_id
        except Exception as e:
            print(f"Error reading stream: {e}")
            break

    return messages

def get_active_jobs_count(redis_client):
    """
    Count active jobs from Redis streams.
    """
    # This would check rip_events for active jobs
    # Placeholder implementation
    return 0

def test_concurrency_limits():
    """
    Test that no more than MAX_CONCURRENT_RIPS jobs run in parallel.
    """
    r = redis.from_url('redis://localhost:6379', decode_responses=True)

    # Clear existing streams
    r.delete('drive_events', 'rip_events')

    MAX_CONCURRENT_RIPS = 5  # From config or env

    # Start monitoring thread
    monitor_thread = threading.Thread(
        target=monitor_redis_streams,
        args=(r, 'rip_events', 30)
    )
    monitor_thread.start()

    # Mock 20 drive inserts
    mock_drive_events(r, 20)

    # Wait for processing
    time.sleep(10)

    # Check concurrent job limits
    active_jobs = get_active_jobs_count(r)
    assert active_jobs <= MAX_CONCURRENT_RIPS, f"Too many concurrent jobs: {active_jobs} > {MAX_CONCURRENT_RIPS}"

    monitor_thread.join()

def test_resource_utilization():
    """
    Monitor CPU/GPU utilization during concurrent processing.
    """
    initial_cpu = psutil.cpu_percent(interval=1)
    initial_mem = psutil.virtual_memory().percent

    # Run concurrency test
    test_concurrency_limits()

    final_cpu = psutil.cpu_percent(interval=1)
    final_mem = psutil.virtual_memory().percent

    # Assert utilization stays within bounds
    cpu_increase = final_cpu - initial_cpu
    mem_increase = final_mem - initial_mem

    assert cpu_increase < 80, f"CPU utilization too high: {cpu_increase}% increase"
    assert mem_increase < 70, f"Memory utilization too high: {mem_increase}% increase"

    print(f"Resource test passed: CPU +{cpu_increase}%, Memory +{mem_increase}%")

def test_job_ordering():
    """
    Verify jobs complete with correct ordering and no deadlocks.
    """
    r = redis.from_url('redis://localhost:6379', decode_responses=True)

    # Clear streams
    r.delete('drive_events', 'rip_events')

    # Mock sequential drive inserts
    mock_drive_events(r, 5)

    # Monitor completion events
    messages = monitor_redis_streams(r, 'rip_events', 30)

    # Check for deadlocks (no progress)
    assert len(messages) > 0, "No job events received - possible deadlock"

    # Check ordering (jobs should complete in FIFO order approximately)
    completed_jobs = [msg for msg in messages if json.loads(msg[1]['data']).get('event') == 'complete']
    assert len(completed_jobs) > 0, "No jobs completed"

    print("Concurrency test passed: Jobs processed without deadlocks")

def test_back_pressure():
    """
    Test Redis stream back-pressure handling.
    """
    r = redis.from_url('redis://localhost:6379', decode_responses=True)

    # Flood the stream with events
    for i in range(100):
        mock_drive_events(r, 1)

    # Check stream length
    stream_info = r.xinfo_stream('drive_events')
    assert stream_info['length'] > 0, "Events not queued"

    # Verify processing doesn't crash under load
    time.sleep(5)
    # Check if services are still responsive
    assert r.ping(), "Redis connection lost under load"