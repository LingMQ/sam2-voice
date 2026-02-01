# Quick Start: Redis Memory System Implementation

This is your starting point. Follow these documents in order for a complete implementation.

## 📚 Documentation Structure

1. **DETAILED_EXECUTION_PLAN.md** - Complete step-by-step implementation guide
   - Every function, every method, every integration point
   - Read this first to understand the full scope

2. **EXECUTION_CHECKLIST.md** - Progress tracking checklist
   - Use this while implementing to track your progress
   - Check off items as you complete them

3. **TECHNICAL_REFERENCE.md** - Code patterns and API details
   - Exact code snippets for Redis, Gemini APIs
   - Copy-paste ready patterns
   - Reference when implementing specific components

4. **This file** - Quick orientation and starting point

## 🎯 What We're Building

A **self-improving memory system** that:
- Stores interventions (what the agent did) with semantic embeddings
- Retrieves similar past interventions using vector search
- Generates insights at end of each session
- Injects personalized context into agent prompts
- Gets better over time as it learns what works for each user

## 🚀 Quick Start (5 Steps)

### Step 1: Setup (5 minutes)
```bash
# 1. Verify dependencies
cat pyproject.toml | grep -E "redis|numpy"

# 2. Install if missing
uv sync

# 3. Set up Redis (choose one):
# Option A: Redis Cloud (recommended)
# - Go to https://redis.com/try-free/
# - Create free instance
# - Copy connection URL

# Option B: Local Redis
# - Install: brew install redis (Mac) or apt-get install redis (Linux)
# - Start: redis-server
# - URL: redis://localhost:6379

# 4. Add to .env
echo "REDIS_URL=redis://your-url-here" >> .env
```

### Step 2: Create Module Structure (2 minutes)
```bash
mkdir -p memory
touch memory/__init__.py
touch memory/embeddings.py
touch memory/user_profile.py
touch memory/redis_memory.py
touch memory/reflection.py
```

### Step 3: Implement Core Components (Follow DETAILED_EXECUTION_PLAN.md)
**Order:**
1. `memory/embeddings.py` - Get embeddings from Gemini
2. `memory/user_profile.py` - User profile management
3. `memory/redis_memory.py` - Core memory class with vector search
4. `memory/reflection.py` - End-of-session reflection

**Time estimate:** 2-3 hours

### Step 4: Integrate with Voice Session (Follow DETAILED_EXECUTION_PLAN.md Phase 3)
**Files to modify:**
- `voice/gemini_live.py` - Load memory context
- `voice/bot.py` - Initialize memory, end-of-session reflection
- `voice/agent_bridge.py` - Record interventions

**Time estimate:** 1-2 hours

### Step 5: Test & Verify (30 minutes)
```bash
# Test embedding
python -c "import asyncio; from memory.embeddings import get_embedding; print(len(asyncio.run(get_embedding('test'))))"

# Test memory storage
# (Use test scripts from DETAILED_EXECUTION_PLAN.md)

# Test full integration
python main.py --user-id test_user
```

## 📋 Implementation Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Setup & Dependencies                                  │
│    - Redis connection                                     │
│    - Verify dependencies                                  │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Core Memory Components                                │
│    - embeddings.py (Gemini API)                          │
│    - user_profile.py (Profile management)                │
│    - redis_memory.py (Vector search)                     │
│    - reflection.py (Insight generation)                  │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Voice Session Integration                             │
│    - Load memory context in prompts                     │
│    - Record interventions after tool calls               │
│    - Generate reflections at session end                │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Dynamic Context Injection                             │
│    - Retrieve similar interventions                      │
│    - Inject as few-shot examples                        │
└────────────────────┬────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Testing & Validation                                  │
│    - Unit tests                                          │
│    - Integration tests                                   │
│    - End-to-end verification                             │
└─────────────────────────────────────────────────────────┘
```

## 🔍 Key Concepts

### Vector Search
- User says: "I can't focus on homework"
- System embeds this text → 768-dimensional vector
- Searches Redis for similar past interventions
- Returns: "Quest mode worked for dishes" (similarity: 0.92)
- Agent uses this as inspiration for response

### Memory Decay
- Interventions expire after 30 days (TTL)
- Old memories fade naturally
- System focuses on recent, relevant patterns

### Self-Improvement Loop
```
Session 1: User says "can't focus" → Agent suggests "break into steps"
           → User completes task → Record: "break into steps" worked
           
Session 2: User says "can't focus" → System finds past success
           → Agent uses similar approach → Better response
           
Session 3: System has learned user's preferences
           → Even better personalized responses
```

## ⚠️ Common Pitfalls

1. **Embedding Dimension Mismatch**
   - Problem: Index expects 768, but embedding is 1024
   - Solution: Verify actual dimension, update index DIM

2. **Redis Connection Issues**
   - Problem: Connection refused or timeout
   - Solution: Test connection first, use graceful degradation

3. **Async/Await Errors**
   - Problem: Calling async function without await
   - Solution: Ensure all async functions are properly awaited

4. **Vector Search Returns Empty**
   - Problem: No results even with stored interventions
   - Solution: Verify index exists, check embedding format, verify query syntax

## 🎓 Learning Resources

- **Redis Vector Search:** https://redis.io/docs/latest/develop/interact/search-and-query/query/vector-search/
- **Gemini Embeddings:** https://ai.google.dev/gemini-api/docs/embeddings
- **Weave Observability:** https://docs.wandb.ai/weave

## ✅ Success Criteria

After implementation, you should be able to:

1. ✅ Store interventions in Redis with embeddings
2. ✅ Search for similar past interventions
3. ✅ Generate session reflections
4. ✅ See memory context in agent prompts
5. ✅ Observe improvement over multiple sessions

## 🆘 Getting Help

If stuck:
1. Check **TECHNICAL_REFERENCE.md** for exact code patterns
2. Review **DETAILED_EXECUTION_PLAN.md** for step-by-step guidance
3. Verify Redis connection and embedding dimension
4. Check error logs for specific issues
5. Test components individually before integration

## 🎯 Next Steps After Implementation

Once memory system is working:
1. Add custom Weave scorers (Phase 7 in implementation plan)
2. Optimize performance (caching, batching)
3. Enhance outcome detection
4. Add user profile management (diagnosis, preferences)
5. Create demo showing improvement over sessions

---

**Ready to start?** Open **DETAILED_EXECUTION_PLAN.md** and begin with Phase 1, Step 1.1!
