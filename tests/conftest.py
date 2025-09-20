"""Pytest configuration and fixtures for Riparr tests."""

import subprocess
import pytest
import redis
import docker


@pytest.fixture(scope="session")
def redis_client():
    """Redis client fixture for tests."""
    client = redis.from_url('redis://localhost:6379', decode_responses=True)
    # Clear test data
    client.flushdb()
    yield client
    client.flushdb()

@pytest.fixture(scope="session")
def docker_client():
    """Docker client fixture for tests."""
    client = docker.from_env()
    yield client

@pytest.fixture(scope="session")
def test_environment():
    """Ensure test environment is set up."""
    # Check if docker-compose is running
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, check=False)
        assert result.returncode == 0, "Docker not running"
    except FileNotFoundError:
        pytest.skip("Docker not available")

    # Check Redis
    try:
        r = redis.from_url('redis://localhost:6379', decode_responses=True)
        r.ping()
    except redis.ConnectionError:
        pytest.skip("Redis not available")

    yield

@pytest.fixture
def cleanup_streams():
    """Clean up Redis streams before and after tests."""
