"""User profile management for personalization."""

import os
import json
import hashlib
import secrets
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
import redis
import weave


@dataclass
class UserAccount:
    """User account with authentication credentials."""

    user_id: str
    name: str
    email: Optional[str] = None
    password_hash: str = ""
    salt: str = ""
    created_at: str = ""
    last_login: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "UserAccount":
        """Create from dictionary."""
        return cls(**data)


class UserAuthManager:
    """Manages user authentication in Redis."""

    def __init__(self, redis_url: str):
        """Initialize auth manager.

        Args:
            redis_url: Redis connection URL
        """
        self.client = redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = "sam2voice:auth:"
        self._email_index_prefix = "sam2voice:email_index:"

    def _get_key(self, user_id: str) -> str:
        """Get Redis key for user account."""
        return f"{self._key_prefix}{user_id}"

    def _get_email_key(self, email: str) -> str:
        """Get Redis key for email index."""
        return f"{self._email_index_prefix}{email.lower()}"

    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using SHA-256."""
        return hashlib.sha256((password + salt).encode()).hexdigest()

    def _generate_salt(self) -> str:
        """Generate a random salt."""
        return secrets.token_hex(16)

    def _generate_user_id(self, name: str, email: Optional[str]) -> str:
        """Generate a unique user ID."""
        base = email.lower() if email else name.lower().replace(" ", "_")
        # Clean the base string
        clean_base = "".join(c for c in base if c.isalnum() or c in "_@.-")
        return f"user_{clean_base[:50]}"

    async def register(
        self,
        name: str,
        password: str,
        email: Optional[str] = None
    ) -> tuple[bool, str, Optional[UserAccount]]:
        """Register a new user.

        Args:
            name: User's display name
            password: User's password
            email: Optional email address

        Returns:
            Tuple of (success, message, account)
        """
        # Check if email already exists
        if email:
            email_key = self._get_email_key(email)
            existing_id = self.client.get(email_key)
            if existing_id:
                return False, "Email already registered", None

        # Generate user ID
        user_id = self._generate_user_id(name, email)

        # Check if user ID already exists
        key = self._get_key(user_id)
        if self.client.exists(key):
            # Add random suffix if ID exists
            user_id = f"{user_id}_{secrets.token_hex(4)}"
            key = self._get_key(user_id)

        # Create account
        salt = self._generate_salt()
        password_hash = self._hash_password(password, salt)
        now = datetime.utcnow().isoformat()

        account = UserAccount(
            user_id=user_id,
            name=name,
            email=email,
            password_hash=password_hash,
            salt=salt,
            created_at=now,
            last_login=now
        )

        # Save to Redis
        self.client.set(key, json.dumps(account.to_dict()))

        # Create email index if email provided
        if email:
            self.client.set(self._get_email_key(email), user_id)

        return True, "Registration successful", account

    async def login(
        self,
        identifier: str,
        password: str
    ) -> tuple[bool, str, Optional[UserAccount]]:
        """Login a user.

        Args:
            identifier: Email or user_id
            password: User's password

        Returns:
            Tuple of (success, message, account)
        """
        # Try to find user by email first
        user_id = identifier
        if "@" in identifier:
            email_key = self._get_email_key(identifier)
            stored_id = self.client.get(email_key)
            if stored_id:
                user_id = stored_id
            else:
                return False, "Email not found", None

        # Get account
        key = self._get_key(user_id)
        data = self.client.get(key)

        if not data:
            return False, "User not found", None

        try:
            account = UserAccount.from_dict(json.loads(data))
        except (json.JSONDecodeError, TypeError):
            return False, "Invalid account data", None

        # Verify password
        password_hash = self._hash_password(password, account.salt)
        if password_hash != account.password_hash:
            return False, "Invalid password", None

        # Update last login
        account.last_login = datetime.utcnow().isoformat()
        self.client.set(key, json.dumps(account.to_dict()))

        return True, "Login successful", account

    async def get_account(self, user_id: str) -> Optional[UserAccount]:
        """Get user account by ID.

        Args:
            user_id: User identifier

        Returns:
            UserAccount if found, None otherwise
        """
        key = self._get_key(user_id)
        data = self.client.get(key)

        if not data:
            return None

        try:
            return UserAccount.from_dict(json.loads(data))
        except (json.JSONDecodeError, TypeError):
            return None

    async def user_exists(self, identifier: str) -> bool:
        """Check if user exists by email or user_id.

        Args:
            identifier: Email or user_id

        Returns:
            True if user exists
        """
        if "@" in identifier:
            return self.client.exists(self._get_email_key(identifier))
        return self.client.exists(self._get_key(identifier))


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
