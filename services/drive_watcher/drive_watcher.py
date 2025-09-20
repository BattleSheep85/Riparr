"""Drive Watcher Service.

Monitors optical drive insertion and ejection events using udev,
publishes 'insert' and 'eject' events to the 'drive_events' Redis stream.
"""

import json
import logging
import os
import sys
import uuid
from typing import Dict

import redis

try:
    import pyudev
except ImportError:
    pyudev = None
    print("pyudev not available, drive watcher disabled")
    sys.exit(1)

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
    """Handle udev device events for optical drives."""
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
        logger.info("Published insert for %s", dev_path)

    elif action == 'remove':
        if dev_path in drive_ids:
            msg = {
                "drive_id": drive_ids[dev_path],
                "device": dev_path,
                "event": "eject"
            }
            r.xadd('drive_events', {'data': json.dumps(msg)})
            del drive_ids[dev_path]
            logger.info("Published eject for %s", dev_path)

def main() -> None:
    """Main function to set up udev monitor and start observing."""
    if pyudev is None:
        logger.error("pyudev not available")
        return

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
    except (OSError, RuntimeError) as e:
        logger.error("Unexpected error in drive watcher: %s", e)
        observer.stop()

if __name__ == '__main__':
    main()

    # Add final newline
