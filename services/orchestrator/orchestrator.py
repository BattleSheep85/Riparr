"""Orchestrator service.

Monitors health of pipeline containers, handles pause/resume/shutdown commands via Redis
streams, and publishes orchestrator events.
"""
import json
import os
import sys
import time

import yaml
import redis
import docker
from docker.errors import DockerException

# Load configuration
config_path = os.getenv('CONFIG_PATH', '/config/config.yaml')
try:
    with open(config_path, 'r', encoding='utf-8') as fp:
        config = yaml.safe_load(fp)
except FileNotFoundError:
    print(f"Config file not found at {config_path}, exiting.")
    sys.exit(1)
except yaml.YAMLError as e:
    print(f"Error parsing config: {e}, exiting.")
    sys.exit(1)

# Redis connection
redis_url = config.get('redis', {}).get('url', 'redis://redis:6379')
r = redis.from_url(redis_url, decode_responses=True)

# Docker client
try:
    client = docker.from_env()
except DockerException as e:
    print(f"Error connecting to Docker: {e}, exiting.")
    sys.exit(1)

# Service containers
pipeline_services = [
    'drive-watcher',
    'rip-worker',
    'enhance-worker',
    'transcode-worker',
    'metadata-worker',
    'blackhole'
]

def check_health():
    """Check health of all services."""
    health_status = {}
    for service in pipeline_services:
        try:
            container = client.containers.get(service)
            status = (
                container.attrs["State"]["Health"]["Status"]
                if "Health" in container.attrs["State"]
                else container.status
            )
            health_status[service] = status
        except docker.errors.NotFound:
            health_status[service] = 'not_found'
        except docker.errors.APIError as err:
            health_status[service] = f"error: {err}"
    return health_status

def pause_pipeline():
    """Pause all pipeline services."""
    for service in pipeline_services:
        try:
            container = client.containers.get(service)
            container.pause()
            print(f"Paused {service}")
        except docker.errors.APIError as err:
            print(f"Error pausing {service}: {err}")

def resume_pipeline():
    """Resume all pipeline services."""
    for service in pipeline_services:
        try:
            container = client.containers.get(service)
            container.unpause()
            print(f"Resumed {service}")
        except docker.errors.APIError as err:
            print(f"Error resuming {service}: {err}")

def graceful_shutdown():
    """Gracefully shutdown all services."""
    for service in pipeline_services:
        try:
            container = client.containers.get(service)
            container.stop()
            print(f"Stopped {service}")
        except docker.errors.APIError as err:
            print(f"Error stopping {service}: {err}")

def process_command(data):
    """Handle a command received on ``orchestrator_commands`` stream."""
    action = data.get('action')
    timestamp = json.dumps({"timestamp": time.time()})
    if action == "pause_pipeline":
        pause_pipeline()
        r.xadd("orchestrator_events", {"event": "pipeline_paused", "data": timestamp})
    elif action == "resume_pipeline":
        resume_pipeline()
        r.xadd("orchestrator_events", {"event": "pipeline_resumed", "data": timestamp})
    elif action == "shutdown":
        graceful_shutdown()
        r.xadd("orchestrator_events", {"event": "shutdown_initiated", "data": timestamp})
        sys.exit(0)

def main() -> None:
    """Main event loop: health checks and command processing."""
    print("Orchestrator started.")
    last_id = '0'
    while True:
        try:
            # Check health every 30 seconds
            health = check_health()
            r.xadd(
                "orchestrator_events",
                {"event": "health_check", "data": json.dumps(health)},
            )

            # Listen for commands
            messages = r.xread({"orchestrator_commands": last_id}, block=30_000)  # 30 seconds
            for _stream, msgs in messages:
                for msg_id, msg in msgs:
                    last_id = msg_id
                    data = json.loads(msg['data'])
                    process_command(data)
        except (redis.RedisError, json.JSONDecodeError, docker.errors.APIError) as err:
            print(f"Error in main loop: {err}")
            time.sleep(5)

if __name__ == "__main__":
    main()
