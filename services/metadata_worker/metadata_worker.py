"""Metadata Worker Service.

Listens for transcode completion events, normalizes movie titles via Ollama,
writes metadata side-car JSON files, and publishes metadata.start / metadata.complete
events through Redis streams.
"""

import json
import os
import sys
import time
from typing import Any, Dict, List

# Third-party
try:  # Ollama is optional in some environments
    import ollama  # type: ignore
except ImportError:  # pragma: no cover
    ollama = None  # type: ignore

import redis

# Service toggle
ENABLE = os.getenv("ENABLE_METADATA", "false").lower() == "true"
if not ENABLE:
    print("Metadata Worker disabled, exiting.")
    sys.exit(0)

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
r = redis.from_url(REDIS_URL, decode_responses=True)

# Config
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
METADATA_DIR = os.getenv("METADATA_DIR", "/data/metadata")
os.makedirs(METADATA_DIR, exist_ok=True)


def normalize_title(filename: str) -> Dict[str, str]:
    """Return normalized title metadata for *filename* using Ollama (with graceful fallback)."""
    title = os.path.splitext(filename)[0]

    if ollama is None:
        return {
            "normalized_title": title,
            "directory": "/Movies/",
            "file_pattern": f"{title}.mkv",
        }

    prompt = (
        f"Normalize this movie title: '{title}'. "
        "Provide a clean title, year if available, directory structure like "
        "/Movies/Title (Year)/, and file pattern like Title (Year).mkv. "
        "Respond in JSON format with keys: normalized_title, directory, file_pattern."
    )

    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
        return json.loads(response["message"]["content"])
    except (json.JSONDecodeError, KeyError, TypeError) as err:
        print(f"Ollama error: {err}")
        return {
            "normalized_title": title,
            "directory": "/Movies/",
            "file_pattern": f"{title}.mkv",
        }


def process_transcode_complete(job_id: str, transcoded_files: List[str]) -> None:
    """Generate metadata for *transcoded_files* and publish completion event."""
    metadata_list: List[Dict[str, Any]] = []

    for file_path in transcoded_files:
        filename = os.path.basename(file_path)
        metadata = normalize_title(filename)
        metadata.update({"original_file": file_path, "job_id": job_id})
        metadata_list.append(metadata)

        json_path = os.path.join(METADATA_DIR, f"{job_id}_{filename}.json")
        with open(json_path, "w", encoding="utf-8") as fp:
            json.dump(metadata, fp, indent=2)

    complete_msg = {"job_id": job_id, "metadata": metadata_list}
    r.xadd("metadata_events", {"event": "complete", "data": json.dumps(complete_msg)})
    print(f"Published metadata.complete for job {job_id}")


def process_transcode_event(data: Dict[str, Any]) -> None:
    """Handle a single transcode event record."""
    if data.get("event") != "complete":
        return

    job_id = data["job_id"]
    transcoded_files = data["transcoded_files"]

    start_msg = {"job_id": job_id, "input_files": transcoded_files}
    r.xadd("metadata_events", {"event": "start", "data": json.dumps(start_msg)})
    print(f"Published metadata.start for job {job_id}")

    process_transcode_complete(job_id, transcoded_files)


def main() -> None:
    """Event-loop: consume transcode_events Redis stream indefinitely."""
    last_id = "0"
    while True:
        try:
            messages = r.xread({"transcode_events": last_id}, block=1000)
            for _stream, msgs in messages:
                for msg_id, msg in msgs:
                    last_id = msg_id
                    data = json.loads(msg["data"])
                    process_transcode_event(data)
        except (redis.ConnectionError, json.JSONDecodeError) as err:
            print(f"Stream read error: {err}")
            time.sleep(1)


if __name__ == "__main__":
    print("Metadata Worker started, waiting for transcode events...")
    main()
