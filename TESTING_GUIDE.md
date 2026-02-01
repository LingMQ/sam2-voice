# Testing Guide: Memory System

## Quick Start Testing

### 1. Web UI Testing (Easiest)

#### Start the Web Server
```bash
cd /Users/vaibhavdixit/sam2-voice
source venv/bin/activate
uvicorn web.app:app --host 0.0.0.0 --port 8000 --reload
```

#### Open Test Interface
1. **Memory Test Dashboard**: http://localhost:8000/test
   - View health status
   - Check memory statistics
   - See debug information
   - Auto-refreshes health on load

2. **Voice Interface**: http://localhost:8000
   - Test voice bot with memory enabled
   - Memory automatically initializes
   - Interventions are recorded
   - Reflections generated at session end

### 2. Command Line Testing

#### Health Check
```bash
python scripts/health_check.py browser_user
```

#### Debug Memory
```bash
# Get summary
python scripts/debug_memory.py browser_user summary

# List interventions
python scripts/debug_memory.py browser_user interventions

# Export data
python scripts/debug_memory.py browser_user export
```

#### Run Test Suite
```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/test_memory_production.py -v

# Run with coverage
pytest tests/test_memory_production.py -v --cov=memory --cov-report=html
```

### 3. Programmatic Testing

#### Basic Test Script
```python
import asyncio
import os
from dotenv import load_dotenv
from memory.redis_memory import RedisUserMemory
from memory.embeddings import get_embedding

load_dotenv()

async def test():
    memory = RedisUserMemory(
        user_id="test_user",
        redis_url=os.getenv("REDIS_URL")
    )
    
    # Store intervention
    embedding = await get_embedding("I can't focus on homework")
    key = await memory.record_intervention(
        intervention_text="Let's break this into steps",
        context="I can't focus on homework",
        task="homework",
        outcome="task_completed",
        embedding=embedding
    )
    print(f"Stored: {key}")
    
    # Search
    query_emb = await get_embedding("I'm struggling to concentrate")
    similar = await memory.find_similar_interventions(query_emb, k=3)
    print(f"Found {len(similar)} similar interventions")
    
    # Stats
    stats = memory.get_stats()
    print(f"Stats: {stats}")

asyncio.run(test())
```

## Testing Scenarios

### Scenario 1: First-Time User
1. Open http://localhost:8000/test
2. Check health status (should be healthy)
3. Check memory stats (should show 0 interventions)
4. Open voice interface
5. Say: "Help me break down cleaning my room"
6. Complete a step
7. End session
8. Check memory stats again (should show interventions)

### Scenario 2: Returning User
1. Run a session and create some interventions
2. Start a new session with the same user_id
3. The system should load memory context
4. Say something similar to previous session
5. Check if similar interventions are found

### Scenario 3: Memory Persistence
1. Store interventions in one session
2. Wait a few seconds
3. Check debug info - interventions should still be there
4. Check TTL - should show ~30 days remaining

### Scenario 4: Error Handling
1. Temporarily break Redis connection
2. System should degrade gracefully
3. Check logs for error messages
4. Fix Redis
5. System should recover automatically

## What to Look For

### ✅ Success Indicators
- Health check shows "healthy"
- Memory stats show increasing intervention count
- Vector search returns similar results
- Reflections are generated after sessions
- No errors in console/logs

### ⚠️ Warning Signs
- Health check shows "degraded" or "unhealthy"
- Empty results from vector search (when data exists)
- Slow operations (>2 seconds)
- Errors in logs

### ❌ Failure Indicators
- Cannot connect to Redis
- Embedding generation fails
- Index creation fails
- Data not persisting

## Debugging Tips

### Check Logs
```bash
# View memory system logs
tail -f logs/memory_system.log

# Search for errors
grep ERROR logs/memory_system.log

# Search for specific user
grep "user_id.*browser_user" logs/memory_system.log
```

### Check Redis Directly
```bash
# Connect to Redis
redis-cli -u $REDIS_URL

# List keys
KEYS user:browser_user:*

# Get specific intervention
JSON.GET user:browser_user:intervention:1234567890

# Check index
FT.INFO idx:user:browser_user
```

### Common Issues

1. **"REDIS_URL not configured"**
   - Check `.env` file has `REDIS_URL` set
   - Restart server after setting

2. **"Vector search returns empty"**
   - Check index exists: `FT.INFO idx:user:USER_ID`
   - Check interventions stored: `KEYS user:USER_ID:intervention:*`
   - Verify embedding dimension matches (768)

3. **"Memory context not loading"**
   - Check health status
   - Verify Redis connection
   - Check logs for errors

## Performance Testing

### Load Test
```python
import asyncio
from memory.redis_memory import RedisUserMemory
from memory.embeddings import get_embedding

async def load_test():
    memory = RedisUserMemory("load_test", redis_url)
    
    # Store 100 interventions
    for i in range(100):
        emb = await get_embedding(f"test context {i}")
        await memory.record_intervention(
            f"Intervention {i}",
            f"Context {i}",
            "test",
            "task_completed",
            emb
        )
    
    # Search
    query_emb = await get_embedding("test query")
    results = await memory.find_similar_interventions(query_emb, k=10)
    print(f"Found {len(results)} results")

asyncio.run(load_test())
```

## Integration Testing

### Full Flow Test
1. Start web server
2. Open voice interface
3. Start session
4. Say: "Help me with homework"
5. Agent should call `create_microsteps` tool
6. Check memory - intervention should be stored
7. Say: "I finished step 1"
8. Agent should call `mark_step_complete`
9. Check memory - another intervention stored
10. End session
11. Check for reflection generation
12. Start new session
13. Memory context should be loaded

## Monitoring During Tests

### Watch Logs
```bash
# Terminal 1: Run server
uvicorn web.app:app --reload

# Terminal 2: Watch logs
tail -f logs/memory_system.log | grep -E "(operation|error|performance)"
```

### Watch Redis
```bash
# Monitor Redis commands
redis-cli -u $REDIS_URL MONITOR
```

---

**Ready to test?** Start with the web UI at http://localhost:8000/test!
