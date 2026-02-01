# How to View Stored Memory Data

## Option 1: Web UI (Easiest)

### Memory Test Dashboard
1. Open: http://localhost:8000/test
2. Click "View Interventions" to see all stored interventions
3. Click "View Reflections" to see session reflections
4. Click "Get Debug Info" for comprehensive memory state

**What you'll see:**
- Intervention text (what the agent did)
- Context (user's message/situation)
- Task being worked on
- Outcome (task_completed, re_engaged, etc.)
- Timestamp
- TTL (time until expiration)

## Option 2: Command Line

### View Interventions
```bash
python scripts/debug_memory.py browser_user interventions
```

### View Reflections
```bash
python scripts/debug_memory.py browser_user reflections
```

### Get Summary
```bash
python scripts/debug_memory.py browser_user summary
```

### Export All Data
```bash
python scripts/debug_memory.py browser_user export
# Creates memory_export_browser_user.json
```

## Option 3: Direct Redis Access

### Connect to Redis
```bash
redis-cli -u $REDIS_URL
```

### List All Keys for User
```redis
KEYS user:browser_user:*
```

### View Specific Intervention
```redis
# Get a key from the list above, then:
JSON.GET user:browser_user:intervention:1234567890

# Or get all fields:
JSON.GET user:browser_user:intervention:1234567890 $
```

### View Reflection
```redis
JSON.GET user:browser_user:reflection:1234567890
```

### Count Interventions
```redis
# Count all intervention keys
KEYS user:browser_user:intervention:* | wc -l
```

### Check TTL (Time Until Expiration)
```redis
TTL user:browser_user:intervention:1234567890
# Returns seconds until expiration (-1 = no expiration, -2 = key doesn't exist)
```

### View Index Information
```redis
FT.INFO idx:user:browser_user
```

### Search Interventions by Outcome
```redis
FT.SEARCH idx:user:browser_user "@outcome:task_completed" LIMIT 0 10
```

## Option 4: Python Script

```python
import asyncio
import os
from dotenv import load_dotenv
from memory.redis_memory import RedisUserMemory
from memory.debug import MemoryDebugger

load_dotenv()

async def view_memory():
    memory = RedisUserMemory(
        user_id="browser_user",
        redis_url=os.getenv("REDIS_URL")
    )
    debugger = MemoryDebugger(memory)
    
    # Get summary
    summary = debugger.get_memory_summary()
    print("Summary:", summary)
    
    # Get interventions
    interventions = debugger.inspect_interventions(limit=10)
    print(f"\nFound {len(interventions)} interventions:")
    for iv in interventions:
        print(f"\nKey: {iv['key']}")
        print(f"Data: {iv['data']}")
        print(f"TTL: {iv['ttl']} seconds")
    
    # Get reflections
    reflections = debugger.inspect_reflections(limit=5)
    print(f"\nFound {len(reflections)} reflections:")
    for rf in reflections:
        print(f"\nKey: {rf['key']}")
        print(f"Insight: {rf['data']['insight']}")

asyncio.run(view_memory())
```

## Understanding the Data Structure

### Intervention Structure
```json
{
  "intervention": "Used create_microsteps: Created 3 micro-steps for: cleaning my room",
  "context": "Help me break down cleaning my room",
  "task": "cleaning my room",
  "outcome": "task_started",
  "timestamp": 1769934000.123,
  "embedding": [0.123, -0.456, ...]  // 768 dimensions
}
```

### Reflection Structure
```json
{
  "insight": "User responds well to task breakdown into micro-steps",
  "session_summary": "USER: Help me with homework\nASSISTANT: Let's break it down...",
  "timestamp": "2024-02-01T12:00:00"
}
```

## Key Locations in Redis

- **Interventions**: `user:{user_id}:intervention:{timestamp_ms}`
- **Reflections**: `user:{user_id}:reflection:{timestamp_ms}`
- **Vector Index**: `idx:user:{user_id}`

## Quick Commands Reference

```bash
# View in web UI
open http://localhost:8000/test

# View via command line
python scripts/debug_memory.py browser_user summary

# View in Redis CLI
redis-cli -u $REDIS_URL
> KEYS user:browser_user:*
> JSON.GET user:browser_user:intervention:1234567890
```

---

**Tip**: The web UI at `/test` is the easiest way to view stored data!
