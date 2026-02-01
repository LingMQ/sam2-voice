"""Memory system for self-improving voice agent.

This module provides:
- Redis-backed memory with vector search
- User profile management
- Embedding generation
- Session reflection
"""

from memory.embeddings import get_embedding
from memory.redis_memory import RedisUserMemory
from memory.reflection import generate_reflection
from memory.user_profile import UserProfile, UserProfileManager

__all__ = [
    "get_embedding",
    "RedisUserMemory",
    "generate_reflection",
    "UserProfile",
    "UserProfileManager",
]
