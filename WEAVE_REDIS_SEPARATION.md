# Weave vs Redis: Clear Separation of Concerns

## ✅ Current Implementation Status

**Good News**: The implementations are already well-separated with minimal overlap!

## Distinct Purposes

### 🔍 Weave: Observability & Evaluation Layer
**Role**: "What happened and how good was it?"

**What Weave Does:**
- ✅ **Tracing**: `@weave.op()` decorators track function execution
- ✅ **Evaluation**: Scorers in `observability/scorers.py` evaluate intervention effectiveness
- ✅ **Metadata**: `weave.attributes()` tags traces for filtering in dashboard
- ✅ **Performance Monitoring**: Tracks latency, duration, errors
- ✅ **Dashboard Visualization**: W&B dashboard for viewing traces and metrics

**What Weave Does NOT Do:**
- ❌ **No persistent storage** - Traces are ephemeral, not stored long-term
- ❌ **No semantic search** - Cannot find similar past interventions
- ❌ **No context injection** - Does not modify agent prompts
- ❌ **No user-specific memory** - Global observability, not per-user

**Location**: `observability/`, `@weave.op()` decorators throughout codebase

---

### 💾 Redis: Memory & Self-Improvement Layer
**Role**: "What worked before and how can we use it?"

**What Redis Does:**
- ✅ **Persistent Storage**: Stores interventions with embeddings (30-day TTL)
- ✅ **Semantic Search**: Vector similarity search to find similar past interventions
- ✅ **Context Generation**: Creates context strings for agent prompts
- ✅ **Session Reflections**: Stores end-of-session insights (90-day TTL)
- ✅ **User Profiles**: Per-user memory and personalization
- ✅ **Memory Decay**: TTL-based automatic cleanup

**What Redis Does NOT Do:**
- ❌ **No evaluation/scoring** - Does not judge intervention quality
- ❌ **No tracing** - Does not track execution flow
- ❌ **No performance metrics** - Does not measure latency
- ❌ **No dashboard** - Data stored, not visualized directly

**Location**: `memory/` module

---

## Current Code Analysis

### ✅ Weave Implementation (Correct)
```python
# voice/agent_bridge.py
@weave.op  # ✅ Just tracing, not storing
def handle_tool_call(self, name: str, args: dict) -> str:
    weave.attributes({  # ✅ Just metadata for filtering
        "user_id": self.user_id,
        "tool_name": name,
    })
    # ... tool execution ...
    # ✅ Records to Redis separately (not Weave)
    self._record_intervention_in_background(...)
```

```python
# observability/scorers.py
class InterventionEffectivenessScorer(weave.Scorer):
    @weave.op
    def score(self, ...) -> dict:
        # ✅ Evaluates effectiveness, returns score
        # ✅ Does NOT store anything
        return {"effectiveness": 0.7, ...}
```

### ✅ Redis Implementation (Correct)
```python
# memory/redis_memory.py
@weave.op()  # ✅ Traced by Weave (observability)
async def record_intervention(self, ...):
    # ✅ Stores in Redis (persistent)
    # ✅ Does NOT evaluate quality
    # ✅ Does NOT duplicate Weave's scoring
    self.client.json().set(key, data)
```

```python
# memory/redis_memory.py
async def find_similar_interventions(self, ...):
    # ✅ Semantic search (unique to Redis)
    # ✅ Returns similar past interventions
    # ✅ Used for context injection
```

---

## Integration Points (How They Work Together)

### 1. Weave Traces Redis Operations
- Redis operations are decorated with `@weave.op()` for observability
- This is **tracing**, not storage overlap
- Weave sees what Redis does, but doesn't store the data

### 2. Redis Stores Outcomes (Not Traces)
- Redis stores intervention outcomes and embeddings
- Does NOT store full execution traces (too verbose)
- Focuses on "what worked" not "how it executed"

### 3. Future: Weave Scores → Redis Metadata (Optional)
- Could store Weave evaluation scores as metadata in Redis
- Would help filter high-quality interventions
- **Not implemented yet** - but would be complementary, not overlapping

---

## Verification Checklist

### ✅ Separation Verified
- [x] Weave only traces/evaluates, doesn't store long-term
- [x] Redis only stores/searches, doesn't evaluate
- [x] No duplicate functionality
- [x] Clear distinct purposes

### ✅ Integration Points (Complementary)
- [x] Redis operations traced by Weave (observability)
- [x] Redis stores outcomes, Weave evaluates them
- [x] No circular dependencies

### ⚠️ Optional Enhancements (Not Overlaps)
- [ ] Store Weave scores as metadata in Redis (would enhance, not duplicate)
- [ ] Use Weave scores to filter Redis searches (would enhance, not duplicate)
- [ ] Log Redis stats to Weave dashboard (would enhance, not duplicate)

---

## Summary

**Weave and Redis are complementary, not overlapping:**

| Aspect | Weave | Redis |
|--------|-------|-------|
| **Purpose** | Observability & Evaluation | Memory & Self-Improvement |
| **Data Lifecycle** | Ephemeral (traces) | Persistent (30-90 day TTL) |
| **User Scope** | Global (all users) | Per-user |
| **Primary Function** | "How good was it?" | "What worked before?" |
| **Storage** | No long-term storage | Persistent storage |
| **Search** | No search capability | Vector semantic search |
| **Context** | Observes context | Provides context |

**Conclusion**: ✅ **No overlap concerns** - They serve distinct purposes and work together harmoniously.

---

## Action Items

1. ✅ **Current separation is good** - No changes needed
2. ⚠️ **Optional**: Integrate Weave scores as Redis metadata (enhancement, not fix)
3. ⚠️ **Optional**: Use Weave scores to filter Redis searches (enhancement, not fix)
4. ✅ **Documentation**: This document clarifies the separation

---

**Last Updated**: February 2025  
**Status**: ✅ Separation verified, no overlap issues
