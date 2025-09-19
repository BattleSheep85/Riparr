import pyudev
import redis
import json
import uuid
import os
import sys

# Check if service is enabled
enable = os.getenv('ENABLE_DRIVE_WATCHER', 'false').lower() == 'true'
if not enable:
    print("Drive Watcher disabled, exiting.")
    sys.exit(0)

# Redis connection
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_port = int(os.getenv('REDIS_PORT', 6379))
r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

# Dictionary to store drive IDs
drive_ids = {}

def device_event(device):
    action = device.action
    dev_path = device.device_node
    is_optical = device.get('ID_CDROM') == '1'

    if not is_optical:
        return

    if action == 'add':
        if dev_path not in drive_ids:
            drive_ids[dev_path] = str(uuid.uuid4())
        msg = {
            "drive_id": drive_ids[dev_path],
            "device": dev_path,
            "event": "insert"
        }
        r.xadd('drive_events', {'data': json.dumps(msg)})
        print(f"Published insert for {dev_path}")

    elif action == 'remove':
        if dev_path in drive_ids:
            msg = {
                "drive_id": drive_ids[dev_path],
                "device": dev_path,
                "event": "eject"
            }
            r.xadd('drive_events', {'data': json.dumps(msg)})
            del drive_ids[dev_path]
            print(f"Published eject for {dev_path}")

# Set up udev monitor
context = pyudev.Context()
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by('block')

observer = pyudev.MonitorObserver(monitor, device_event)
observer.start()

print("Drive Watcher started, monitoring optical drives...")

# Keep the script running
try:
    observer.join()
except KeyboardInterrupt:
    observer.stop()
    print("Drive Watcher stopped.")