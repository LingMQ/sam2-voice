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
| `GEMINI_LIVE_MODEL` | Optional | Use if your account supports a specific Live model |
| `WANDB_API_KEY` | For observability | https://wandb.ai |

**Live model default:** `gemini-2.5-flash-native-audio-latest`.  
Override with `GEMINI_LIVE_MODEL` if your account has access to a different Live model.

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

### Optional: Web UI (Next.js)

The UI shows live status and transcript while the voice bot runs locally on
this machine (mic + speakers stay local).

Run the backend (WebSocket API):

```bash
pip install -e ".[web]"
uvicorn web.app:app --reload
```

Run the Next.js frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:3000 and click **Start session**.

If you want FastAPI to serve a static export of the UI at
http://127.0.0.1:8000, build the frontend:

```bash
cd frontend
npm run build
```

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

## Evaluation

The project includes a Weave-based evaluation system to measure response quality.

### Run Evaluation

```bash
# Run full evaluation (15 test cases)
python -m eval.run_eval

# Run specific category
python -m eval.run_eval --category emotional

# Use a different model
python -m eval.run_eval --model gemini-2.0-flash

# Custom evaluation name
python -m eval.run_eval --name my-eval-run
```

### Evaluation Categories

| Category | Description |
|----------|-------------|
| `task_breakdown` | Tests microstep creation for complex tasks |
| `progress` | Tests completion tracking and win logging |
| `emotional` | Tests breathing exercises and sensory support |
| `checkin` | Tests reminder scheduling |
| `general` | Tests general supportive responses |
| `onboarding` | Tests new user scenarios |

### Scorers

The evaluation measures three dimensions:

- **Brevity** (30%) - Responses should be 1-2 sentences for voice
- **Supportiveness** (40%) - Positive, non-judgmental language
- **Tool Usage** (30%) - Correct tool selection for scenarios

### View Results

Results are logged to Weights & Biases Weave:
https://wandb.ai/lingmiaojiayou-/hackathon

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
