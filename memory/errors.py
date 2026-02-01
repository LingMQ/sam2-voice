"""Custom exceptions for memory system."""

from typing import Optional


class MemoryError(Exception):
    """Base exception for memory system errors."""
    pass


class EmbeddingError(MemoryError):
    """Error generating embeddings."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class RedisConnectionError(MemoryError):
    """Error connecting to Redis."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class VectorSearchError(MemoryError):
    """Error performing vector search."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class IndexCreationError(MemoryError):
    """Error creating vector search index."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class ValidationError(MemoryError):
    """Data validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field
