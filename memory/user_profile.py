"""User profile management for personalization."""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
import redis
import weave


@dataclass
class UserProfile:
    """User profile with diagnosis and preferences."""
    
    user_id: str
    diagnosis: str = "NONE"  # NONE, ADHD, AUTISM, BOTH
    diagnosis_source: str = "UNSPECIFIED"  # OFFICIAL, SELF, UNSPECIFIED
    onboarding_complete: bool = False
    preferred_checkin_interval: float = 3.0  # minutes
    sensory_sensitivities: list[str] = field(default_factory=list)
    
    def get_adaptation_intensity(self) -> float:
        """Get adaptation intensity based on diagnosis source.
        
        Returns:
            Intensity value (0.0 to 1.0)
        """
        if self.diagnosis == "NONE":
            return 0.0
        
        if self.diagnosis_source == "OFFICIAL":
            return 1.0
        elif self.diagnosis_source == "SELF":
            return 0.8
        else:  # UNSPECIFIED
            return 0.9
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Create from dictionary."""
        return cls(**data)


class UserProfileManager:
    """Manages user profiles in Redis."""
    
    def __init__(self, redis_url: str):
        """Initialize profile manager.
        
        Args:
            redis_url: Redis connection URL
        """
        self.client = redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = "sam2voice:profile:"
    
    def _get_key(self, user_id: str) -> str:
        """Get Redis key for user profile."""
        return f"{self._key_prefix}{user_id}"
    
    @weave.op()
    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from Redis.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserProfile if found, None otherwise
        """
        key = self._get_key(user_id)
        data = self.client.get(key)
        
        if not data:
            return None
        
        try:
            profile_dict = json.loads(data)
            return UserProfile.from_dict(profile_dict)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing profile for {user_id}: {e}")
            return None
    
    @weave.op()
    async def save_profile(self, profile: UserProfile):
        """Save user profile to Redis.
        
        Args:
            profile: UserProfile to save
        """
        key = self._get_key(profile.user_id)
        data = json.dumps(profile.to_dict())
        self.client.set(key, data)
        # Profiles don't expire - they're permanent
    
    @weave.op()
    async def update_diagnosis(
        self,
        user_id: str,
        diagnosis: str,
        source: str
    ):
        """Update user diagnosis and mark onboarding complete.
        
        Args:
            user_id: User identifier
            diagnosis: Diagnosis (NONE, ADHD, AUTISM, BOTH)
            source: Source (OFFICIAL, SELF, UNSPECIFIED)
        """
        profile = await self.get_or_create(user_id)
        profile.diagnosis = diagnosis.upper()
        profile.diagnosis_source = source.upper()
        profile.onboarding_complete = True
        await self.save_profile(profile)
    
    @weave.op()
    async def get_or_create(self, user_id: str) -> UserProfile:
        """Get existing profile or create new default one.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserProfile (existing or new)
        """
        profile = await self.get_profile(user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
            await self.save_profile(profile)
        return profile
