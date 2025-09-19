import redis
import json
import os
import yaml
import time
import docker
from docker.errors import DockerException

# Load configuration
config_path = os.getenv('CONFIG_PATH', '/config/config.yaml')
try:
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    print(f"Config file not found at {config_path}, exiting.")
    exit(1)
except yaml.YAMLError as e:
    print(f"Error parsing config: {e}, exiting.")
    exit(1)

# Redis connection
redis_url = config.get('redis', {}).get('url', 'redis://redis:6379')
r = redis.from_url(redis_url, decode_responses=True)

# Docker client
docker_socket = config.get('docker', {}).get('socket', '/var/run/docker.sock')
try:
    client = docker.from_env()
except DockerException as e:
    print(f"Error connecting to Docker: {e}, exiting.")
    exit(1)

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
            status = container.attrs['State']['Health']['Status'] if 'Health' in container.attrs['State'] else container.status
            health_status[service] = status
        except docker.errors.NotFound:
            health_status[service] = 'not_found'
        except Exception as e:
            health_status[service] = f'error: {str(e)}'
    return health_status

def pause_pipeline():
    """Pause all pipeline services."""
    for service in pipeline_services:
        try:
            container = client.containers.get(service)
            container.pause()
            print(f"Paused {service}")
        except Exception as e:
            print(f"Error pausing {service}: {e}")

def resume_pipeline():
    """Resume all pipeline services."""
    for service in pipeline_services:
        try:
            container = client.containers.get(service)
            container.unpause()
            print(f"Resumed {service}")
        except Exception as e:
            print(f"Error resuming {service}: {e}")

def graceful_shutdown():
    """Gracefully shutdown all services."""
    for service in pipeline_services:
        try:
            container = client.containers.get(service)
            container.stop()
            print(f"Stopped {service}")
        except Exception as e:
            print(f"Error stopping {service}: {e}")

def process_command(data):
    action = data.get('action')
    if action == 'pause_pipeline':
        pause_pipeline()
        r.xadd('orchestrator_events', {'event': 'pipeline_paused', 'data': json.dumps({'timestamp': time.time()})})
    elif action == 'resume_pipeline':
        resume_pipeline()
        r.xadd('orchestrator_events', {'event': 'pipeline_resumed', 'data': json.dumps({'timestamp': time.time()})})
    elif action == 'shutdown':
        graceful_shutdown()
        r.xadd('orchestrator_events', {'event': 'shutdown_initiated', 'data': json.dumps({'timestamp': time.time()})})
        exit(0)

def main():
    print("Orchestrator started.")
    last_id = '0'
    while True:
        try:
            # Check health every 30 seconds
            health = check_health()
            r.xadd('orchestrator_events', {'event': 'health_check', 'data': json.dumps(health)})
            
            # Listen for commands
            messages = r.xread({'orchestrator_commands': last_id}, block=30000)  # 30 seconds
            for stream, msgs in messages:
                for msg_id, msg in msgs:
                    last_id = msg_id
                    data = json.loads(msg['data'])
                    process_command(data)
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()