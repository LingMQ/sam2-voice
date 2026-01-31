# Implementation Plan: Voice Agent for Autism/ADHD Support

## Executive Summary

This plan outlines the implementation of a **self-improving** voice-based feedback loop system for WeaveHacks 3.

**Core Technologies (All Free/Credited):**
- **Gemini Live API** for real-time voice input/output (FREE tier)
- **Google ADK** for multi-agent orchestration (FREE - uses Gemini)
- **Redis** for vector-based memory & session state ($500 credit)
- **W&B Weave** for observability and self-improvement tracking (FREE tier)

**Self-Improvement Mechanism:**
- Redis vector search for semantic retrieval of past successful interventions
- End-of-session reflection generating insights
- Dynamic few-shot examples from similar past situations
- Memory decay via Redis TTL (old memories fade naturally)
- Weave traces feed directly into Redis memory → agent improves over time

**Cost: $0** (all within free tiers + Redis credits)

---

## Phase 1: Foundation Setup

### 1.1 Project Structure

```
sam2-voice/
├── agents/
│   ├── __init__.py
│   ├── main_agent.py           # Google ADK root agent (coordinator)
│   ├── feedback_loop_agent.py  # Micro-feedback timing & reinforcement
│   ├── aba_agent.py            # ABA therapy techniques
│   ├── task_agent.py           # Task breakdown & management
│   ├── emotional_agent.py      # Emotional regulation support
│   └── reflection_agent.py     # End-of-session reflection
├── voice/
│   ├── __init__.py
│   ├── gemini_live.py          # Gemini Live API voice handler
│   └── session.py              # Voice session management
├── memory/
│   ├── __init__.py
│   ├── redis_memory.py         # Redis-backed user memory with vector search
│   ├── embeddings.py           # Gemini embeddings for semantic search
│   └── reflection.py           # End-of-session reflection logic
├── observability/
│   ├── __init__.py
│   ├── weave_setup.py          # W&B Weave initialization
│   ├── scorers.py              # Custom evaluation scorers
│   └── improvement_metrics.py  # Self-improvement tracking
├── config/
│   └── prompts/                # System prompts for agents
│       ├── main_agent.txt
│       ├── feedback_loop.txt
│       ├── aba_agent.txt
│       └── task_agent.txt
├── tests/
│   ├── test_agents.py
│   ├── test_voice.py
│   └── test_memory.py
├── .env.example
├── pyproject.toml
└── README.md
```

### 1.2 Environment Setup

**Python Version:** 3.10+

**Package Manager:** `uv`

**Dependencies (pyproject.toml):**
```toml
[project]
name = "sam2-voice"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    # Voice (Gemini Live API - FREE)
    "google-genai",               # Gemini SDK with Live API

    # Agent Framework (FREE - uses Gemini)
    "google-adk",                 # Google Agent Development Kit

    # Memory (Redis - $500 credit)
    "redis[hiredis]",             # Redis client with fast C parser
    "numpy",                      # For vector operations

    # Observability (FREE tier)
    "weave",                      # W&B Weave

    # Utilities
    "python-dotenv",
    "asyncio",
]
```

**Required API Keys (.env):**
```ini
# Gemini (FREE tier)
GOOGLE_API_KEY=your_gemini_api_key

# Redis ($500 credit)
REDIS_URL=redis://default:password@your-redis-cloud-instance:6379

# Observability (FREE tier)
WANDB_API_KEY=your_wandb_key
```

---

## Phase 2: Voice with Gemini Live API

### 2.1 Architecture Overview

Gemini Live API handles everything - no separate STT/TTS needed:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SIMPLIFIED VOICE ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   User Microphone ──► WebSocket ──► Gemini Live API             │
│                                           │                      │
│                                           ▼                      │
│                                    Native Audio Processing       │
│                                    (STT + LLM + TTS built-in)    │
│                                           │                      │
│                                           ▼                      │
│   User Speaker ◄── WebSocket ◄── Audio Response                 │
│                                                                  │
│   Latency: ~600ms first token, sub-second full response         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Gemini Live API Voice Handler (voice/gemini_live.py)

```python
import asyncio
import os
from google import genai
from google.genai import types
import weave

weave.init("sam2-voice")

class GeminiVoiceSession:
    """Real-time voice conversation using Gemini Live API."""

    def __init__(self, user_id: str, system_prompt: str):
        self.user_id = user_id
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.system_prompt = system_prompt
        self.session = None
        self.transcript = []  # For reflection at end

    async def start(self):
        """Start a voice session."""
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore"  # Warm, supportive voice
                    )
                )
            ),
            system_instruction=self.system_prompt,
        )

        self.session = await self.client.aio.live.connect(
            model="gemini-2.0-flash-live-001",
            config=config
        )
        return self

    @weave.op()
    async def send_audio(self, audio_chunk: bytes):
        """Send audio to Gemini."""
        await self.session.send(
            input=types.LiveClientRealtimeInput(
                media_chunks=[
                    types.Blob(data=audio_chunk, mime_type="audio/pcm")
                ]
            )
        )

    @weave.op()
    async def receive_audio(self) -> bytes:
        """Receive audio response from Gemini."""
        async for response in self.session.receive():
            if response.data:
                return response.data
            if response.text:
                # Also capture text for transcript
                self.transcript.append({
                    "role": "assistant",
                    "content": response.text
                })
        return b""

    async def send_text(self, text: str):
        """Send text (for injecting context)."""
        self.transcript.append({"role": "user", "content": text})
        await self.session.send(input=text, end_of_turn=True)

    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()

    def get_transcript(self) -> list[dict]:
        """Get conversation transcript for reflection."""
        return self.transcript


async def create_voice_session(user_id: str, memory_context: str) -> GeminiVoiceSession:
    """Create a voice session with personalized context."""

    system_prompt = f"""You are a supportive voice assistant helping someone with ADHD/autism.

Your role:
- Provide micro-feedback loops to maintain engagement
- Break tasks into small, achievable steps
- Give frequent positive reinforcement
- Check in regularly (every 2-5 minutes)
- Use warm, encouraging language
- Keep responses SHORT (1-2 sentences for check-ins)

PERSONALIZED CONTEXT FOR THIS USER:
{memory_context}

Remember: You're having a real-time voice conversation. Be natural and conversational.
"""

    session = GeminiVoiceSession(user_id, system_prompt)
    await session.start()
    return session
```

### 2.3 Audio Handling for Browser/Client

```python
# voice/session.py
import asyncio
import pyaudio
import weave

class LocalAudioHandler:
    """Handle local microphone/speaker for testing."""

    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None

    def start_input(self):
        """Start microphone capture."""
        self.input_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )

    def start_output(self):
        """Start speaker output."""
        self.output_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,  # Gemini outputs at 24kHz
            output=True
        )

    @weave.op()
    def read_audio(self) -> bytes:
        """Read audio from microphone."""
        return self.input_stream.read(1024, exception_on_overflow=False)

    @weave.op()
    def play_audio(self, audio_data: bytes):
        """Play audio to speaker."""
        self.output_stream.write(audio_data)

    def close(self):
        if self.input_stream:
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.close()
        self.audio.terminate()
```

---

## Phase 3: Google ADK Multi-Agent System

### 3.1 Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Conversation Agent                   │
│               (Coordinator/Dispatcher Pattern)               │
└─────────────────────────┬───────────────────────────────────┘
                          │ LLM-driven delegation
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ FeedbackLoop  │ │   ABA Agent   │ │  Task Agent   │
│    Agent      │ │               │ │               │
│ (timing/micro-│ │ (reinforcement│ │ (breakdown,   │
│  interactions)│ │  prompting,   │ │  reminders)   │
│               │ │  shaping)     │ │               │
└───────────────┘ └───────────────┘ └───────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
                ┌───────────────────┐
                │  Progress Agent   │
                │ (tracks patterns, │
                │  adapts timing)   │
                └───────────────────┘
```

### 3.2 Root Agent Implementation (agents/main_agent.py)

```python
from google.adk import Agent
from google.adk.agents import SequentialAgent, ParallelAgent
import weave

# Initialize Weave for observability
weave.init("sam2-voice/agents")

# Define specialized agents
feedback_loop_agent = Agent(
    name="feedback_loop_agent",
    model="gemini-2.0-flash",
    description="Manages micro-interactions, timing, and reinforcement schedules. "
                "Tracks attention span and provides timely check-ins.",
    instruction=open("config/prompts/feedback_loop.txt").read(),
)

aba_agent = Agent(
    name="aba_agent",
    model="gemini-2.0-flash",
    description="Implements ABA therapy techniques: positive reinforcement, "
                "prompting, shaping, and task analysis.",
    instruction=open("config/prompts/aba_agent.txt").read(),
)

task_agent = Agent(
    name="task_agent",
    model="gemini-2.0-flash",
    description="Breaks down tasks into micro-steps, manages reminders, "
                "and tracks task completion.",
    instruction=open("config/prompts/task_agent.txt").read(),
    tools=[get_current_time, create_reminder],  # Custom function tools
)

emotional_agent = Agent(
    name="emotional_agent",
    model="gemini-2.0-flash",
    description="Provides emotional regulation support, calming techniques, "
                "and sensory overload detection.",
    instruction=open("config/prompts/emotional_agent.txt").read(),
)

# Root agent with sub-agents
root_agent = Agent(
    name="main_agent",
    model="gemini-2.0-flash",
    description="Main conversation coordinator for autism/ADHD support.",
    instruction="""You are a supportive voice assistant helping users with
    autism and ADHD. Your role is to:

    1. Understand user needs and route to appropriate specialized agents
    2. Maintain a warm, encouraging tone
    3. Provide micro-feedback loops to maintain engagement

    Available specialists:
    - feedback_loop_agent: For timing, check-ins, micro-reinforcements
    - aba_agent: For behavioral techniques and positive reinforcement
    - task_agent: For task breakdown and reminders
    - emotional_agent: For calming and emotional regulation

    Always prioritize the user's current emotional state and engagement level.
    """,
    sub_agents=[feedback_loop_agent, aba_agent, task_agent, emotional_agent],
)
```

### 3.3 Workflow Patterns to Use

**Sequential Pipeline (for task completion flow):**
```python
task_completion_pipeline = SequentialAgent(
    name="task_completion",
    sub_agents=[
        task_agent,           # Step 1: Break down task
        feedback_loop_agent,  # Step 2: Set up check-in schedule
        aba_agent,            # Step 3: Apply reinforcement
    ]
)
```

**Parallel Agent (for comprehensive assessment):**
```python
initial_assessment = ParallelAgent(
    name="initial_assessment",
    sub_agents=[
        emotional_state_checker,  # Check emotional state
        task_status_checker,      # Check current tasks
        engagement_analyzer,      # Analyze engagement level
    ]
)
```

---

## Phase 4: W&B Weave Observability

### 4.1 Setup (observability/weave_setup.py)

```python
import weave
from functools import wraps

def init_weave():
    """Initialize W&B Weave for the project."""
    weave.init("sam2-voice")

# Decorator for tracking agent interactions
@weave.op()
def track_agent_response(agent_name: str, user_input: str, response: str, metadata: dict):
    """Track agent responses for evaluation."""
    return {
        "agent": agent_name,
        "input": user_input,
        "output": response,
        "metadata": metadata,
    }
```

### 4.2 Custom Scorers (observability/scorers.py)

```python
import weave
from weave import Scorer

class FeedbackLoopEffectivenessScorer(Scorer):
    """Evaluates if feedback loops are appropriately timed and helpful."""

    @weave.op()
    def score(self, output: str, task_completed: bool, time_since_last_checkin: float):
        # Score based on whether the intervention helped task completion
        return {
            "intervention_helpful": task_completed,
            "timing_appropriate": 2 <= time_since_last_checkin <= 5,  # 2-5 min optimal
        }

class ABAReinforcementScorer(Scorer):
    """Evaluates quality of ABA reinforcement techniques."""

    @weave.op()
    def score(self, output: str, user_response: str):
        # Check for positive reinforcement patterns
        positive_indicators = ["great", "well done", "progress", "you did it"]
        has_reinforcement = any(ind in output.lower() for ind in positive_indicators)

        return {
            "contains_reinforcement": has_reinforcement,
            "user_engaged": len(user_response) > 10,
        }

class EngagementDurationScorer(Scorer):
    """Tracks how long users stay engaged with tasks."""

    @weave.op()
    def score(self, session_duration: float, distraction_count: int):
        return {
            "session_minutes": session_duration / 60,
            "distractions_per_minute": distraction_count / (session_duration / 60),
            "sustained_focus": distraction_count < 2 and session_duration > 300,
        }
```

### 4.3 Metrics to Track

| Metric | Purpose | Target |
|--------|---------|--------|
| Check-in frequency | Optimal timing per user | 2-5 minutes |
| Task completion rate | Effectiveness of micro-steps | > 80% |
| Session duration | Sustained engagement | 15+ minutes |
| Distraction recovery time | Speed of redirection | < 30 seconds |
| User sentiment | Emotional state tracking | Positive trend |

---

## Phase 5: Integration (Gemini Live + ADK + Redis Memory)

### 5.1 Main Application Loop

```python
# main.py
import asyncio
import os
from dotenv import load_dotenv
import weave

from voice.gemini_live import create_voice_session
from voice.session import LocalAudioHandler
from memory.redis_memory import RedisUserMemory
from memory.embeddings import get_embedding
from memory.reflection import generate_reflection

load_dotenv()
weave.init("sam2-voice")

async def run_session(user_id: str):
    """Run a complete voice session with self-improvement."""

    # 1. Load user memory from Redis
    memory = RedisUserMemory(
        user_id=user_id,
        redis_url=os.getenv("REDIS_URL")
    )

    # 2. Get personalized context
    memory_context = await memory.get_context_for_prompt()

    # 3. Create voice session with personalized prompt
    voice_session = await create_voice_session(user_id, memory_context)

    # 4. Start audio handling
    audio = LocalAudioHandler()
    audio.start_input()
    audio.start_output()

    print(f"🎙️ Session started for user {user_id}")
    print("Speak to your assistant... (Ctrl+C to end)")

    try:
        while True:
            # Read audio from mic
            audio_chunk = audio.read_audio()

            # Send to Gemini
            await voice_session.send_audio(audio_chunk)

            # Get response
            response_audio = await voice_session.receive_audio()

            if response_audio:
                # Play response
                audio.play_audio(response_audio)

    except KeyboardInterrupt:
        print("\n\n📝 Generating session reflection...")

        # 5. End of session - generate reflection
        transcript = voice_session.get_transcript()
        reflection = await generate_reflection(memory, transcript)
        print(f"💡 Insight: {reflection}")

    finally:
        audio.close()
        await voice_session.close()

if __name__ == "__main__":
    user_id = input("Enter user ID: ") or "demo_user"
    asyncio.run(run_session(user_id))
```

---

## Phase 6: Self-Improvement System (Redis + Vector Search)

This is the **core differentiator** for WeaveHacks 3's "Self-Improving Agents" theme.

### 6.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  SELF-IMPROVEMENT WITH REDIS VECTOR SEARCH              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   User says: "I can't focus on homework"                                │
│          │                                                              │
│          ▼                                                              │
│   ┌─────────────────────────────────────────────┐                      │
│   │         REDIS VECTOR SEARCH                  │                      │
│   │                                              │                      │
│   │  1. Embed query with Gemini (FREE)           │                      │
│   │  2. Search Redis for similar past contexts   │                      │
│   │  3. Return top-k successful interventions    │                      │
│   │                                              │                      │
│   │  Results:                                    │                      │
│   │  • "Quest mode worked for dishes" (0.92)     │                      │
│   │  • "2-min timer helped with reading" (0.87)  │                      │
│   └─────────────────────────────────────────────┘                      │
│          │                                                              │
│          ▼                                                              │
│   Agent uses examples ──► Personalized response                         │
│          │                                                              │
│          ▼                                                              │
│   ┌─────────────────────────────────────────────┐                      │
│   │         OUTCOME TRACKING                     │                      │
│   │                                              │                      │
│   │  Did user complete task? Re-engage?          │                      │
│   │  SUCCESS → Store in Redis with embedding     │                      │
│   │  FAILURE → Store separately for avoidance    │                      │
│   │  TTL: 30 days (memory naturally decays)      │                      │
│   └─────────────────────────────────────────────┘                      │
│          │                                                              │
│          ▼                                                              │
│   End of Session ──► Reflection Agent ──► Store insight in Redis        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Redis Memory with Vector Search (memory/redis_memory.py)

```python
import os
import json
import numpy as np
import redis
from redis.commands.search.field import TextField, VectorField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from datetime import datetime
from typing import Optional
import weave

class RedisUserMemory:
    """User memory backed by Redis with vector search for semantic retrieval."""

    def __init__(self, user_id: str, redis_url: str):
        self.user_id = user_id
        self.client = redis.from_url(redis_url, decode_responses=False)
        self.index_name = f"idx:user:{user_id}"
        self._ensure_index()

    def _ensure_index(self):
        """Create vector search index if it doesn't exist."""
        try:
            self.client.ft(self.index_name).info()
        except redis.ResponseError:
            schema = (
                TextField("$.intervention", as_name="intervention"),
                TextField("$.context", as_name="context"),
                TagField("$.outcome", as_name="outcome"),
                TextField("$.task", as_name="task"),
                NumericField("$.timestamp", as_name="timestamp"),
                VectorField(
                    "$.embedding",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": 768,  # Gemini text-embedding-004 dimension
                        "DISTANCE_METRIC": "COSINE"
                    },
                    as_name="embedding"
                )
            )
            self.client.ft(self.index_name).create_index(
                schema,
                definition=IndexDefinition(
                    prefix=[f"user:{self.user_id}:intervention:"],
                    index_type=IndexType.JSON
                )
            )

    @weave.op()
    async def record_intervention(
        self,
        intervention_text: str,
        context: str,
        task: str,
        outcome: str,
        embedding: list[float]
    ) -> str:
        """Store intervention with embedding for vector search."""
        from memory.embeddings import get_embedding

        key = f"user:{self.user_id}:intervention:{int(datetime.now().timestamp() * 1000)}"

        data = {
            "intervention": intervention_text,
            "context": context,
            "task": task,
            "outcome": outcome,
            "timestamp": datetime.now().timestamp(),
            "embedding": embedding
        }

        # Store with 30-day TTL (memory decay)
        self.client.json().set(key, "$", data)
        self.client.expire(key, 60 * 60 * 24 * 30)

        return key

    @weave.op()
    async def find_similar_interventions(
        self,
        query_embedding: list[float],
        k: int = 5,
        successful_only: bool = True
    ) -> list[dict]:
        """Find semantically similar past interventions using vector search."""

        query_vector = np.array(query_embedding, dtype=np.float32).tobytes()

        # Filter for successful outcomes only
        filter_str = "@outcome:{task_completed|re_engaged}" if successful_only else "*"

        q = Query(
            f"({filter_str})=>[KNN {k} @embedding $query_vector AS distance]"
        ).sort_by("distance").return_fields(
            "intervention", "context", "outcome", "task", "distance"
        ).dialect(2)

        try:
            results = self.client.ft(self.index_name).search(
                q,
                query_params={"query_vector": query_vector}
            )

            return [
                {
                    "intervention": doc.intervention,
                    "context": doc.context,
                    "outcome": doc.outcome,
                    "task": doc.task,
                    "similarity": 1 - float(doc.distance)
                }
                for doc in results.docs
            ]
        except Exception as e:
            print(f"Vector search error: {e}")
            return []

    @weave.op()
    def store_reflection(self, insight: str, session_summary: str):
        """Store session reflection."""
        key = f"user:{self.user_id}:reflection:{int(datetime.now().timestamp() * 1000)}"

        self.client.json().set(key, "$", {
            "insight": insight,
            "session_summary": session_summary[:500],
            "timestamp": datetime.now().isoformat()
        })
        self.client.expire(key, 60 * 60 * 24 * 90)  # 90 days for reflections

    @weave.op()
    def get_recent_reflections(self, limit: int = 5) -> list[str]:
        """Get recent session reflections."""
        pattern = f"user:{self.user_id}:reflection:*"
        keys = list(self.client.scan_iter(pattern, count=100))
        keys = sorted(keys, reverse=True)[:limit]

        reflections = []
        for key in keys:
            data = self.client.json().get(key)
            if data and "insight" in data:
                reflections.append(data["insight"])

        return reflections

    @weave.op()
    async def get_context_for_prompt(self) -> str:
        """Generate context string to include in agent prompts."""
        context_parts = []

        # Get recent reflections
        reflections = self.get_recent_reflections(3)
        if reflections:
            context_parts.append(
                "## Key insights from past sessions:\n" +
                "\n".join(f"- {r}" for r in reflections)
            )

        # Count successful interventions
        pattern = f"user:{self.user_id}:intervention:*"
        intervention_count = len(list(self.client.scan_iter(pattern, count=1000)))

        if intervention_count > 0:
            context_parts.append(
                f"## Memory status:\n- {intervention_count} past interventions stored"
            )

        return "\n\n".join(context_parts) if context_parts else "New user - no history yet."

    def get_stats(self) -> dict:
        """Get memory statistics for this user."""
        intervention_pattern = f"user:{self.user_id}:intervention:*"
        reflection_pattern = f"user:{self.user_id}:reflection:*"

        return {
            "user_id": self.user_id,
            "total_interventions": len(list(self.client.scan_iter(intervention_pattern, count=1000))),
            "total_reflections": len(list(self.client.scan_iter(reflection_pattern, count=1000)))
        }
```

### 6.3 Embeddings with Gemini (memory/embeddings.py)

```python
import os
from google import genai
import weave

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@weave.op()
async def get_embedding(text: str) -> list[float]:
    """Get embedding from Gemini (FREE tier)."""
    result = await client.aio.models.embed_content(
        model="text-embedding-004",
        contents=text
    )
    return result.embeddings[0].values
```

### 6.4 End-of-Session Reflection (memory/reflection.py)

```python
import os
from google import genai
import weave

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@weave.op()
async def generate_reflection(
    memory: "RedisUserMemory",
    transcript: list[dict]
) -> str:
    """Generate reflection at end of session."""

    # Format transcript
    transcript_str = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in transcript[-20:]  # Last 20 messages
    ])

    # Get previous insights for context
    previous_insights = memory.get_recent_reflections(3)
    previous_str = "\n".join(f"- {i}" for i in previous_insights) if previous_insights else "None yet"

    prompt = f"""Analyze this support session for someone with ADHD/autism.

SESSION TRANSCRIPT:
{transcript_str}

PREVIOUS INSIGHTS ABOUT THIS USER:
{previous_str}

Generate ONE brief insight (1-2 sentences) about what we learned from this session.
Focus on:
- What intervention styles worked or didn't work
- User's preferences or patterns you noticed
- What to do differently next time

Keep it specific and actionable."""

    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    insight = response.text.strip()

    # Store the reflection
    memory.store_reflection(
        insight=insight,
        session_summary=transcript_str
    )

    return insight
```

### 6.5 Memory-Aware Response Generation

```python
# Used during conversation to inject relevant examples
from memory.embeddings import get_embedding

@weave.op()
async def get_personalized_context(
    memory: RedisUserMemory,
    user_message: str
) -> str:
    """Get personalized context for the current user message."""

    # 1. Embed the current message
    query_embedding = await get_embedding(user_message)

    # 2. Find similar past successful interventions
    similar = await memory.find_similar_interventions(
        query_embedding=query_embedding,
        k=3,
        successful_only=True
    )

    # 3. Format as context
    if not similar:
        return ""

    examples = "\n".join([
        f"- When user said '{s['context']}', responding with '{s['intervention']}' → {s['outcome']}"
        for s in similar
    ])

    return f"""
## Relevant past successes (use these as inspiration):
{examples}
"""
```

---

## Phase 7: Implementation Milestones (Hackathon Timeline)

Given WeaveHacks 3 is Jan 31 - Feb 1 (24 hours), here's a compressed timeline:

### Hour 0-3: Foundation
- [ ] Set up project structure with `uv`
- [ ] Configure API keys (.env): GOOGLE_API_KEY, REDIS_URL, WANDB_API_KEY
- [ ] Set up Redis Cloud instance (use $500 credit)
- [ ] Test basic Gemini API connection

### Hour 3-6: Voice with Gemini Live API
- [ ] Implement GeminiVoiceSession class
- [ ] Test voice input/output with Gemini Live API
- [ ] Add Weave tracing to voice calls
- [ ] Test: speak → Gemini responds → hear response

### Hour 6-10: Redis Memory System
- [ ] Implement RedisUserMemory with vector search
- [ ] Implement embeddings with Gemini text-embedding-004
- [ ] Test storing and retrieving interventions
- [ ] Test vector similarity search

### Hour 10-14: Self-Improvement Integration ⭐
- [ ] Connect memory to voice session (personalized prompts)
- [ ] Implement outcome tracking
- [ ] Implement end-of-session reflection
- [ ] Test: simulate 2-3 sessions, verify memory improves responses

### Hour 14-18: Weave Observability + Polish
- [ ] Add comprehensive Weave tracing
- [ ] Implement improvement scorers
- [ ] Create Weave dashboard views
- [ ] Test full flow end-to-end

### Hour 18-22: Demo Prep
- [ ] Create compelling demo script
- [ ] Record demo video (for social media prize)
- [ ] Prepare Weave dashboard screenshots showing improvement
- [ ] Write README with architecture diagram

### Hour 22-24: Submission
- [ ] Final testing
- [ ] Clean up code
- [ ] Submit to Devpost/GitHub
- [ ] Prepare 2-minute pitch

---

## Key Technical Decisions

### 1. Voice Architecture
- **Approach:** Gemini Live API (native audio, no separate STT/TTS)
- **Benefit:** Simpler stack, FREE tier, ~600ms latency

### 2. LLM Provider
- **All Gemini:** Live API for voice, 2.0 Flash for agents, text-embedding-004 for vectors
- **Cost:** FREE tier for all

### 3. Memory/State
- **Redis Cloud** with vector search ($500 credit)
- **Features:** Semantic retrieval, TTL for memory decay, JSON storage

### 4. Observability
- **W&B Weave** for tracing and evaluation (FREE tier)

---

## Resources

### Official Documentation
- [Gemini Live API](https://ai.google.dev/gemini-api/docs/live-guide)
- [Google ADK Docs](https://google.github.io/adk-docs/)
- [W&B Weave Docs](https://docs.wandb.ai/weave)
- [Redis Vector Search](https://redis.io/docs/latest/develop/interact/search-and-query/query/vector-search/)

### Quick Commands
```bash
# Install dependencies
uv sync

# Run locally
uv run python main.py

# Run ADK dev UI (for testing agents)
adk web

# Check Redis connection
redis-cli -u $REDIS_URL ping
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Gemini Live API latency | Use 2.0 Flash (fastest); keep prompts short |
| Redis connection issues | Test early; have JSON file fallback ready |
| Vector search accuracy | Use good embedding model (text-embedding-004) |
| 15-min session limit | Implement session restart logic |
| Demo reliability | Pre-record backup demo video |

---

## Next Steps

1. **Set up Redis:** Create Redis Cloud instance with $500 credit
2. **Test Gemini Live:** Get basic voice working with Gemini
3. **Implement memory:** Build RedisUserMemory with vector search
4. **Connect everything:** Voice → Memory → Personalized responses
5. **Add Weave:** Trace everything, build improvement dashboard

---

## Why This Project Wins WeaveHacks 3

### Theme Alignment: Self-Improving Agents ✓
| Hackathon Criteria | Our Implementation |
|-------------------|-------------------|
| "Better memory systems" | Redis vector search for semantic memory retrieval |
| "Dynamic tool creation" | Agent learns which techniques work per user |
| "Autonomous improvement loops" | Weave traces → Redis memory → Better prompts → Weave traces |
| "Reinforcement learning" | Memory acts as implicit reward signal (success → stored in Redis) |

### Prize Targeting

**Grand Prize ($4k + $2k):** Novel architecture combining voice + self-improvement + Redis vector search

**Best Use of Weave ($1k):**
- Weave traces feed directly into Redis memory system
- Custom scorers measure improvement over time
- Dashboard shows before/after effectiveness
- Full observability of self-improvement loop

**Social Media Demo ($1k):** Voice demo is inherently engaging - user talks, agent learns

### Competitive Advantages

1. **Practical application:** Autism/ADHD support is meaningful and demo-able
2. **Clear improvement metric:** Task completion rate goes up over sessions
3. **Novel angle:** Most projects don't personalize per-user with vector search
4. **Full Weave integration:** Traces → Redis Memory → Evaluation loop
5. **Zero cost stack:** All FREE tiers + Redis credits = sustainable demo
6. **Redis vector search:** Semantic retrieval, not just keyword matching
