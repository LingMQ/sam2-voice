# Investigation Findings: Reflections & Check-ins

## 1. How Reflections Are Used

### Current Implementation

**Reflections are being used**, but the flow is:

1. **Generation**: At the end of each session, `generate_reflection()` is called in `voice/bot.py` (line 131)
   - Analyzes the last 20 messages of the transcript
   - Uses previous insights for context
   - Generates a 1-2 sentence insight about what worked/didn't work

2. **Storage**: Reflections are stored in Redis via `memory.store_reflection()`
   - Key format: `user:{user_id}:reflection:{timestamp_ms}`
   - TTL: 90 days
   - Contains: `insight`, `session_summary`, `timestamp`

3. **Retrieval & Usage**: Reflections are retrieved in `memory/redis_memory.py` in `get_context_for_prompt()` (line 244)
   - Gets the 3 most recent reflections
   - Formats them as: `## Key insights from past sessions:\n- {insight1}\n- {insight2}...`
   - Included in the system instruction when the session starts

4. **Injection**: The system instruction is built in `voice/gemini_live.py` in `_build_system_instruction()` (line 248)
   - Calls `await self._load_memory_context()` during `connect()` (line 481)
   - Memory context (including reflections) is added to the system instruction
   - This means reflections influence the agent's behavior throughout the session

### Status: ✅ Working
Reflections are being used correctly - they're included in the system prompt at session start, so the agent has access to past insights.

---

## 2. Check-in Timing Feature Issue

### Current Implementation

**The check-in feature is NOT working** - it schedules check-ins but never triggers them.

1. **Scheduling**: When `schedule_checkin` is called:
   - Stores a datetime in `_scheduled_checkins[session_id]` (in-memory dict)
   - Returns confirmation message
   - Gets logged as an intervention

2. **Missing Component**: There is **NO code** that:
   - Checks if the scheduled time has passed
   - Triggers a check-in message when time expires
   - Monitors `_scheduled_checkins` for expired check-ins

### The Problem

```python
# In agents/feedback_loop_agent.py and voice/agent_bridge.py
_scheduled_checkins[session_id] = datetime.now() + timedelta(minutes=minutes)
# ... but nothing ever checks if datetime.now() >= checkin_time
```

The check-in is scheduled and logged, but there's no background task or polling mechanism to actually execute it.

### Status: ❌ Broken
Check-ins are scheduled but never executed. The user is correct - they see it logged as an intervention but don't hear a response when the time expires.

---

## Recommendations

### For Reflections
- ✅ Current implementation is working
- Consider: Adding reflections to dynamic context (not just static system prompt) for more real-time influence

### For Check-ins
- ✅ **FIXED**: Implemented a background task that:
  1. Periodically checks `_scheduled_checkins` for expired check-ins (every 5 seconds)
  2. When a check-in time passes, sends a message to the user via `client.send_text()`
  3. Removes the check-in from the schedule after triggering to prevent duplicates
  4. Handles the case where the model is speaking (reschedules for 10 seconds later)
  
  **Implementation locations:**
  - `voice/bot.py`: Added `_checkin_monitor_loop()` method
  - `web/app.py`: Added `checkin_monitor()` function for browser-based sessions
  
  **How it works:**
  - Background task runs every 5 seconds
  - Checks if `datetime.now() >= checkin_time` for the session
  - Sends check-in message: "Check-in: How are you doing? Still on track?"
  - The Gemini model will respond naturally based on the conversation context
