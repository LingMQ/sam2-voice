# Technical Reference: Redis Memory System Implementation

This document provides exact code patterns, API calls, and technical details needed for implementation.

## Gemini Embedding API

### Model Details
- **Model:** `text-embedding-004`
- **Dimension:** Verify during implementation (likely 768 or 1024)
- **API Method:** `client.aio.models.embed_content()`

### Code Pattern
```python
from google import genai
import os

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Single embedding
result = await client.aio.models.embed_content(
    model="text-embedding-004",
    contents="text to embed"
)
embedding = result.embeddings[0].values  # List of floats

# Verify dimension
print(f"Embedding dimension: {len(embedding)}")
```

## Redis Vector Search Setup

### Required Redis Version
- Redis Stack 7.0+ (includes RediSearch with vector search)
- Or Redis Cloud with vector search enabled

### Index Schema
```python
from redis.commands.search.field import TextField, VectorField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

# Vector field configuration
# DIM: Must match embedding dimension (verify with actual embedding)
# TYPE: FLOAT32 for Gemini embeddings
# DISTANCE_METRIC: COSINE for semantic similarity

schema = (
    TextField("$.intervention", as_name="intervention"),
    TextField("$.context", as_name="context"),
    TagField("$.outcome", as_name="outcome"),  # TagField for exact matches
    TextField("$.task", as_name="task"),
    NumericField("$.timestamp", as_name="timestamp"),
    VectorField(
        "$.embedding",
        "FLAT",  # Index type: FLAT (exact) or HNSW (approximate, faster)
        {
            "TYPE": "FLOAT32",
            "DIM": 768,  # VERIFY: Check actual embedding dimension
            "DISTANCE_METRIC": "COSINE"
        },
        as_name="embedding"
    )
)

definition = IndexDefinition(
    prefix=[f"user:{user_id}:intervention:"],
    index_type=IndexType.JSON
)

client.ft(index_name).create_index(schema, definition=definition)
```

### Vector Search Query
```python
from redis.commands.search.query import Query
import numpy as np

# Convert embedding to bytes
query_vector = np.array(embedding, dtype=np.float32).tobytes()

# Build query
# KNN = k-nearest neighbors
# $query_vector = parameter placeholder
# AS distance = return distance as "distance" field
query = Query(
    f"(@outcome:{{task_completed|re_engaged}})=>[KNN {k} @embedding $query_vector AS distance]"
).sort_by("distance").return_fields(
    "intervention", "context", "outcome", "task", "distance"
).dialect(2)  # Dialect 2 required for vector search

# Execute
results = client.ft(index_name).search(
    query,
    query_params={"query_vector": query_vector}
)

# Process results
for doc in results.docs:
    similarity = 1 - float(doc.distance)  # Convert distance to similarity
    print(f"Intervention: {doc.intervention}, Similarity: {similarity:.2f}")
```

## Redis JSON Operations

### Storing JSON
```python
import json
from datetime import datetime

key = f"user:{user_id}:intervention:{int(datetime.now().timestamp() * 1000)}"
data = {
    "intervention": "text",
    "context": "text",
    "task": "text",
    "outcome": "task_completed",
    "timestamp": datetime.now().timestamp(),
    "embedding": embedding_list  # List of floats
}

# Store
client.json().set(key, "$", data)

# Set TTL (30 days)
client.expire(key, 60 * 60 * 24 * 30)
```

### Retrieving JSON
```python
# Get single document
data = client.json().get(key)

# Scan for keys
pattern = f"user:{user_id}:intervention:*"
keys = list(client.scan_iter(pattern, count=1000))

# Get multiple documents
for key in keys:
    data = client.json().get(key)
    if data:
        print(data["intervention"])
```

## Gemini Reflection Generation

### Prompt Template
```python
prompt = f"""Analyze this support session for someone with ADHD/autism.

SESSION TRANSCRIPT:
{transcript_str}

PREVIOUS INSIGHTS ABOUT THIS USER:
{previous_str}

Generate ONE brief insight (1-2 sentences) about what we learned from this session.
Focus on:
- What intervention styles worked or didn't work
- User's preferences or patterns you noticed
- What to do differently next time

Keep it specific and actionable."""

response = await client.aio.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt
)
insight = response.text.strip()
```

## Outcome Detection Patterns

### Completion Signals
```python
completion_keywords = [
    "done", "finished", "completed", "all done", "finished it",
    "got it done", "accomplished", "finished the task"
]

def detect_completion(message: str) -> bool:
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in completion_keywords)
```

### Re-engagement Signals
```python
reengagement_keywords = [
    "okay", "ok", "sounds good", "let's do it", "yes", "yeah",
    "sure", "alright", "ready", "let's go", "I'll do it"
]
```

### Distraction Signals
```python
distraction_keywords = [
    "wait", "hold on", "what was I doing", "lost track",
    "forgot", "distracted", "off track"
]
```

## Async/Await Patterns

### Making Sync Function Async
```python
# Original sync function
def handle_tool_call(name: str, args: dict) -> str:
    return "result"

# Make async
async def handle_tool_call(name: str, args: dict) -> str:
    return "result"

# Or spawn async task from sync function
def handle_tool_call(name: str, args: dict) -> str:
    if self.memory:
        asyncio.create_task(self._record_async(name, args))
    return "result"
```

### Async Context Manager Pattern
```python
# For Redis connections (if needed)
async with redis.asyncio.from_url(redis_url) as client:
    data = await client.json().get(key)
```

## Error Handling Patterns

### Graceful Degradation
```python
try:
    if self.memory:
        context = await self.memory.get_context_for_prompt()
except Exception as e:
    logger.warning(f"Memory context unavailable: {e}")
    context = ""  # Continue without memory
```

### Retry Logic
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_embedding_with_retry(text: str) -> list[float]:
    return await get_embedding(text)
```

## Weave Integration

### Decorating Functions
```python
import weave

@weave.op()
async def record_intervention(...):
    # Function implementation
    pass

# Weave automatically tracks:
# - Function inputs/outputs
# - Execution time
# - Errors
# - Can be viewed in W&B dashboard
```

## Testing Patterns

### Mock Redis for Tests
```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_redis():
    redis_mock = Mock()
    redis_mock.json().set = Mock()
    redis_mock.json().get = Mock(return_value={"intervention": "test"})
    redis_mock.ft.return_value.search = Mock(return_value=Mock(docs=[]))
    return redis_mock
```

### Async Test Pattern
```python
import pytest

@pytest.mark.asyncio
async def test_memory_storage():
    memory = RedisUserMemory("test_user", "redis://localhost:6379")
    emb = await get_embedding("test")
    key = await memory.record_intervention(
        "test", "test", "test", "task_completed", emb
    )
    assert key is not None
```

## Environment Variables

### Required
```bash
GOOGLE_API_KEY=your_key_here
REDIS_URL=redis://default:password@host:port
```

### Optional
```bash
WANDB_API_KEY=your_key_here  # For Weave observability
GEMINI_LIVE_MODEL=gemini-2.5-flash-native-audio-latest
```

## Common Issues & Solutions

### Issue: "Index already exists"
```python
# Solution: Check if index exists before creating
try:
    client.ft(index_name).info()
except redis.ResponseError:
    # Index doesn't exist, create it
    client.ft(index_name).create_index(...)
```

### Issue: "Vector dimension mismatch"
```python
# Solution: Verify embedding dimension matches index
embedding = await get_embedding("test")
actual_dim = len(embedding)
print(f"Actual dimension: {actual_dim}")
# Update index DIM to match actual_dim
```

### Issue: "Redis connection refused"
```python
# Solution: Test connection first
import redis
try:
    client = redis.from_url(redis_url)
    client.ping()
    print("Redis connected")
except Exception as e:
    print(f"Redis connection failed: {e}")
    # Use fallback or raise
```

## Performance Tips

### Batch Operations
```python
# Instead of multiple individual calls
for item in items:
    await memory.record_intervention(...)

# Consider batching (if API supports)
# Or use asyncio.gather for parallel execution
await asyncio.gather(*[
    memory.record_intervention(...) for item in items
])
```

### Caching
```python
# Cache memory context for session duration
class GeminiLiveClient:
    def __init__(self):
        self._memory_context_cache = None
        self._cache_timestamp = None
    
    async def _load_memory_context(self):
        # Refresh cache every 5 minutes
        if (self._memory_context_cache is None or 
            time.time() - self._cache_timestamp > 300):
            self._memory_context_cache = await self.memory.get_context_for_prompt()
            self._cache_timestamp = time.time()
        return self._memory_context_cache
```

## Verification Commands

### Redis CLI Commands
```bash
# Connect to Redis
redis-cli -u $REDIS_URL

# Check connection
PING

# List all keys for user
KEYS user:test_user:*

# Get specific document
JSON.GET user:test_user:intervention:1234567890

# Check index info
FT.INFO idx:user:test_user

# Search index
FT.SEARCH idx:user:test_user "*" LIMIT 0 10

# Check TTL
TTL user:test_user:intervention:1234567890
```

### Python Verification
```python
# Verify embedding dimension
emb = await get_embedding("test")
print(f"Dimension: {len(emb)}")
print(f"Type: {type(emb[0])}")  # Should be float

# Verify Redis connection
import redis
client = redis.from_url(os.getenv("REDIS_URL"))
print(client.ping())  # Should print True

# Verify index exists
try:
    info = client.ft("idx:user:test_user").info()
    print("Index exists")
except:
    print("Index does not exist")
```
