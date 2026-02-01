# Sam2 Voice

Voice assistant for ADHD/Autism support using Gemini Live API with tool calling and self-improving memory system.

## System Architecture

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
│  │                    GeminiLiveClient                         ││
│  │  ┌─────────────────┐    ┌────────────────────────────────┐  ││
│  │  │ System Prompt   │    │      AgentToolBridge           │  ││
│  │  │ + Memory Context│    │  ┌──────────────────────────┐  │  ││
│  │  │ + Dynamic Context│   │  │ 13 Tools:                │  │  ││
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
│  └─────────────────────────────────────────────────────────────┘│
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Gemini Live API                               │
│              (Real-time audio streaming + tool calling)          │
└─────────────────────────────────────────────────────────────────┘
```

## How It Works

The system uses **Gemini Live API** for real-time voice conversations:

1. **Audio Input**: Browser captures microphone audio and streams via WebSocket
2. **Gemini Live**: Processes audio, handles speech-to-text, generates responses, and text-to-speech
3. **Tool Calling**: Gemini Live calls tools (via `AgentToolBridge`) for task management, emotional support, etc.
4. **Memory System**: Redis stores past interventions and injects relevant context into conversations
5. **Audio Output**: Generated speech is streamed back to the browser

## Quick Start

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

## Example Prompts

| Say this | Triggers |
|----------|----------|
| "Help me break down cleaning my room" | `create_microsteps` |
| "I finished that step" | `mark_step_complete` |
| "I'm feeling overwhelmed" | `reframe_thought` |
| "I need a breathing exercise" | `start_breathing_exercise` |
| "Do a sensory check" | `sensory_check` |

## Project Structure

```
sam2-voice/
├── web/
│   ├── app.py                 # FastAPI backend + WebSocket
│   └── static/
│       ├── index.html         # Main UI
│       ├── browser_audio.html # Classic UI
│       └── calm_ui.html       # Calm UI variant
├── voice/
│   ├── gemini_live.py         # Gemini Live API client
│   ├── agent_bridge.py        # Tool call handler
│   ├── bot.py                 # Terminal-based voice bot
│   └── audio.py               # Audio capture/playback
├── agents/                    # ADK agent definitions (not currently used in voice flow)
│   ├── main_agent.py          # Root orchestrator
│   ├── task_agent.py          # Task breakdown
│   ├── emotional_agent.py     # Emotional support
│   ├── feedback_loop_agent.py # Check-ins & reinforcement
│   ├── aba_agent.py           # ABA techniques
│   └── progress_agent.py      # Progress tracking
├── memory/
│   ├── redis_memory.py        # Redis memory with vector search
│   ├── embeddings.py          # Embedding generation
│   ├── reflection.py          # Session reflection
│   ├── health.py              # Health checks
│   └── user_profile.py        # User profile management
├── state/
│   ├── session.py             # Session state management
│   └── context.py             # Conversation context
├── config/prompts/
│   └── main_agent.md          # System prompt for Gemini
└── tests/
    ├── test_memory_system.py  # Memory system tests
    ├── test_dynamic_context.py # Dynamic context tests
    └── ...
```

## Available Tools (13)

| Category | Tools |
|----------|-------|
| **Task** | `create_microsteps`, `get_current_step`, `mark_step_complete`, `create_reminder`, `get_current_time` |
| **Emotional** | `start_breathing_exercise`, `sensory_check`, `grounding_exercise`, `suggest_break`, `reframe_thought` |
| **Feedback** | `schedule_checkin`, `get_time_since_last_checkin`, `log_micro_win` |

## Self-Improving Memory System

The voice assistant includes a Redis-backed memory system that learns from past interactions:

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

### Testing

```bash
# Test memory system
pytest tests/test_memory_system.py -v

# Test dynamic context injection
pytest tests/test_dynamic_context.py -v

# Health check
python scripts/health_check.py <user_id>
```

## Future Work

The `agents/` directory contains ADK (Agent Development Kit) agent definitions that could be integrated for more sophisticated multi-agent orchestration in the future.
