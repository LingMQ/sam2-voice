"""Structured logging for memory system."""

import logging
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime


class MemoryLogger:
    """Structured logger for memory operations."""
    
    _logger: Optional[logging.Logger] = None
    _initialized = False
    
    @classmethod
    def _initialize(cls):
        """Initialize logger if not already done."""
        if cls._initialized:
            return
        
        cls._logger = logging.getLogger("memory_system")
        cls._logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if cls._logger.handlers:
            return
        
        # Console handler with structured format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # File handler for detailed logs
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "memory_system.log",
            mode="a"
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Formatters
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        detailed_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d] %(funcName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(detailed_formatter)
        
        cls._logger.addHandler(console_handler)
        cls._logger.addHandler(file_handler)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Get the logger instance."""
        cls._initialize()
        return cls._logger
    
    @classmethod
    def log_operation(
        cls,
        operation: str,
        user_id: str,
        status: str,
        details: Optional[dict] = None,
        error: Optional[Exception] = None
    ):
        """Log a memory operation with structured data.
        
        Args:
            operation: Operation name (e.g., "record_intervention")
            user_id: User identifier
            status: Status (success, error, warning)
            details: Additional details dict
            error: Exception if any
        """
        logger = cls.get_logger()
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "user_id": user_id,
            "status": status,
        }
        
        if details:
            log_data.update(details)
        
        if error:
            log_data["error"] = {
                "type": type(error).__name__,
                "message": str(error),
            }
            logger.error(json.dumps(log_data))
        elif status == "warning":
            logger.warning(json.dumps(log_data))
        else:
            logger.info(json.dumps(log_data))
    
    @classmethod
    def log_performance(
        cls,
        operation: str,
        duration_ms: float,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        """Log performance metrics.
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            user_id: Optional user identifier
            metadata: Additional metadata
        """
        logger = cls.get_logger()
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "duration_ms": duration_ms,
            "type": "performance"
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if metadata:
            log_data.update(metadata)
        
        logger.debug(json.dumps(log_data))
        
        # Warn on slow operations
        if duration_ms > 1000:
            logger.warning(f"Slow operation: {operation} took {duration_ms:.0f}ms")


def get_logger() -> logging.Logger:
    """Get the memory system logger."""
    return MemoryLogger.get_logger()
