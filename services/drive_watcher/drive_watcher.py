import pyudev
import redis
import json
import uuid
import os
import sys
import logging
from typing import Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if service is enabled
enable = os.getenv('ENABLE_DRIVE_WATCHER', 'false').lower() == 'true'
if not enable:
    logger.info("Drive Watcher disabled, exiting.")
    sys.exit(0)

# Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
r = redis.from_url(redis_url, decode_responses=True)

# Dictionary to store drive IDs
drive_ids: Dict[str, str] = {}

def device_event(device) -> None:
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
        logger.info(f"Published insert for {dev_path}")

    elif action == 'remove':
        if dev_path in drive_ids:
            msg = {
                "drive_id": drive_ids[dev_path],
                "device": dev_path,
                "event": "eject"
            }
            r.xadd('drive_events', {'data': json.dumps(msg)})
            del drive_ids[dev_path]
            logger.info(f"Published eject for {dev_path}")

# Set up udev monitor
context = pyudev.Context()
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by('block')

observer = pyudev.MonitorObserver(monitor, device_event)
observer.start()

logger.info("Drive Watcher started, monitoring optical drives...")

# Keep the script running
try:
    observer.join()
except KeyboardInterrupt:
    observer.stop()
    logger.info("Drive Watcher stopped.")
except Exception as e:
    logger.error(f"Unexpected error in drive watcher: {e}")
    observer.stop()