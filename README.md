# sam2-voice

A self-improving voice agent for Autism/ADHD support, using Gemini Live API for real-time audio conversations.

## Quick Start

### 1. Install Dependencies

```bash
cd sam2-voice
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

**Note:** pyaudio requires PortAudio. Install it first:
- macOS: `brew install portaudio`
- Ubuntu: `sudo apt-get install portaudio19-dev`
- Windows: Usually works out of the box

### 2. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

| Key | Required | Get from |
|-----|----------|----------|
| `GOOGLE_API_KEY` | Yes | https://aistudio.google.com |
| `WANDB_API_KEY` | For observability | https://wandb.ai |

### 3. Run the Bot

```bash
python main.py
```

The bot uses your local microphone and speakers. Start speaking and the bot will respond in real-time.

**With a different voice:**
```bash
python main.py --voice Kore
```

Available voices: `Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`

### 4. Start Talking

The bot will start listening immediately. Try saying:
- "I need to clean my room" - Task breakdown
- "I'm feeling overwhelmed" - Emotional support
- "I finished that step" - Micro-reinforcement

Press `Ctrl+C` to stop.

## Command Line Options

```
python main.py [OPTIONS]

Options:
  --voice VOICE       Gemini voice to use (Puck, Charon, Kore, Fenrir, Aoede)
  --session-id ID     Session identifier for state management (default: "default")
  --user-id ID        User identifier (default: "user")
```

## Architecture

```
Microphone → Gemini Live API (audio-to-audio) → Speakers
                    ↓
            Built-in Tools:
            - schedule_checkin
            - create_microsteps
            - mark_step_complete
            - log_win
            - start_breathing_exercise
            - sensory_check
```

**Key Features:**
- Real-time audio streaming via Gemini Live API
- Native voice activity detection
- Built-in tool calling for task management
- No separate STT/TTS services needed

## ADK Agents (for extension)

The codebase includes Google ADK agents that can be integrated for more complex orchestration:
- `main_agent` - Coordinator that routes to specialists
- `feedback_loop_agent` - Micro-reinforcements and check-ins
- `aba_agent` - ABA therapy techniques
- `task_agent` - Task breakdown into micro-steps
- `emotional_agent` - Emotional regulation support
- `progress_agent` - Pattern tracking and adaptation
