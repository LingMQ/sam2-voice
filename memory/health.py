"""Health checks and diagnostics for memory system."""

import time
from typing import Dict, Optional
import redis
from memory.logger import get_logger

logger = get_logger()


class MemoryHealthCheck:
    """Health check utilities for memory system."""
    
    def __init__(self, redis_url: str):
        """Initialize health checker.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None
    
    def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=False)
        return self._client
    
    def check_redis_connection(self) -> Dict[str, any]:
        """Check Redis connection health.
        
        Returns:
            Health status dict
        """
        start_time = time.time()
        try:
            client = self._get_client()
            result = client.ping()
            duration_ms = (time.time() - start_time) * 1000
            
            if result:
                return {
                    "status": "healthy",
                    "latency_ms": round(duration_ms, 2),
                    "error": None
                }
            else:
                return {
                    "status": "unhealthy",
                    "latency_ms": round(duration_ms, 2),
                    "error": "Ping returned False"
                }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Redis connection check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": round(duration_ms, 2),
                "error": str(e)
            }
    
    def check_vector_search(self, user_id: str) -> Dict[str, any]:
        """Check if vector search index exists and is accessible.
        
        Args:
            user_id: User identifier
            
        Returns:
            Health status dict
        """
        start_time = time.time()
        try:
            client = self._get_client()
            index_name = f"idx:user:{user_id}"
            
            try:
                info = client.ft(index_name).info()
                duration_ms = (time.time() - start_time) * 1000
                
                return {
                    "status": "healthy",
                    "index_name": index_name,
                    "latency_ms": round(duration_ms, 2),
                    "index_info": {
                        "num_docs": info.get("num_docs", 0),
                        "index_definition": info.get("index_definition", {})
                    },
                    "error": None
                }
            except redis.ResponseError as e:
                if "no such index" in str(e).lower():
                    return {
                        "status": "warning",
                        "index_name": index_name,
                        "latency_ms": round((time.time() - start_time) * 1000, 2),
                        "error": "Index does not exist (will be created on first use)",
                        "index_info": None
                    }
                raise
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Vector search check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": round(duration_ms, 2),
                "error": str(e)
            }
    
    def check_json_support(self) -> Dict[str, any]:
        """Check if Redis JSON module is available.
        
        Returns:
            Health status dict
        """
        start_time = time.time()
        try:
            client = self._get_client()
            
            # Test JSON operations
            test_key = "health:check:json"
            test_data = {"test": True, "timestamp": time.time()}
            
            client.json().set(test_key, "$", test_data)
            retrieved = client.json().get(test_key)
            client.delete(test_key)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if retrieved and retrieved.get("test") is True:
                return {
                    "status": "healthy",
                    "latency_ms": round(duration_ms, 2),
                    "error": None
                }
            else:
                return {
                    "status": "unhealthy",
                    "latency_ms": round(duration_ms, 2),
                    "error": "JSON operations returned unexpected result"
                }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"JSON support check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": round(duration_ms, 2),
                "error": str(e)
            }
    
    def get_comprehensive_health(self, user_id: str) -> Dict[str, any]:
        """Get comprehensive health status.
        
        Args:
            user_id: User identifier
            
        Returns:
            Complete health status dict
        """
        health = {
            "timestamp": time.time(),
            "checks": {}
        }
        
        # Redis connection
        health["checks"]["redis_connection"] = self.check_redis_connection()
        
        # JSON support
        health["checks"]["json_support"] = self.check_json_support()
        
        # Vector search
        health["checks"]["vector_search"] = self.check_vector_search(user_id)
        
        # Overall status
        all_statuses = [check["status"] for check in health["checks"].values()]
        if "unhealthy" in all_statuses:
            health["overall_status"] = "unhealthy"
        elif "warning" in all_statuses:
            health["overall_status"] = "degraded"
        else:
            health["overall_status"] = "healthy"
        
        return health
