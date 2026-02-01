"""Input validation for memory system."""

from typing import List, Optional
from memory.errors import ValidationError
from memory.logger import get_logger

logger = get_logger()


def validate_embedding(embedding: List[float], expected_dim: int = 768) -> None:
    """Validate embedding vector.
    
    Args:
        embedding: Embedding vector
        expected_dim: Expected dimension
        
    Raises:
        ValidationError: If embedding is invalid
    """
    if not embedding:
        raise ValidationError("Embedding cannot be empty")
    
    if not isinstance(embedding, list):
        raise ValidationError(f"Embedding must be a list, got {type(embedding)}")
    
    if len(embedding) != expected_dim:
        raise ValidationError(
            f"Embedding dimension mismatch: expected {expected_dim}, got {len(embedding)}",
            field="embedding"
        )
    
    # Check for NaN or Inf values
    import math
    for i, val in enumerate(embedding):
        if not isinstance(val, (int, float)):
            raise ValidationError(
                f"Embedding value at index {i} is not a number: {type(val)}",
                field="embedding"
            )
        if math.isnan(val) or math.isinf(val):
            raise ValidationError(
                f"Embedding value at index {i} is NaN or Inf",
                field="embedding"
            )


def validate_intervention_data(
    intervention_text: str,
    context: str,
    task: str,
    outcome: str,
    embedding: Optional[List[float]] = None
) -> None:
    """Validate intervention data before storage.
    
    Args:
        intervention_text: Intervention text
        context: Context string
        task: Task name
        outcome: Outcome string
        embedding: Optional embedding to validate
        
    Raises:
        ValidationError: If data is invalid
    """
    if not intervention_text or not intervention_text.strip():
        raise ValidationError("intervention_text cannot be empty", field="intervention_text")
    
    if len(intervention_text) > 1000:
        raise ValidationError(
            f"intervention_text too long: {len(intervention_text)} chars (max 1000)",
            field="intervention_text"
        )
    
    if not context or not context.strip():
        raise ValidationError("context cannot be empty", field="context")
    
    if len(context) > 2000:
        raise ValidationError(
            f"context too long: {len(context)} chars (max 2000)",
            field="context"
        )
    
    if not task or not task.strip():
        raise ValidationError("task cannot be empty", field="task")
    
    valid_outcomes = {
        "task_completed", "re_engaged", "task_progress",
        "task_started", "distracted", "abandoned", "intervention_applied"
    }
    if outcome not in valid_outcomes:
        logger.warning(f"Unknown outcome: {outcome} (expected one of {valid_outcomes})")
    
    if embedding is not None:
        validate_embedding(embedding)


def validate_user_id(user_id: str) -> None:
    """Validate user ID format.
    
    Args:
        user_id: User identifier
        
    Raises:
        ValidationError: If user_id is invalid
    """
    if not user_id or not user_id.strip():
        raise ValidationError("user_id cannot be empty", field="user_id")
    
    if len(user_id) > 100:
        raise ValidationError(
            f"user_id too long: {len(user_id)} chars (max 100)",
            field="user_id"
        )
    
    # Check for invalid characters that might break Redis keys
    invalid_chars = ['*', '?', '[', ']', ':', ' ', '\n', '\r', '\t']
    for char in invalid_chars:
        if char in user_id:
            raise ValidationError(
                f"user_id contains invalid character: {repr(char)}",
                field="user_id"
            )
