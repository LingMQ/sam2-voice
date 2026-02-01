"""Production-grade tests for memory system."""

import pytest
import asyncio
import os
import time
from unittest.mock import Mock, patch, AsyncMock
from dotenv import load_dotenv

from memory.redis_memory import RedisUserMemory
from memory.embeddings import get_embedding
from memory.errors import (
    EmbeddingError,
    RedisConnectionError,
    VectorSearchError,
    ValidationError
)
from memory.validators import (
    validate_embedding,
    validate_intervention_data,
    validate_user_id
)
from memory.health import MemoryHealthCheck
from memory.logger import get_logger

load_dotenv()


@pytest.fixture
def redis_url():
    """Get Redis URL from environment."""
    url = os.getenv("REDIS_URL")
    if not url:
        pytest.skip("REDIS_URL not set")
    return url


@pytest.fixture
def test_user_id():
    """Generate test user ID."""
    return f"test_user_{int(time.time())}"


@pytest.fixture
async def memory(redis_url, test_user_id):
    """Create memory instance for testing."""
    memory = RedisUserMemory(user_id=test_user_id, redis_url=redis_url)
    yield memory
    # Cleanup: delete test data
    try:
        # Delete test interventions
        pattern = f"user:{test_user_id}:intervention:*"
        keys = list(memory.client.scan_iter(pattern, count=1000))
        if keys:
            memory.client.delete(*keys)
        
        # Delete test reflections
        pattern = f"user:{test_user_id}:reflection:*"
        keys = list(memory.client.scan_iter(pattern, count=1000))
        if keys:
            memory.client.delete(*keys)
    except Exception:
        pass


class TestValidation:
    """Test input validation."""
    
    def test_validate_embedding_valid(self):
        """Test valid embedding."""
        embedding = [0.1] * 768
        validate_embedding(embedding, expected_dim=768)
    
    def test_validate_embedding_wrong_dimension(self):
        """Test embedding with wrong dimension."""
        embedding = [0.1] * 512
        with pytest.raises(ValidationError) as exc_info:
            validate_embedding(embedding, expected_dim=768)
        assert "dimension mismatch" in str(exc_info.value)
    
    def test_validate_embedding_empty(self):
        """Test empty embedding."""
        with pytest.raises(ValidationError):
            validate_embedding([])
    
    def test_validate_embedding_nan(self):
        """Test embedding with NaN values."""
        import math
        embedding = [0.1] * 767 + [float('nan')]
        with pytest.raises(ValidationError):
            validate_embedding(embedding)
    
    def test_validate_intervention_data_valid(self):
        """Test valid intervention data."""
        validate_intervention_data(
            intervention_text="Test intervention",
            context="Test context",
            task="test_task",
            outcome="task_completed",
            embedding=[0.1] * 768
        )
    
    def test_validate_intervention_data_empty_text(self):
        """Test intervention with empty text."""
        with pytest.raises(ValidationError):
            validate_intervention_data(
                intervention_text="",
                context="Test",
                task="test",
                outcome="task_completed"
            )
    
    def test_validate_user_id_valid(self):
        """Test valid user ID."""
        validate_user_id("user123")
    
    def test_validate_user_id_empty(self):
        """Test empty user ID."""
        with pytest.raises(ValidationError):
            validate_user_id("")
    
    def test_validate_user_id_invalid_chars(self):
        """Test user ID with invalid characters."""
        with pytest.raises(ValidationError):
            validate_user_id("user:123")  # Colon is invalid


class TestEmbeddings:
    """Test embedding generation."""
    
    @pytest.mark.asyncio
    async def test_get_embedding_success(self):
        """Test successful embedding generation."""
        embedding = await get_embedding("test text")
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_get_embedding_empty_text(self):
        """Test embedding with empty text."""
        # Should still work (empty string is valid)
        embedding = await get_embedding("")
        assert len(embedding) == 768
    
    @pytest.mark.asyncio
    async def test_get_embedding_long_text(self):
        """Test embedding with long text."""
        long_text = "test " * 1000
        embedding = await get_embedding(long_text)
        assert len(embedding) == 768
    
    @pytest.mark.asyncio
    async def test_get_embedding_api_error(self):
        """Test embedding with API error."""
        with patch('memory.embeddings._get_client') as mock_client:
            mock_client.return_value.aio.models.embed_content = AsyncMock(
                side_effect=Exception("API Error")
            )
            with pytest.raises(Exception):
                await get_embedding("test")


class TestRedisMemory:
    """Test Redis memory operations."""
    
    @pytest.mark.asyncio
    async def test_record_intervention_success(self, memory):
        """Test successful intervention recording."""
        embedding = await get_embedding("test context")
        key = await memory.record_intervention(
            intervention_text="Test intervention",
            context="test context",
            task="test_task",
            outcome="task_completed",
            embedding=embedding
        )
        assert key is not None
        assert key.startswith(f"user:{memory.user_id}:intervention:")
    
    @pytest.mark.asyncio
    async def test_record_intervention_validation_error(self, memory):
        """Test intervention recording with invalid data."""
        with pytest.raises(ValidationError):
            await memory.record_intervention(
                intervention_text="",  # Empty
                context="test",
                task="test",
                outcome="task_completed",
                embedding=[0.1] * 768
            )
    
    @pytest.mark.asyncio
    async def test_find_similar_interventions(self, memory):
        """Test vector search."""
        # Store a few interventions
        contexts = [
            "I can't focus on homework",
            "I need help with cleaning",
            "I'm feeling overwhelmed"
        ]
        
        for context in contexts:
            embedding = await get_embedding(context)
            await memory.record_intervention(
                intervention_text=f"Help with {context}",
                context=context,
                task="general",
                outcome="task_completed",
                embedding=embedding
            )
        
        # Search for similar
        query_embedding = await get_embedding("I can't concentrate on my studies")
        similar = await memory.find_similar_interventions(
            query_embedding=query_embedding,
            k=3,
            successful_only=True
        )
        
        assert len(similar) > 0
        assert "similarity" in similar[0]
        assert similar[0]["similarity"] > 0
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_reflection(self, memory):
        """Test reflection storage and retrieval."""
        memory.store_reflection(
            insight="Test insight",
            session_summary="Test summary"
        )
        
        reflections = memory.get_recent_reflections(limit=5)
        assert len(reflections) > 0
        assert "Test insight" in reflections
    
    @pytest.mark.asyncio
    async def test_get_context_for_prompt(self, memory):
        """Test context generation."""
        # Add some data
        embedding = await get_embedding("test")
        await memory.record_intervention(
            intervention_text="Test",
            context="test",
            task="test",
            outcome="task_completed",
            embedding=embedding
        )
        memory.store_reflection("Test insight", "Test summary")
        
        context = await memory.get_context_for_prompt()
        assert "insight" in context.lower() or "intervention" in context.lower()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, memory):
        """Test statistics retrieval."""
        stats = memory.get_stats()
        assert "user_id" in stats
        assert "total_interventions" in stats
        assert "total_reflections" in stats


class TestHealthChecks:
    """Test health check functionality."""
    
    def test_redis_connection_check(self, redis_url):
        """Test Redis connection health check."""
        health = MemoryHealthCheck(redis_url)
        result = health.check_redis_connection()
        
        assert "status" in result
        assert "latency_ms" in result
        assert result["status"] in ["healthy", "unhealthy"]
    
    def test_json_support_check(self, redis_url):
        """Test JSON support health check."""
        health = MemoryHealthCheck(redis_url)
        result = health.check_json_support()
        
        assert "status" in result
        assert result["status"] in ["healthy", "unhealthy"]
    
    def test_vector_search_check(self, redis_url, test_user_id):
        """Test vector search health check."""
        health = MemoryHealthCheck(redis_url)
        result = health.check_vector_search(test_user_id)
        
        assert "status" in result
        assert result["status"] in ["healthy", "unhealthy", "warning"]
    
    def test_comprehensive_health(self, redis_url, test_user_id):
        """Test comprehensive health check."""
        health = MemoryHealthCheck(redis_url)
        result = health.get_comprehensive_health(test_user_id)
        
        assert "overall_status" in result
        assert "checks" in result
        assert "timestamp" in result
        assert result["overall_status"] in ["healthy", "degraded", "unhealthy"]


class TestErrorHandling:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self):
        """Test behavior when Redis is unavailable."""
        # Use invalid Redis URL
        invalid_url = "redis://invalid:6379"
        
        with pytest.raises(Exception):
            memory = RedisUserMemory(user_id="test", redis_url=invalid_url)
            # Should fail on initialization or first operation
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_on_search_error(self, memory):
        """Test graceful degradation when vector search fails."""
        # Corrupt the index by trying invalid query
        # Should return empty list, not crash
        invalid_embedding = [float('nan')] * 768
        
        # This should handle gracefully
        result = await memory.find_similar_interventions(
            query_embedding=invalid_embedding,
            k=5
        )
        # Should return empty list or handle error gracefully
        assert isinstance(result, list)


class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_embedding_performance(self):
        """Test embedding generation performance."""
        start = time.time()
        embedding = await get_embedding("test text")
        duration = time.time() - start
        
        assert duration < 5.0  # Should complete in under 5 seconds
        assert len(embedding) == 768
    
    @pytest.mark.asyncio
    async def test_intervention_storage_performance(self, memory):
        """Test intervention storage performance."""
        embedding = await get_embedding("test")
        
        start = time.time()
        await memory.record_intervention(
            intervention_text="Test",
            context="test",
            task="test",
            outcome="task_completed",
            embedding=embedding
        )
        duration = time.time() - start
        
        assert duration < 1.0  # Should complete in under 1 second
    
    @pytest.mark.asyncio
    async def test_vector_search_performance(self, memory):
        """Test vector search performance."""
        # Store some interventions
        for i in range(10):
            embedding = await get_embedding(f"test context {i}")
            await memory.record_intervention(
                intervention_text=f"Intervention {i}",
                context=f"test context {i}",
                task="test",
                outcome="task_completed",
                embedding=embedding
            )
        
        # Search
        query_embedding = await get_embedding("test query")
        start = time.time()
        results = await memory.find_similar_interventions(query_embedding, k=5)
        duration = time.time() - start
        
        assert duration < 2.0  # Should complete in under 2 seconds
        assert len(results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
