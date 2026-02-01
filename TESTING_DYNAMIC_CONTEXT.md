# Testing Dynamic Context Injection

## Overview

Dynamic context injection automatically finds similar past interventions and injects them as context to improve agent responses. This works for both text and audio interfaces.

## Quick Test

### 1. Run the Test Script

```bash
# Make sure you have REDIS_URL and GOOGLE_API_KEY in .env
python test_dynamic_context_audio.py
```

This will:
- Store test interventions in Redis
- Test context inference from conversation patterns
- Verify context format and quality
- Test edge cases

### 2. Test with Web Interface

```bash
# Start the web server
uvicorn web.app:app --reload

# Open browser
open http://localhost:8000
```

**What to look for:**
1. Start a conversation
2. Say something like "I can't focus on my homework"
3. After the assistant responds, check console logs for:
   - `📚 Injected dynamic context based on conversation pattern`
4. The next response should be influenced by similar past interventions

## How It Works

### For Audio Interface

1. **User speaks** → Audio sent to Gemini Live API
2. **Assistant responds** → Response triggers context preparation
3. **System analyzes** → Infers user intent from conversation patterns
4. **Context found** → Similar past interventions retrieved
5. **Context injected** → Sent as formatted message to influence next response

### For Text Interface

1. **User sends text** → `send_text()` called
2. **Dynamic context loaded** → Based on exact user message
3. **Context injected** → Prepended to user message
4. **Model processes** → Uses context to provide better response

## Test Scenarios

### Scenario 1: Focus Issues

**User says (audio):** "I can't focus on my homework"

**Expected:**
- System finds similar past intervention: "I can't focus" → create_microsteps worked
- Context injected: Example of breaking tasks into steps
- Agent response: Uses similar approach (suggests breaking into steps)

### Scenario 2: Overwhelm

**User says (audio):** "I'm feeling overwhelmed"

**Expected:**
- System finds: Past intervention where breaking down helped
- Context injected: Example of successful task breakdown
- Agent response: Suggests breaking down the task

### Scenario 3: No Similar Context

**User says:** "What's the weather like?"

**Expected:**
- No similar interventions found
- No context injected (graceful degradation)
- Normal response (no memory influence)

## Verification

### Check Console Logs

Look for these messages:
- `📚 Prepared dynamic context for next turn (inferred from conversation)`
- `📚 Injected dynamic context based on conversation pattern`
- `✅ Injected dynamic context for next interaction`

### Check Redis

```bash
# View stored interventions
python scripts/debug_memory.py <user_id> interventions

# Check memory stats
python scripts/debug_memory.py <user_id> summary
```

### Check Memory Stats API

```bash
curl http://localhost:8000/api/memory/stats
```

## Troubleshooting

### Context Not Being Injected

1. **Check Redis connection:**
   ```bash
   python scripts/health_check.py <user_id>
   ```

2. **Verify interventions exist:**
   ```bash
   python scripts/debug_memory.py <user_id> interventions
   ```

3. **Check similarity threshold:**
   - Only interventions with similarity > 0.7 are included
   - If no matches, try storing more diverse interventions

### Context Format Issues

1. **Check console for errors:**
   - Look for "Warning: Could not inject dynamic context"

2. **Verify embedding generation:**
   ```bash
   python -c "import asyncio; from memory.embeddings import get_embedding; print(len(asyncio.run(get_embedding('test'))))"
   ```

### Performance Issues

1. **Context injection is async** - shouldn't block
2. **Caching** - Same message won't trigger redundant searches
3. **Quality filtering** - Only high-quality matches are used

## Expected Behavior

### ✅ Working Correctly

- Context injected after assistant responses (audio)
- Context injected with user messages (text)
- Only high-quality matches (similarity > 0.7)
- Only successful interventions used as examples
- Graceful degradation if no context found

### ❌ Issues to Watch For

- Context injected too frequently (should be after responses)
- Context format confusing the model
- Performance degradation
- Missing context when it should be found

## Manual Testing Checklist

- [ ] Test interventions stored in Redis
- [ ] Test context inference from conversation patterns
- [ ] Test context injection after assistant response
- [ ] Test with web interface (audio)
- [ ] Test with text interface
- [ ] Verify context improves responses
- [ ] Test edge cases (no context, unrelated queries)
- [ ] Check console logs for injection messages
- [ ] Verify no performance issues

## Next Steps

After testing:
1. Monitor real conversations for context injection
2. Adjust similarity threshold if needed (currently 0.7)
3. Fine-tune pattern detection keywords
4. Add more diverse test interventions
5. Measure improvement in response quality
