# Execution Checklist: Redis Memory System Implementation

Use this checklist to track progress during implementation. Check off items as you complete them.

## Pre-Implementation Setup
- [ ] Verify Redis dependencies in `pyproject.toml` (`redis[hiredis]`, `numpy`)
- [ ] Run `uv sync` to install dependencies
- [ ] Set up Redis Cloud instance (or local Redis) and get `REDIS_URL`
- [ ] Add `REDIS_URL` to `.env` file
- [ ] Test Redis connection: `redis-cli -u $REDIS_URL ping`

## Phase 1: Core Memory Components
- [ ] Create `memory/` directory structure
- [ ] Implement `memory/__init__.py`
- [ ] Implement `memory/embeddings.py` with `get_embedding()` function
  - [ ] Test: Generate embedding for "test text"
  - [ ] Verify: Embedding dimension is 768 (or correct for text-embedding-004)
- [ ] Implement `memory/user_profile.py` with `UserProfile` and `UserProfileManager`
  - [ ] Test: Save and load user profile
- [ ] Implement `memory/redis_memory.py` with `RedisUserMemory` class
  - [ ] `_ensure_index()` - Creates vector search index
  - [ ] `record_intervention()` - Stores interventions with embeddings
  - [ ] `find_similar_interventions()` - Vector search for similar past interventions
  - [ ] `store_reflection()` - Stores session reflections
  - [ ] `get_recent_reflections()` - Retrieves recent insights
  - [ ] `get_context_for_prompt()` - Builds context string for prompts
  - [ ] `get_stats()` - Returns memory statistics
  - [ ] Test: Store intervention → Search for similar → Verify results
- [ ] Implement `memory/reflection.py` with `generate_reflection()` function
  - [ ] Test: Generate reflection from sample transcript

## Phase 2: Voice Session Integration
- [ ] Update `voice/gemini_live.py`:
  - [ ] Add `memory` parameter to `__init__`
  - [ ] Add `_memory_context` attribute
  - [ ] Add `_load_memory_context()` async method
  - [ ] Call `_load_memory_context()` in `connect()`
  - [ ] Update `_build_system_instruction()` to include memory context
  - [ ] Make `_handle_tool_call()` async
- [ ] Update `voice/bot.py`:
  - [ ] Initialize `RedisUserMemory` in `VoiceBot.__init__`
  - [ ] Pass memory to `GeminiLiveClient`
  - [ ] Add end-of-session reflection in `stop()` method
- [ ] Update `voice/agent_bridge.py`:
  - [ ] Initialize `RedisUserMemory` in `__init__`
  - [ ] Make `handle_tool_call()` async (or use async task)
  - [ ] Add `_record_intervention_async()` method
  - [ ] Record interventions after tool calls with appropriate outcomes

## Phase 3: Dynamic Context Injection
- [ ] Create `memory/context_builder.py` (or add to `redis_memory.py`)
  - [ ] Implement `get_personalized_context()` function
  - [ ] Test: Get context for user message
- [ ] Update `voice/gemini_live.py`:
  - [ ] Add `_inject_memory_context()` method
  - [ ] Call before sending user messages (or integrate into system instruction)

## Phase 4: Outcome Tracking
- [ ] Add outcome analysis logic:
  - [ ] Detect task completion signals
  - [ ] Detect re-engagement signals
  - [ ] Detect distraction signals
- [ ] Enhance intervention recording with better context:
  - [ ] Include recent user messages
  - [ ] Include current task state
  - [ ] Include timing information

## Phase 5: Testing
- [ ] Create `tests/test_memory_system.py`:
  - [ ] Test embedding generation
  - [ ] Test intervention storage
  - [ ] Test vector search
  - [ ] Test reflection generation
- [ ] Create `tests/test_voice_memory_integration.py`:
  - [ ] Test full integration flow
- [ ] Manual testing:
  - [ ] Start voice bot with memory enabled
  - [ ] Verify memory context in system prompt
  - [ ] Call tools and verify interventions recorded
  - [ ] Send similar messages and verify context retrieval
  - [ ] End session and verify reflection generated
  - [ ] Start new session and verify improved context

## Phase 6: Error Handling
- [ ] Add graceful degradation for Redis failures
- [ ] Add retry logic for embedding API calls
- [ ] Add error handling for vector search failures
- [ ] Add logging for all error cases

## Phase 7: Verification
- [ ] Run all tests: `pytest tests/`
- [ ] Manual end-to-end test:
  1. Start bot: `python main.py --user-id test_user`
  2. Say: "Help me break down cleaning my room"
  3. Complete a step: "I finished step 1"
  4. End session (Ctrl+C)
  5. Verify reflection generated
  6. Start new session with same user
  7. Verify memory context includes previous session
- [ ] Check Redis:
  - [ ] Interventions stored: `redis-cli --scan --pattern "user:test_user:intervention:*"`
  - [ ] Reflections stored: `redis-cli --scan --pattern "user:test_user:reflection:*"`
  - [ ] Vector index exists: `redis-cli FT.INFO idx:user:test_user`

## Phase 8: Documentation
- [ ] Update `README.md` with memory system documentation
- [ ] Add comments to all memory-related code
- [ ] Document Redis setup requirements
- [ ] Document environment variables needed

## Final Checklist
- [ ] All tests pass
- [ ] No linter errors
- [ ] Memory system works end-to-end
- [ ] Error handling works (test with Redis down)
- [ ] Documentation updated
- [ ] Ready for demo!

---

## Quick Test Commands

```bash
# Test Redis connection
redis-cli -u $REDIS_URL ping

# Test embedding generation
python -c "import asyncio; from memory.embeddings import get_embedding; print(asyncio.run(get_embedding('test')))"

# Test memory storage
python -c "import asyncio, os; from memory.redis_memory import RedisUserMemory; from memory.embeddings import get_embedding; m = RedisUserMemory('test', os.getenv('REDIS_URL')); emb = asyncio.run(get_embedding('test')); print(asyncio.run(m.record_intervention('test intervention', 'test context', 'test task', 'task_completed', emb)))"

# Check Redis keys
redis-cli -u $REDIS_URL --scan --pattern "user:*"

# Run voice bot with memory
python main.py --user-id test_user
```

---

## Troubleshooting

**Issue: Redis connection fails**
- Check `REDIS_URL` format: `redis://default:password@host:port`
- Verify Redis instance is running
- Check network connectivity

**Issue: Vector search returns no results**
- Verify index was created: `redis-cli FT.INFO idx:user:USER_ID`
- Check if interventions were stored: `redis-cli --scan --pattern "user:USER_ID:intervention:*"`
- Verify embedding dimension matches index (768)

**Issue: Embeddings fail**
- Check `GOOGLE_API_KEY` is set
- Verify API key has access to embedding model
- Check API quota/rate limits

**Issue: Memory context not appearing in prompts**
- Verify `_load_memory_context()` is called in `connect()`
- Check `_memory_context` is not None
- Verify `_build_system_instruction()` includes memory context
