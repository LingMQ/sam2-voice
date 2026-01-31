"""Configuration utilities for sam2-voice."""

import os
from typing import Optional
from dotenv import load_dotenv


def load_config() -> None:
    """Load environment variables from .env file."""
    load_dotenv()


def get_env(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get environment variable with optional default and required validation.

    Args:
        key: Environment variable name
        default: Default value if not found
        required: If True, raises ValueError when not found

    Returns:
        The environment variable value or default

    Raises:
        ValueError: If required=True and variable is not set
    """
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


def validate_config() -> dict:
    """Validate all required configuration is present.

    Returns:
        Dict with all validated config values

    Raises:
        ValueError: If any required config is missing
    """
    config = {
        "daily_api_key": get_env("DAILY_API_KEY", required=True),
        "deepgram_api_key": get_env("DEEPGRAM_API_KEY", required=True),
        "google_api_key": get_env("GOOGLE_API_KEY", required=True),
        "daily_room_url": get_env("DAILY_ROOM_URL"),  # Optional
    }
    return config
