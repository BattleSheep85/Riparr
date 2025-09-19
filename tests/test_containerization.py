import pytest
import subprocess
import os
import time
import docker
from docker.errors import DockerException

def test_rip_worker_container_access():
    """
    Test that the Rip Worker can access an optical drive inside a container.
    Validates containerization by mounting /dev/sr0 and attempting to run MakeMKV.
    """
    client = docker.from_env()

    # Test container configuration
    container_config = {
        'image': 'riparr/rip-worker:latest',  # Assuming built image
        'environment': {
            'REDIS_URL': 'redis://redis:6379',
            'ENABLE_RIP': 'true',
            'MKV_OUTPUT_DIR': '/data/rips',
            'TITLE_SELECTION': 'all'
        },
        'volumes': {
            '/data': {'bind': '/data', 'mode': 'rw'}
        },
        'devices': ['/dev/sr0:/dev/sr0:rwm'],  # Mount optical drive
        'detach': True,
        'auto_remove': True
    }

    # Start container
    try:
        container = client.containers.run(**container_config)
        time.sleep(5)  # Allow startup

        # Check if container is running
        container.reload()
        assert container.status == 'running', f"Container failed to start: {container.status}"

        # Simulate drive insert event (would normally come from drive-watcher)
        # For testing, we can check if makemkvcon is available in container
        exec_result = container.exec_run('which makemkvcon')
        assert exec_result.exit_code == 0, "MakeMKV not found in container"

        # Check device access
        exec_result = container.exec_run('ls -la /dev/sr0')
        assert exec_result.exit_code == 0, "Cannot access optical drive device"

        print("Containerization test passed: Rip Worker container can access optical drive")

    except DockerException as e:
        pytest.fail(f"Docker error: {e}")
    finally:
        if 'container' in locals():
            container.stop()

def test_mkv_output_validation():
    """
    Test MKV file generation and validation.
    Note: Requires actual test disc inserted.
    """
    # This would require a physical disc
    # For CI/testing without hardware, this is a placeholder
    pytest.skip("Requires physical optical disc for full validation")

    # Placeholder assertions
    # - Check file size in expected range
    # - Verify tracks present
    # - Check rip.complete event emitted