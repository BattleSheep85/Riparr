"""Blackhole Integration Service.

Moves final media files into the configured *blackhole* directory,
writes optional `.nfo` side-car metadata, and emits
`blackhole.start` / `blackhole.complete` events on the
`blackhole_events` Redis stream.
"""

import json
import logging
import os
import shutil
import sys
import time
from typing import Any, Dict, List

import redis

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

# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #


def create_sidecar_nfo(metadata: Dict[str, Any], target_dir: str) -> str:
    """Write an `.nfo` side-car containing minimal metadata.

    Args:
        metadata: Dict with keys ``normalized_title``, ``original_file``, ``job_id``.
        target_dir: Destination directory where the `.nfo` file will be written.

    Returns:
        Absolute path to the created `.nfo` file.
    """
    nfo_path = os.path.join(target_dir, f"{metadata['normalized_title']}.nfo")
    with open(nfo_path, 'w', encoding="utf-8") as f:
        f.write(f"Title: {metadata['normalized_title']}\n")
        f.write(f"Original File: {metadata['original_file']}\n")
        f.write(f"Job ID: {metadata['job_id']}\n")
    return nfo_path


def process_metadata_complete(job_id: str, metadata_list: List[Dict[str, Any]]) -> None:
    """Move files and publish a `blackhole.complete` event.

    Args:
        job_id: ID of the job being processed.
        metadata_list: A list of per-file metadata dictionaries.
    """
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
    logger.info("Published blackhole.complete for job %s", job_id)


def process_metadata_event(data: Dict[str, Any]) -> None:
    """Handle a single message from ``metadata_events`` stream."""
    if data.get('event') == 'complete':
        job_id = data['job_id']
        metadata_list = data['metadata']

        # Publish start
        start_msg = {
            "job_id": job_id,
            "metadata": metadata_list
        }
        r.xadd('blackhole_events', {'event': 'start', 'data': json.dumps(start_msg)})
        logger.info("Published blackhole.start for job %s", job_id)

        # Process
        process_metadata_complete(job_id, metadata_list)


def main() -> None:
    """Event loop – blocks on Redis ``metadata_events`` stream and processes messages."""
    last_id = '0'
    while True:
        try:
            messages = r.xread({'metadata_events': last_id}, block=1000)
            for _stream, msgs in messages:  # underscore to mark unused variable
                for msg_id, msg in msgs:
                    last_id = msg_id
                    data = json.loads(msg['data'])
                    process_metadata_event(data)
        except (redis.ConnectionError, redis.TimeoutError) as err:
            logger.error("Redis connection error: %s", err)
            time.sleep(1)
        except json.JSONDecodeError as err:
            logger.error("JSON decode error: %s", err)
            time.sleep(1)
        except Exception as err:  # pylint: disable=broad-except
            logger.error("Unexpected error in main loop: %s", err)
            time.sleep(1)

if __name__ == '__main__':
    logger.info("Blackhole Integration started, waiting for metadata events...")
    main()
