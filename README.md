# Sam2 Voice

**Voice assistant for ADHD/Autism support** using Gemini Live API with Weave observability, custom evaluation scorers, and self-improving memory system.

> Built for [WeaveHacks 3](https://www.notion.so/wandbai/WeaveHacks-3-participant-logistics-2f4e2f5c7ef380ca9a3cdebb8f8d0d24) 🚀

## ✨ Key Features

- **Real-time Voice Conversations** - Gemini Live API for natural speech interaction
- **ADHD/Autism-Optimized** - 13 specialized tools for task breakdown, emotional regulation, and micro-feedback
- **Weave Observability** - Full tracing of voice sessions, tool calls, and user interactions
- **Custom Evaluation Framework** - Scorers for brevity, supportiveness, tool usage, and response quality
- **Self-Improving Memory** - Redis-backed vector search learns from past successful interventions

## 🏆 Sponsor Technologies Used

| Sponsor | Technology | How We Use It |
|---------|------------|---------------|
| **Weights & Biases** | [Weave](https://wandb.ai/site/weave) | `@weave.op` tracing on all voice interactions, tool calls, and memory operations. Custom evaluation scorers (`brevity_scorer`, `supportiveness_scorer`, `tool_usage_scorer`, `response_quality_scorer`). Session tracking with `weave.attributes()`. `weave.Evaluation` for systematic testing. |
| **Google** | [Gemini Live API](https://ai.google.dev/gemini-api/docs/live) | Real-time bidirectional audio streaming for voice conversations. Native speech-to-text and text-to-speech. Tool calling for 13 ADHD/Autism support functions. |
| **Google** | [GenAI SDK](https://github.com/google/genai-python) | `google-genai` Python SDK for Gemini API access. Embedding generation via `models.embed_content()` for semantic memory search. |
| **Google** | [ADK](https://github.com/google/adk-python) | Agent Development Kit for multi-agent orchestration (agent definitions in `agents/`). |
| **Redis** | [Redis Stack](https://redis.io/docs/stack/) | Vector similarity search for finding relevant past interventions. User memory storage with 30-day TTL. Session state and user profiles. |

## 🔍 Weave Integration

### Observability (`@weave.op` Tracing)

Every critical function is traced with `@weave.op` for full observability:

```python
# voice/gemini_live.py - Core voice interactions
@weave.op
async def connect(self) -> bool: ...

@weave.op
async def send_text(self, text: str): ...

@weave.op
async def _handle_tool_call(self, name: str, args: dict) -> str: ...

# observability/session_tracker.py - Session metrics
@weave.op
def log_session_summary(self) -> dict: ...

@weave.op
def mark_intervention_successful(...) -> dict: ...
```

### Session Tracking

The `SessionTracker` logs rich metrics to Weave:
- Session duration and productivity
- Tool calls with arguments and results
- Task/step completion events
- Emotional intervention frequency
- Overall effectiveness scores

```python
# Automatic Weave attributes on every session
weave.attributes({
    "session_id": session_id,
    "user_id": user_id,
    "session_duration_minutes": duration,
    "session_productive": steps_completed > 0,
})
```

### Custom Evaluation Scorers

Four specialized scorers evaluate response quality:

| Scorer | Weight | Purpose |
|--------|--------|---------|
| `brevity_scorer` | 30% | Voice responses should be 1-2 sentences (10-30 words) |
| `supportiveness_scorer` | 40% | Detects positive vs. judgmental language |
| `tool_usage_scorer` | 30% | Validates correct tool selection for scenarios |
| `response_quality_scorer` | Combined | Weighted aggregate of all scorers |

```bash
# Run evaluation
python -m eval.run_eval                    # Full evaluation
python -m eval.run_eval --category task    # Specific category
```

### Evaluation Dataset

15 curated scenarios across 6 categories:
- **task_breakdown** - "Help me clean my room"
- **progress** - "I finished that step"
- **emotional** - "I'm feeling overwhelmed"
- **checkin** - "Remind me in a few minutes"
- **general** - "Thanks for helping"
- **onboarding** - "What can you help with?"

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  Microphone │───▶│  WebSocket  │───▶│  Audio Playback     │  │
│  │  (MediaAPI) │    │  /ws/audio  │◀───│  (Web Audio API)    │  │
│  └─────────────┘    └──────┬──────┘    └─────────────────────┘  │
└────────────────────────────┼────────────────────────────────────┘
                             │ Audio bytes
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Python Backend (FastAPI)                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              GeminiLiveClient (@weave.op traced)            ││
│  │  ┌─────────────────┐    ┌────────────────────────────────┐  ││
│  │  │ System Prompt   │    │      AgentToolBridge           │  ││
│  │  │ + Memory Context│    │  ┌──────────────────────────┐  │  ││
│  │  │ + Dynamic Context│   │  │ 13 Tools (all traced):   │  │  ││
│  │  │                 │    │  │ • create_microsteps      │  │  ││
│  │  │ ADHD/Autism     │    │  │ • mark_step_complete     │  │  ││
│  │  │ guidance        │    │  │ • start_breathing_exercise│ │  ││
│  │  └─────────────────┘    │  │ • reframe_thought        │  │  ││
│  │                         │  │ • grounding_exercise     │  │  ││
│  │                         │  │ • schedule_checkin       │  │  ││
│  │                         │  │ • ... (7 more)           │  │  ││
│  │                         │  └──────────────────────────┘  │  ││
│  │                         └────────────────────────────────┘  ││
│  │  ┌──────────────────────────────────────────────────────┐  ││
│  │  │         Redis Memory System (Vector Search)          │  ││
│  │  │  • Stores interventions with embeddings              │  ││
│  │  │  • Finds similar past interventions                 │  ││
│  │  │  • Injects context for self-improvement             │  ││
│  │  └──────────────────────────────────────────────────────┘  ││
│  │  ┌──────────────────────────────────────────────────────┐  ││
│  │  │         SessionTracker (Weave Observability)         │  ││
│  │  │  • Logs session summaries to Weave                   │  ││
│  │  │  • Tracks tool calls, completions, effectiveness     │  ││
│  │  │  • Enables feedback and intervention learning        │  ││
│  │  └──────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Gemini Live API                               │
│              (Real-time audio streaming + tool calling)          │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Install

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add:
# GOOGLE_API_KEY=your-key-from-aistudio.google.com
# REDIS_URL=redis://default:password@host:port  # Optional: for memory system
# WEAVE_PROJECT=your-weave-project              # For observability
```

### 3. Run

**Browser mode (recommended):**
```bash
uvicorn web.app:app --host 0.0.0.0 --port 8000
# Open http://localhost:8000
```

**Terminal mode:**
```bash
python main.py
```

**Run evaluation:**
```bash
python -m eval.run_eval
```

## 💬 Example Prompts

| Say this | Triggers | Category |
|----------|----------|----------|
| "Help me break down cleaning my room" | `create_microsteps` | task_breakdown |
| "I finished that step" | `mark_step_complete` | progress |
| "I'm feeling overwhelmed" | `start_breathing_exercise` | emotional |
| "Everything is too loud" | `sensory_check` | emotional |
| "Remind me in 5 minutes" | `schedule_checkin` | checkin |

## 🛠️ Available Tools (13)

| Category | Tools |
|----------|-------|
| **Task** | `create_microsteps`, `get_current_step`, `mark_step_complete`, `create_reminder`, `get_current_time` |
| **Emotional** | `start_breathing_exercise`, `sensory_check`, `grounding_exercise`, `suggest_break`, `reframe_thought` |
| **Feedback** | `schedule_checkin`, `get_time_since_last_checkin`, `log_micro_win` |

## 🧠 Self-Improving Memory System

The Redis-backed memory system learns from past interactions:

- **Vector Search**: Finds similar past interventions using semantic similarity
- **Dynamic Context Injection**: Automatically injects relevant past successes into conversations
- **Session Reflections**: Generates insights at end of each session
- **Self-Improvement**: Gets better over time by learning what works for each user

### Memory Features

- ✅ Stores interventions with embeddings (30-day TTL)
- ✅ Semantic similarity search for finding relevant past interactions
- ✅ Dynamic context injection for both audio and text interfaces
- ✅ End-of-session reflection generation
- ✅ User-specific memory and personalization
- ✅ Production-ready with health checks, logging, and error handling

## 📁 Project Structure

```
sam2-voice/
├── web/
│   ├── app.py                 # FastAPI backend + WebSocket
│   └── static/                # Browser UIs
├── voice/
│   ├── gemini_live.py         # Gemini Live API client (@weave.op traced)
│   ├── agent_bridge.py        # Tool call handler
│   └── bot.py                 # Terminal-based voice bot
├── eval/
│   ├── run_eval.py            # Weave evaluation runner
│   ├── scorers.py             # Custom evaluation scorers
│   ├── dataset.py             # Evaluation dataset
│   └── model.py               # Weave Model wrapper
├── observability/
│   ├── session_tracker.py     # Session metrics for Weave
│   └── scorers.py             # Additional scorers
├── memory/
│   ├── redis_memory.py        # Redis memory with vector search
│   ├── embeddings.py          # Embedding generation
│   ├── reflection.py          # Session reflection
│   └── health.py              # Health checks
├── agents/                    # ADK agent definitions (future work)
├── state/                     # Session and context management
├── config/prompts/            # System prompts
└── tests/                     # Test suite
```

## 🧪 Testing

```bash
# Test memory system
pytest tests/test_memory_system.py -v

# Test dynamic context injection
pytest tests/test_dynamic_context.py -v

# Health check
python scripts/health_check.py <user_id>

# Run Weave evaluation
python -m eval.run_eval
```

## 📊 View Results in Weave

After running the application or evaluation, view traces and metrics at: [**Weave Dashboard**](https://wandb.ai/vaibhavyashdixit-massachusetts-institute-of-technology/sam2-voice/weave/traces)

---

Built with ❤️ for neurodivergent users who deserve better support tools.
