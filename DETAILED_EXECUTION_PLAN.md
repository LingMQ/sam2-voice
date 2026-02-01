# Detailed Execution Plan: Redis Memory System & Self-Improvement Loop

## Overview
This plan provides step-by-step instructions to implement Phase 6 (Redis Memory System) and Phase 7 (Self-Improvement Integration) from the implementation plan. Each step is designed to be executed sequentially without requiring additional analysis.

---

## Phase 1: Redis Memory Infrastructure Setup

### Step 1.1: Verify Redis Dependencies
**Action:** Check if Redis dependencies are in pyproject.toml
**Expected:** `redis[hiredis]` and `numpy` should be in dependencies
**If missing:** Add them to pyproject.toml dependencies list
**Test:** Run `uv sync` to install dependencies

### Step 1.2: Create Memory Module Structure
**Action:** Create the memory module directory structure
**Commands:**
```bash
mkdir -p memory
touch memory/__init__.py
touch memory/redis_memory.py
touch memory/embeddings.py
touch memory/reflection.py
touch memory/user_profile.py  # For user profile management (diagnosis, preferences)
```

### Step 1.3: Verify Environment Configuration
**Action:** Check if REDIS_URL is documented/configured
**Expected:** REDIS_URL should be in .env or documented
**Action if missing:** Add to .env.example:
```ini
REDIS_URL=redis://default:password@your-redis-cloud-instance:6379
```
**Note:** For local testing, can use `redis://localhost:6379` if Redis is running locally

---

## Phase 2: Implement Core Memory Components

### Step 2.1: Implement `memory/embeddings.py`
**Purpose:** Get embeddings from Gemini text-embedding-004 model
**Implementation Details:**
- Import: `from google import genai`, `import os`, `import weave`
- Create client: `genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))`
- Function: `async def get_embedding(text: str) -> list[float]`
- Use model: `text-embedding-004`
- Method: `client.aio.models.embed_content(model="text-embedding-004", contents=text)`
- Return: `result.embeddings[0].values` (list of floats)
- Decorate with `@weave.op()` for observability
- Handle errors gracefully (return empty list or raise)

**Test:** Create simple test script:
```python
import asyncio
from memory.embeddings import get_embedding

async def test():
    emb = await get_embedding("test text")
    print(f"Embedding dim: {len(emb)}")
    assert len(emb) > 0

asyncio.run(test())
```

### Step 2.2: Implement `memory/user_profile.py`
**Purpose:** Manage user profiles (diagnosis, preferences, onboarding state)
**Implementation Details:**
- Class: `UserProfile` (dataclass)
- Fields:
  - `user_id: str`
  - `diagnosis: str` (NONE, ADHD, AUTISM, BOTH)
  - `diagnosis_source: str` (OFFICIAL, SELF, UNSPECIFIED)
  - `onboarding_complete: bool = False`
  - `preferred_checkin_interval: float = 3.0` (minutes)
  - `sensory_sensitivities: list[str] = field(default_factory=list)`
- Class: `UserProfileManager`
  - Methods:
    - `__init__(self, redis_url: str)`
    - `async def get_profile(self, user_id: str) -> Optional[UserProfile]`
    - `async def save_profile(self, profile: UserProfile)`
    - `async def update_diagnosis(self, user_id: str, diagnosis: str, source: str)`
    - `async def get_or_create(self, user_id: str) -> UserProfile`
- Redis key format: `sam2voice:profile:{user_id}`
- Use Redis JSON: `client.json().set(key, "$", profile_dict)`
- TTL: None (profiles don't expire)

**Test:** Create test script to save/load profile

### Step 2.3: Implement `memory/redis_memory.py` - Core Class
**Purpose:** Redis-backed memory with vector search for semantic retrieval
**Implementation Details:**

**Class: `RedisUserMemory`**
- `__init__(self, user_id: str, redis_url: str)`
  - Store `user_id`, create Redis client: `redis.from_url(redis_url, decode_responses=False)`
  - Set `index_name = f"idx:user:{user_id}"`
  - Call `self._ensure_index()`

**Method: `_ensure_index(self)`**
- Try: `self.client.ft(self.index_name).info()` to check if index exists
- If `redis.ResponseError` (index doesn't exist), create it:
  - Schema fields:
    - `TextField("$.intervention", as_name="intervention")`
    - `TextField("$.context", as_name="context")`
    - `TagField("$.outcome", as_name="outcome")`
    - `TextField("$.task", as_name="task")`
    - `NumericField("$.timestamp", as_name="timestamp")`
    - `VectorField("$.embedding", "FLAT", {"TYPE": "FLOAT32", "DIM": 768, "DISTANCE_METRIC": "COSINE"}, as_name="embedding")`
  - Index definition:
    - `prefix=[f"user:{self.user_id}:intervention:"]`
    - `index_type=IndexType.JSON`
  - Create: `self.client.ft(self.index_name).create_index(schema, definition=...)`

**Method: `async def record_intervention(...)`**
- Parameters:
  - `intervention_text: str` - What the agent said/did
  - `context: str` - User's situation/request
  - `task: str` - Task being worked on
  - `outcome: str` - Result: "task_completed", "re_engaged", "distracted", "abandoned"
  - `embedding: list[float]` - Pre-computed embedding (from embeddings.py)
- Generate key: `f"user:{self.user_id}:intervention:{int(datetime.now().timestamp() * 1000)}"`
- Data structure:
  ```python
  {
    "intervention": intervention_text,
    "context": context,
    "task": task,
    "outcome": outcome,
    "timestamp": datetime.now().timestamp(),
    "embedding": embedding
  }
  ```
- Store: `self.client.json().set(key, "$", data)`
- Set TTL: `self.client.expire(key, 60 * 60 * 24 * 30)` (30 days)
- Return key
- Decorate with `@weave.op()`

**Method: `async def find_similar_interventions(...)`**
- Parameters:
  - `query_embedding: list[float]` - Embedding of current user message
  - `k: int = 5` - Number of results
  - `successful_only: bool = True` - Only return successful outcomes
- Convert embedding to bytes: `np.array(query_embedding, dtype=np.float32).tobytes()`
- Build filter: `"@outcome:{task_completed|re_engaged}"` if successful_only else `"*"`
- Query: `Query(f"({filter_str})=>[KNN {k} @embedding $query_vector AS distance]").sort_by("distance").return_fields("intervention", "context", "outcome", "task", "distance").dialect(2)`
- Execute: `self.client.ft(self.index_name).search(q, query_params={"query_vector": query_vector})`
- Transform results:
  ```python
  [
    {
      "intervention": doc.intervention,
      "context": doc.context,
      "outcome": doc.outcome,
      "task": doc.task,
      "similarity": 1 - float(doc.distance)
    }
    for doc in results.docs
  ]
  ```
- Handle errors (return empty list)
- Decorate with `@weave.op()`

**Method: `def store_reflection(self, insight: str, session_summary: str)`**
- Key: `f"user:{self.user_id}:reflection:{int(datetime.now().timestamp() * 1000)}"`
- Data: `{"insight": insight, "session_summary": session_summary[:500], "timestamp": datetime.now().isoformat()}`
- Store: `self.client.json().set(key, "$", data)`
- TTL: 90 days
- Decorate with `@weave.op()`

**Method: `def get_recent_reflections(self, limit: int = 5) -> list[str]`**
- Pattern: `f"user:{self.user_id}:reflection:*"`
- Scan: `list(self.client.scan_iter(pattern, count=100))`
- Sort by key (reverse), take first `limit`
- Extract insights: `[data["insight"] for key in keys if (data := self.client.json().get(key)) and "insight" in data]`
- Return list of insight strings

**Method: `async def get_context_for_prompt(self) -> str`**
- Get recent reflections (last 3)
- Count interventions: `len(list(self.client.scan_iter(f"user:{self.user_id}:intervention:*", count=1000)))`
- Build context string:
  - If reflections exist: `"## Key insights from past sessions:\n" + "\n".join(f"- {r}" for r in reflections)`
  - If interventions exist: `"## Memory status:\n- {count} past interventions stored"`
- Return combined string or `"New user - no history yet."`
- Decorate with `@weave.op()`

**Method: `def get_stats(self) -> dict`**
- Count interventions and reflections
- Return: `{"user_id": self.user_id, "total_interventions": count, "total_reflections": count}`

**Test:** Create test script:
```python
import asyncio
from memory.redis_memory import RedisUserMemory
from memory.embeddings import get_embedding

async def test():
    memory = RedisUserMemory("test_user", os.getenv("REDIS_URL"))
    emb = await get_embedding("I can't focus on homework")
    key = await memory.record_intervention(
        "Let's break this into 3 tiny steps",
        "I can't focus on homework",
        "homework",
        "task_completed",
        emb
    )
    print(f"Stored: {key}")
    
    similar = await memory.find_similar_interventions(emb, k=3)
    print(f"Found {len(similar)} similar interventions")

asyncio.run(test())
```

### Step 2.4: Implement `memory/reflection.py`
**Purpose:** Generate end-of-session reflections using Gemini
**Implementation Details:**
- Import: `from google import genai`, `import os`, `import weave`
- Function: `async def generate_reflection(memory: RedisUserMemory, transcript: list[dict]) -> str`
- Get transcript (last 20 messages): `transcript[-20:]`
- Format: `"\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in transcript])`
- Get previous insights: `memory.get_recent_reflections(3)`
- Build prompt:
  ```
  Analyze this support session for someone with ADHD/autism.

  SESSION TRANSCRIPT:
  {transcript_str}

  PREVIOUS INSIGHTS ABOUT THIS USER:
  {previous_str}

  Generate ONE brief insight (1-2 sentences) about what we learned from this session.
  Focus on:
  - What intervention styles worked or didn't work
  - User's preferences or patterns you noticed
  - What to do differently next time

  Keep it specific and actionable.
  ```
- Call Gemini: `client.aio.models.generate_content(model="gemini-2.0-flash", contents=prompt)`
- Extract: `response.text.strip()`
- Store: `memory.store_reflection(insight, transcript_str)`
- Return insight
- Decorate with `@weave.op()`

**Test:** Create test with sample transcript

---

## Phase 3: Integration with Voice Session

### Step 3.1: Update `voice/gemini_live.py` - Load Memory Context
**File:** `voice/gemini_live.py`
**Method to modify:** `_build_system_instruction(self)`
**Changes:**
1. Import: `from memory.redis_memory import RedisUserMemory`
2. In `__init__`, add optional `memory: Optional[RedisUserMemory] = None` parameter
3. Store: `self.memory = memory`
4. In `_build_system_instruction()`:
   - If `self.memory` exists:
     - Call: `memory_context = await self.memory.get_context_for_prompt()` (needs to be async or cached)
     - Append to instruction: `f"{base_instruction}\n\n---\nPERSONALIZED CONTEXT:\n{memory_context}\n---"`
   - **Note:** Since `_build_system_instruction` is called during `connect()` which is async, we can make it async or cache the context
   - **Better approach:** Make `_build_system_instruction` async, cache context in `__init__` or during connect

**Implementation:**
- Add `self._memory_context: Optional[str] = None` to `__init__`
- Add method: `async def _load_memory_context(self)`:
  ```python
  if self.memory:
      self._memory_context = await self.memory.get_context_for_prompt()
  ```
- Call `await self._load_memory_context()` at start of `connect()` method
- In `_build_system_instruction()`, use `self._memory_context` if available

### Step 3.2: Update `voice/bot.py` - Initialize Memory
**File:** `voice/bot.py`
**Changes:**
1. Import: `from memory.redis_memory import RedisUserMemory`, `import os`
2. In `VoiceBot.__init__`, add:
   ```python
   # Initialize memory if Redis URL is available
   self.memory = None
   redis_url = os.getenv("REDIS_URL")
   if redis_url:
       self.memory = RedisUserMemory(user_id=user_id, redis_url=redis_url)
   ```
3. Pass memory to client: In `VoiceBot.__init__`, update client creation:
   ```python
   self.client = GeminiLiveClient(
       config=config,
       session_id=session_id,
       user_id=user_id,
       memory=self.memory,  # Add this
   )
   ```

### Step 3.3: Update `voice/agent_bridge.py` - Record Interventions
**File:** `voice/agent_bridge.py`
**Purpose:** Record intervention outcomes after tool calls
**Changes:**
1. Import: `from memory.redis_memory import RedisUserMemory`, `from memory.embeddings import get_embedding`, `import os`, `import asyncio`
2. In `AgentToolBridge.__init__`, add:
   ```python
   # Initialize memory if available
   self.memory = None
   redis_url = os.getenv("REDIS_URL")
   if redis_url:
       self.memory = RedisUserMemory(user_id=user_id, redis_url=redis_url)
   ```
3. Add method: `async def _record_intervention_async(self, tool_name: str, args: dict, result: str, outcome: str = "unknown")`
   - Get current context from session state or conversation context
   - Get embedding of user's last message or context
   - Call: `await self.memory.record_intervention(...)`
4. Update `handle_tool_call` to be async: `async def handle_tool_call(self, name: str, args: dict) -> str`
5. After each tool call, determine outcome and record:
   - For `create_microsteps`: outcome = "task_started"
   - For `mark_step_complete`: outcome = "task_progress"
   - For `log_micro_win`: outcome = "task_completed"
   - For `schedule_checkin`: outcome = "re_engaged"
   - For emotional tools: outcome = "re_engaged"
   - Default: outcome = "intervention_applied"
6. Call: `await self._record_intervention_async(name, args, result, outcome)`
7. **Note:** Since `handle_tool_call` in `gemini_live.py` calls this, we need to make that async too

**Alternative approach (simpler):**
- Keep `handle_tool_call` sync, but spawn async task for recording:
  ```python
  if self.memory:
      asyncio.create_task(self._record_intervention_async(...))
  ```

### Step 3.4: Update `voice/gemini_live.py` - Make Tool Handling Async
**File:** `voice/gemini_live.py`
**Method:** `_handle_tool_call`
**Change:** Make it async: `async def _handle_tool_call(self, name: str, args: dict) -> str`
**Update call site:** In `receive_responses()`, change: `result = await self._handle_tool_call(fc.name, fc.args)`

### Step 3.5: Update `voice/bot.py` - End-of-Session Reflection
**File:** `voice/bot.py`
**Method:** `stop()`
**Changes:**
1. Import: `from memory.reflection import generate_reflection`
2. Before disconnecting, if memory exists:
   ```python
   if self.memory:
       print("\n📝 Generating session reflection...")
       transcript = self.client.get_transcript()
       try:
           reflection = await generate_reflection(self.memory, transcript)
           print(f"💡 Insight: {reflection}")
       except Exception as e:
           print(f"Reflection generation failed: {e}")
   ```

---

## Phase 4: Dynamic Few-Shot Context Injection

### Step 4.1: Create Helper Function for Context Retrieval
**File:** `memory/redis_memory.py` (or new file `memory/context_builder.py`)
**Function:** `async def get_personalized_context(memory: RedisUserMemory, user_message: str) -> str`
**Implementation:**
1. Get embedding of user message: `query_embedding = await get_embedding(user_message)`
2. Find similar interventions: `similar = await memory.find_similar_interventions(query_embedding, k=3, successful_only=True)`
3. If no similar found, return empty string
4. Format examples:
   ```python
   examples = "\n".join([
       f"- When user said '{s['context']}', responding with '{s['intervention']}' → {s['outcome']} (similarity: {s['similarity']:.2f})"
       for s in similar
   ])
   return f"""
   ## Relevant past successes (use these as inspiration):
   {examples}
   """
   ```

### Step 4.2: Inject Context During Conversation
**File:** `voice/gemini_live.py`
**Method:** `send_text` or new method `_inject_memory_context`
**Approach:** Before sending user message, if memory exists:
1. Get personalized context: `context = await get_personalized_context(self.memory, text)`
2. If context exists, send it as a system message or prepend to user message
3. **Better:** Send as separate system message before user message

**Implementation:**
- Add method: `async def _inject_memory_context(self, user_message: str)`
  ```python
  if not self.memory:
      return
  
  from memory.context_builder import get_personalized_context
  context = await get_personalized_context(self.memory, user_message)
  if context:
      await self.send_text(f"[Memory context: {context}]")  # Or better: send as system message
  ```
- Call before sending user message in `send_text()`

**Alternative (cleaner):**
- Modify `_build_system_instruction` to include dynamic context, but this requires rebuilding instruction mid-conversation
- **Best:** Send memory context as a separate message before user message, or include in user message with special formatting

---

## Phase 5: Outcome Tracking Enhancement

### Step 5.1: Track Outcomes from User Responses
**File:** `voice/gemini_live.py` or `voice/bot.py`
**Purpose:** Detect when user completes tasks or gets re-engaged
**Approach:** Analyze user messages for completion signals

**Implementation:**
- Add method: `async def _analyze_outcome(self, user_message: str, last_tool_called: Optional[str]) -> Optional[str]`
- Patterns:
  - Completion: "done", "finished", "completed", "all done"
  - Progress: "step done", "next step", "moving on"
  - Re-engagement: "okay", "let's do it", "sounds good", "yes"
  - Distraction: "wait", "hold on", "what was I doing"
- Return outcome string or None

### Step 5.2: Update Intervention Recording with Better Context
**File:** `voice/agent_bridge.py`
**Enhancement:** Capture more context when recording interventions
- Store last N user messages as context
- Store current task state
- Store time since last check-in
- Include in `record_intervention` call

---

## Phase 6: Testing & Validation

### Step 6.1: Create Test Script for Memory System
**File:** `tests/test_memory_system.py`
**Tests:**
1. Test embedding generation
2. Test storing intervention
3. Test vector search retrieval
4. Test reflection generation
5. Test context building
6. Test end-to-end: store → search → use in prompt

### Step 6.2: Create Integration Test
**File:** `tests/test_voice_memory_integration.py`
**Tests:**
1. Start voice bot with memory
2. Send a message
3. Verify memory context is loaded
4. Call a tool
5. Verify intervention is recorded
6. Send similar message
7. Verify similar interventions are retrieved
8. End session
9. Verify reflection is generated

### Step 6.3: Manual Testing Checklist
- [ ] Redis connection works
- [ ] Embeddings are generated correctly (768 dimensions)
- [ ] Interventions are stored in Redis
- [ ] Vector search returns similar interventions
- [ ] Memory context appears in system prompt
- [ ] Tool calls record interventions
- [ ] End-of-session reflection generates insights
- [ ] Multiple sessions show improvement (memory context gets richer)

---

## Phase 7: Weave Custom Scorers (Optional Enhancement)

### Step 7.1: Implement Custom Scorers
**File:** `eval/scorers.py` (already exists, enhance it)
**Scorers to add:**
1. `InterventionEffectivenessScorer` - Measures if interventions led to task completion
2. `MemoryRetrievalScorer` - Measures if retrieved memories are relevant
3. `ReflectionQualityScorer` - Measures quality of generated reflections

### Step 7.2: Integrate Scorers with Memory System
- Score interventions when recorded
- Score memory retrievals
- Score reflections

---

## Phase 8: Error Handling & Edge Cases

### Step 8.1: Handle Redis Connection Failures
**Files:** All memory-related files
**Strategy:**
- Graceful degradation: If Redis unavailable, continue without memory
- Log warnings but don't crash
- Return empty results from memory queries

### Step 8.2: Handle Embedding Failures
**File:** `memory/embeddings.py`
**Strategy:**
- Retry logic (max 3 attempts)
- Fallback: Return empty list or raise with clear error
- Log errors

### Step 8.3: Handle Vector Search Failures
**File:** `memory/redis_memory.py`
**Strategy:**
- Try-catch around search queries
- Return empty list on error
- Log error details

---

## Phase 9: Performance Optimization

### Step 9.1: Cache Memory Context
**File:** `voice/gemini_live.py`
**Strategy:**
- Cache `get_context_for_prompt()` result for session duration
- Refresh cache after recording new intervention
- Or: Refresh every N minutes

### Step 9.2: Batch Embedding Requests
**File:** `memory/embeddings.py`
**Strategy:**
- If multiple embeddings needed, batch them
- Gemini API supports batch requests

---

## Execution Order Summary

1. **Setup** (Steps 1.1-1.3): Dependencies, module structure, env config
2. **Core Memory** (Steps 2.1-2.4): Embeddings, user profiles, Redis memory, reflection
3. **Integration** (Steps 3.1-3.5): Connect memory to voice session
4. **Dynamic Context** (Steps 4.1-4.2): Few-shot examples from memory
5. **Outcome Tracking** (Steps 5.1-5.2): Better outcome detection
6. **Testing** (Steps 6.1-6.3): Comprehensive tests
7. **Enhancements** (Steps 7-9): Scorers, error handling, optimization

---

## Success Criteria

After completing this plan, the system should:
- ✅ Store interventions in Redis with vector embeddings
- ✅ Retrieve similar past interventions using vector search
- ✅ Generate end-of-session reflections
- ✅ Inject memory context into system prompts
- ✅ Record intervention outcomes automatically
- ✅ Show improvement over multiple sessions (richer context)
- ✅ Handle errors gracefully (Redis unavailable, API failures)
- ✅ Pass all integration tests

---

## Notes

- **Redis Cloud Setup:** User needs to set up Redis Cloud instance separately (not in code)
- **Embedding Dimension:** Gemini text-embedding-004 uses 768 dimensions (verify in implementation)
- **TTL Strategy:** Interventions expire after 30 days, reflections after 90 days
- **Async Considerations:** Many operations are async - ensure proper async/await usage
- **Weave Integration:** All key operations should be decorated with `@weave.op()` for observability
