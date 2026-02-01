# Sam2 Voice

Voice assistant for ADHD/Autism support using Gemini Live API with ADK agent orchestration.

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
│  │  │ (main_agent.txt)│    │  ┌──────────────────────────┐  │  ││
│  │  │                 │    │  │ 13 Tools:                │  │  ││
│  │  │ ADHD/Autism     │    │  │ • create_microsteps      │  │  ││
│  │  │ guidance        │    │  │ • mark_step_complete     │  │  ││
│  │  └─────────────────┘    │  │ • start_breathing_exercise│ │  ││
│  │                         │  │ • reframe_thought        │  │  ││
│  │                         │  │ • grounding_exercise     │  │  ││
│  │                         │  │ • schedule_checkin       │  │  ││
│  │                         │  │ • ... (7 more)           │  │  ││
│  │                         │  └──────────────────────────┘  │  ││
│  │                         └────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Gemini Live API                               │
│              (Real-time audio streaming)                         │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add: GOOGLE_API_KEY=your-key-from-aistudio.google.com
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
│       └── browser_audio.html # Browser UI
├── voice/
│   ├── gemini_live.py         # Gemini Live API client
│   ├── agent_bridge.py        # Routes tools to ADK implementations
│   └── bot.py                 # Terminal-based voice bot
├── agents/
│   ├── main_agent.py          # Root orchestrator
│   ├── task_agent.py          # Task breakdown
│   ├── emotional_agent.py     # Emotional support
│   ├── feedback_loop_agent.py # Check-ins & reinforcement
│   └── ...
└── config/prompts/
    └── main_agent.txt         # System prompt for Gemini
```

## Available Tools (13)

| Category | Tools |
|----------|-------|
| **Task** | `create_microsteps`, `get_current_step`, `mark_step_complete`, `create_reminder`, `get_current_time` |
| **Emotional** | `start_breathing_exercise`, `sensory_check`, `grounding_exercise`, `suggest_break`, `reframe_thought` |
| **Feedback** | `schedule_checkin`, `get_time_since_last_checkin`, `log_micro_win` |
