"""Pytest configuration for memory tests."""

import pytest
import os
from dotenv import load_dotenv

load_dotenv()


def pytest_configure(config):
    """Configure pytest."""
    # Mark tests that require Redis
    config.addinivalue_line(
        "markers", "requires_redis: mark test as requiring Redis connection"
    )


@pytest.fixture(scope="session")
def redis_available():
    """Check if Redis is available for testing."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        pytest.skip("REDIS_URL not set - skipping Redis tests")
    return redis_url
