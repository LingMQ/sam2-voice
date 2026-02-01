# Weave vs Redis Memory: Overlap Analysis & Integration Strategy

## Current State Analysis

### Weave/W&B Integration (Existing)
**Purpose**: Observability, evaluation, and quality scoring
**Location**: `eval/` module, `@weave.op()` decorators

**What Weave Does:**
1. **Tracing** (`@weave.op()` decorators)
   - Tracks function calls, inputs/outputs
   - Performance metrics (latency, duration)
   - Error tracking
   - Used in: `voice/bot.py`, `voice/gemini_live.py`, `memory/*.py`

2. **Evaluation** (`eval/` module)
   - Quality scorers: brevity, supportiveness, tool usage
   - Dataset-based evaluation
   - Model comparison
   - Scoring agent responses

3. **Observability**
   - Dashboard views in W&B
   - Trace visualization
   - Performance monitoring

### Redis Memory System (New)
**Purpose**: Persistent memory, semantic search, self-improvement
**Location**: `memory/` module

**What Redis Does:**
1. **Persistent Storage**
   - Stores interventions with embeddings
   - Stores session reflections
   - User profiles
   - TTL-based memory decay (30 days)

2. **Semantic Search**
   - Vector similarity search
   - Find similar past interventions
   - Context retrieval for prompts

3. **Self-Improvement Loop**
   - Learns what works per user
   - Injects past successes into prompts
   - Generates insights from sessions

## Overlap Analysis

### ✅ NO OVERLAP (Complementary)

| Feature | Weave | Redis | Notes |
|---------|-------|-------|-------|
| **Function Tracing** | ✅ Yes | ❌ No | Weave tracks execution, Redis doesn't |
| **Performance Metrics** | ✅ Yes | ❌ No | Weave tracks latency, Redis stores outcomes |
| **Quality Scoring** | ✅ Yes | ❌ No | Weave evaluates responses, Redis stores them |
| **Persistent Storage** | ❌ No | ✅ Yes | Redis stores long-term, Weave is ephemeral |
| **Semantic Search** | ❌ No | ✅ Yes | Redis does vector search, Weave doesn't |
| **User-Specific Memory** | ❌ No | ✅ Yes | Redis stores per-user, Weave is global |
| **Context Injection** | ❌ No | ✅ Yes | Redis provides context, Weave observes |

### ⚠️ POTENTIAL OVERLAP (Needs Clarification)

| Feature | Weave | Redis | Resolution |
|---------|-------|-------|------------|
| **Intervention Tracking** | Could track | ✅ Stores | **Weave observes, Redis stores** |
| **Outcome Tracking** | Could score | ✅ Stores | **Weave evaluates, Redis remembers** |
| **Session Data** | Could log | ✅ Stores | **Weave traces, Redis persists** |

## Recommended Separation of Concerns

### Weave: Observability & Evaluation Layer
**Role**: "What happened and how good was it?"

- ✅ Trace all operations (already doing)
- ✅ Score response quality (already doing)
- ✅ Track performance metrics
- ✅ Evaluate against datasets
- ✅ Dashboard visualization
- ❌ **Don't store** user-specific data long-term
- ❌ **Don't do** semantic search
- ❌ **Don't inject** context into prompts

### Redis: Memory & Self-Improvement Layer
**Role**: "What worked before and how can we use it?"

- ✅ Store interventions with outcomes
- ✅ Semantic search for similar situations
- ✅ Generate session reflections
- ✅ Inject context into prompts
- ✅ User-specific memory
- ❌ **Don't duplicate** Weave's tracing
- ❌ **Don't replace** Weave's evaluation
- ❌ **Don't store** full traces (too verbose)

## Integration Strategy: Make Them Work Together

### 1. Weave → Redis Pipeline (Recommended)

**Flow**: Weave evaluates → Redis stores successful patterns

```python
# In agent_bridge.py or similar
@weave.op()
async def record_intervention_with_evaluation(...):
    # 1. Record in Redis (already doing)
    key = await memory.record_intervention(...)
    
    # 2. Evaluate with Weave (if available)
    if weave_available:
        score = response_quality_scorer({
            "response": intervention_text,
            "tool_used": True,
            "tool_name": tool_name
        })
        
        # 3. Only store high-quality interventions in Redis
        if score["quality_score"] > 0.7:
            # Already stored, but we could add quality metadata
            await memory.record_intervention(...)
        else:
            # Store but mark as low quality
            await memory.record_intervention(..., metadata={"quality": score})
```

### 2. Redis → Weave Feedback Loop

**Flow**: Redis provides context → Agent uses it → Weave evaluates → Results inform Redis

```python
# In gemini_live.py
async def _load_memory_context(self):
    # Get context from Redis
    context = await self.memory.get_context_for_prompt()
    
    # Track in Weave that we're using memory
    if weave_available:
        weave.log({"memory_context_length": len(context)})
    
    return context
```

### 3. Shared Metadata (Optional)

Store Weave evaluation scores in Redis for filtering:

```python
# Enhanced intervention storage
await memory.record_intervention(
    ...,
    metadata={
        "weave_quality_score": quality_score,
        "weave_brevity": brevity_score,
        "weave_supportiveness": supportiveness_score
    }
)

# Then filter by quality in searches
similar = await memory.find_similar_interventions(
    ...,
    min_quality_score=0.7  # Only high-quality interventions
)
```

## Current Implementation Review

### ✅ Good Separation (No Changes Needed)

1. **Weave Tracing**: All `@weave.op()` decorators are appropriate
   - Tracks execution without storing data
   - Provides observability

2. **Redis Storage**: Stores interventions without duplicating traces
   - Focuses on outcomes, not full execution traces
   - Semantic search is unique to Redis

3. **Evaluation**: Weave scorers evaluate, Redis doesn't duplicate this

### ⚠️ Potential Improvements

1. **Add Quality Metadata to Redis**
   - Store Weave scores with interventions
   - Filter by quality in searches
   - Track which high-quality interventions work best

2. **Weave Dashboard for Memory Stats**
   - Log memory statistics to Weave
   - Track intervention counts over time
   - Monitor memory system health

3. **Evaluation → Memory Pipeline**
   - When Weave evaluates a response as high-quality
   - Automatically prioritize storing in Redis
   - Or mark low-quality interventions differently

## Recommended Changes

### 1. Enhance Redis Storage with Weave Scores

```python
# In memory/redis_memory.py
async def record_intervention(
    self,
    ...,
    weave_scores: Optional[dict] = None  # Add this
):
    data = {
        ...,
        "weave_scores": weave_scores  # Store evaluation scores
    }
```

### 2. Filter by Quality in Vector Search

```python
# In memory/redis_memory.py
async def find_similar_interventions(
    ...,
    min_quality_score: float = 0.0  # Filter by quality
):
    # Only return interventions above quality threshold
```

### 3. Log Memory Stats to Weave

```python
# In memory/redis_memory.py
def get_stats(self) -> Dict:
    stats = {...}
    
    # Log to Weave
    if weave_available:
        weave.log({
            "memory_interventions": stats["total_interventions"],
            "memory_reflections": stats["total_reflections"]
        })
    
    return stats
```

## Summary: Distinct & Complementary

### Weave (Observability)
- **What**: Observes, evaluates, scores
- **When**: Real-time during execution
- **Where**: W&B dashboard
- **Why**: Quality assurance, performance monitoring

### Redis (Memory)
- **What**: Stores, searches, remembers
- **When**: Persistent across sessions
- **Where**: Redis database
- **Why**: Self-improvement, personalization

### Integration Points
1. **Weave evaluates** → Redis stores high-quality patterns
2. **Redis provides context** → Agent uses it → Weave evaluates
3. **Weave scores** → Stored as metadata in Redis
4. **Redis stats** → Logged to Weave dashboard

## Action Items

1. ✅ **Keep current separation** - They're already distinct
2. ⚠️ **Add quality metadata** - Store Weave scores in Redis
3. ⚠️ **Filter by quality** - Only use high-quality past interventions
4. ⚠️ **Log memory stats** - Track Redis metrics in Weave
5. ⚠️ **Document integration** - Show how they work together

---

**Conclusion**: Weave and Redis are **complementary, not overlapping**. Weave observes and evaluates, Redis remembers and improves. They should work together, not duplicate each other.
