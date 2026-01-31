# Implementation Plan: Voice Agent for Autism/ADHD Support

## Executive Summary

This plan outlines the implementation of a **self-improving** voice-based feedback loop system for WeaveHacks 3.

**Core Technologies:**
- **Pipecat** for real-time voice processing pipeline
- **Google ADK** for multi-agent orchestration
- **W&B Weave** for observability, evaluation, and self-improvement tracking
- **Daily.co** for WebRTC transport (optional - can run locally)

**Self-Improvement Mechanism:**
- Persistent memory bank storing successful interventions per user
- End-of-session reflection generating insights
- Dynamic few-shot examples from past successes
- Weave traces feed directly into memory → agent improves over time

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
│   └── progress_agent.py       # Progress tracking & adaptation
├── voice/
│   ├── __init__.py
│   ├── pipeline.py             # Pipecat pipeline configuration
│   ├── bot.py                  # Main voice bot entry point
│   └── handlers.py             # Audio event handlers
├── memory/                     # 🆕 Self-Improvement System
│   ├── __init__.py
│   ├── user_memory.py          # Per-user memory storage
│   ├── reflection.py           # End-of-session reflection
│   └── retrieval.py            # Dynamic few-shot retrieval
├── observability/
│   ├── __init__.py
│   ├── weave_setup.py          # W&B Weave initialization
│   ├── scorers.py              # Custom evaluation scorers
│   └── metrics.py              # Metrics collection
├── state/
│   ├── __init__.py
│   ├── session.py              # Session state management
│   └── context.py              # Conversation context storage
├── api/
│   ├── __init__.py
│   └── main.py                 # FastAPI server (optional)
├── frontend/
│   └── web/                    # React client (Phase 2)
├── config/
│   ├── agent_config.yaml       # Agent configuration
│   └── prompts/                # System prompts for agents
│       ├── main_agent.txt
│       ├── feedback_loop.txt
│       ├── aba_agent.txt
│       ├── task_agent.txt
│       └── emotional_agent.txt
├── data/                       # 🆕 Persistent storage
│   └── memories/               # User memory JSON files
├── tests/
│   ├── test_agents.py
│   ├── test_pipeline.py
│   └── test_memory.py          # 🆕 Memory system tests
├── .env.example
├── pyproject.toml
└── README.md
```

### 1.2 Environment Setup

**Python Version:** 3.10+

**Package Manager:** `uv` (recommended by Pipecat docs)

**Dependencies (pyproject.toml):**
```toml
[project]
name = "sam2-voice"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    # Voice Pipeline
    "pipecat-ai[daily,silero]",  # Pipecat with Daily transport + VAD

    # Speech Services (choose based on preference)
    "pipecat-ai[deepgram]",      # Deepgram STT
    "pipecat-ai[cartesia]",      # Cartesia TTS
    # OR use openai for both: "pipecat-ai[openai]"

    # Agent Framework
    "google-adk",                 # Google Agent Development Kit

    # Observability
    "weave",                      # W&B Weave

    # Utilities
    "python-dotenv",
    "pyyaml",
    "fastapi",
    "uvicorn",
]
```

**Required API Keys (.env):**
```ini
# Speech Services
DEEPGRAM_API_KEY=your_key
CARTESIA_API_KEY=your_key
# OR use OpenAI for STT/TTS
OPENAI_API_KEY=your_key

# Agent LLM
GOOGLE_API_KEY=your_gemini_key
# OR for Vertex AI:
# GOOGLE_CLOUD_PROJECT=your_project
# GOOGLE_CLOUD_LOCATION=us-central1

# Transport (optional - for cloud deployment)
DAILY_API_KEY=your_key

# Observability
WANDB_API_KEY=your_key
```

---

## Phase 2: Voice Pipeline Implementation

### 2.1 Pipecat Pipeline Architecture

The pipeline processes voice in this sequence:
```
User Audio → Transport → STT → LLM Agent → TTS → Transport → User
              (500-800ms round-trip)
```

### 2.2 Basic Voice Bot (voice/bot.py)

```python
import asyncio
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.transports.local.audio import LocalAudioTransport  # Local dev
# from pipecat.transports.services.daily import DailyTransport  # Cloud
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from dotenv import load_dotenv
import os

load_dotenv()

async def main():
    # Transport (local for development)
    transport = LocalAudioTransport(
        mic_enabled=True,
        speaker_enabled=True,
    )

    # Speech-to-Text
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    # Text-to-Speech
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="your_voice_id"
    )

    # LLM Context (will integrate with ADK agents)
    context = OpenAILLMContext(
        messages=[{"role": "system", "content": "You are a supportive assistant..."}]
    )

    # Build Pipeline
    pipeline = Pipeline([
        transport.input(),
        stt,
        # ADK Agent integration goes here
        tts,
        transport.output(),
    ])

    # Run
    task = PipelineTask(pipeline, PipelineParams())
    runner = PipelineRunner()
    await runner.run(task)

if __name__ == "__main__":
    asyncio.run(main())
```

### 2.3 Transport Options

**For Local Development:**
- Use `LocalAudioTransport` or `SmallWebRTCTransport` (peer-to-peer, no cloud)

**For Production:**
- Use `DailyTransport` with Daily.co WebRTC infrastructure
- Provides echo cancellation, noise reduction, reconnection handling

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

## Phase 5: Integration (Pipecat + ADK)

### 5.1 Bridge Implementation

The key challenge is connecting Pipecat's streaming pipeline with ADK's agent system:

```python
# voice/pipeline.py
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import TextFrame, TranscriptionFrame
from agents.main_agent import root_agent
import weave

class ADKAgentProcessor(FrameProcessor):
    """Bridge between Pipecat pipeline and Google ADK agents."""

    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.session_state = {}

    @weave.op()
    async def process_frame(self, frame):
        if isinstance(frame, TranscriptionFrame):
            # Got transcribed user speech
            user_text = frame.text

            # Run through ADK agent
            response = await self._run_agent(user_text)

            # Output as text frame for TTS
            yield TextFrame(text=response)
        else:
            yield frame

    async def _run_agent(self, user_input: str) -> str:
        """Run the ADK agent and get response."""
        # Use ADK's run method (async)
        result = await self.agent.run_async(
            user_input,
            state=self.session_state
        )
        return result.output
```

---

## Phase 6: Self-Improvement System (Memory + Reflection)

This is the **core differentiator** for WeaveHacks 3's "Self-Improving Agents" theme.

### 6.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SELF-IMPROVEMENT LOOP                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   User Interaction ──► Weave Traces ──► Outcome Tracking                │
│          │                                    │                         │
│          ▼                                    ▼                         │
│   ┌─────────────┐                    ┌──────────────────┐              │
│   │ Agent uses  │◄───────────────────│  Success? Add to │              │
│   │ past examples│                    │  Memory Bank     │              │
│   └─────────────┘                    └──────────────────┘              │
│          ▲                                    │                         │
│          │                                    ▼                         │
│   ┌─────────────────┐              ┌──────────────────┐                │
│   │ Dynamic Few-Shot │◄─────────────│ End-of-Session   │                │
│   │ Retrieval        │              │ Reflection       │                │
│   └─────────────────┘              └──────────────────┘                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 User Memory Implementation (memory/user_memory.py)

```python
import json
import weave
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

@dataclass
class Intervention:
    """A single intervention attempt."""
    intervention_text: str
    context: str  # What was happening when intervention occurred
    task: str
    outcome: str  # "task_completed", "re_engaged", "no_effect", "negative"
    timestamp: str
    metadata: dict

@dataclass
class Reflection:
    """End-of-session insight."""
    insight: str
    session_summary: str
    timestamp: str

class UserMemory(weave.Object):
    """Persistent memory for a single user - enables self-improvement."""

    user_id: str
    successful_interventions: list[dict]  # Interventions that worked
    failed_interventions: list[dict]      # Interventions that didn't work
    reflections: list[dict]               # Session insights
    preferences: dict                     # Learned user preferences

    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id
        self.successful_interventions = []
        self.failed_interventions = []
        self.reflections = []
        self.preferences = {
            "optimal_checkin_interval": 3.0,  # minutes, will adapt
            "preferred_tone": "encouraging",
            "responds_to_gamification": None,  # learned over time
            "needs_task_breakdown": None,
        }

    @weave.op()
    def record_intervention(
        self,
        intervention_text: str,
        context: str,
        task: str,
        outcome: str,
        metadata: Optional[dict] = None
    ):
        """Record an intervention and its outcome."""
        record = Intervention(
            intervention_text=intervention_text,
            context=context,
            task=task,
            outcome=outcome,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )

        if outcome in ["task_completed", "re_engaged"]:
            self.successful_interventions.append(asdict(record))
        else:
            self.failed_interventions.append(asdict(record))

        self._save()
        return record

    @weave.op()
    def add_reflection(self, insight: str, session_summary: str):
        """Add end-of-session reflection."""
        reflection = Reflection(
            insight=insight,
            session_summary=session_summary,
            timestamp=datetime.now().isoformat()
        )
        self.reflections.append(asdict(reflection))
        self._save()
        return reflection

    @weave.op()
    def get_relevant_examples(self, current_context: str, k: int = 3) -> list[dict]:
        """Retrieve most relevant successful interventions for current context."""
        if not self.successful_interventions:
            return []

        # Simple keyword matching (can upgrade to embeddings later)
        scored = []
        context_words = set(current_context.lower().split())

        for intervention in self.successful_interventions:
            intervention_words = set(intervention["context"].lower().split())
            overlap = len(context_words & intervention_words)
            scored.append((overlap, intervention))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:k]]

    @weave.op()
    def get_context_for_prompt(self) -> str:
        """Generate context string to include in agent prompts."""
        context_parts = []

        # Add recent successful interventions
        if self.successful_interventions:
            recent = self.successful_interventions[-5:]
            examples = "\n".join([
                f"- When '{i['context']}', saying '{i['intervention_text']}' → {i['outcome']}"
                for i in recent
            ])
            context_parts.append(f"## What works for this user:\n{examples}")

        # Add recent reflections
        if self.reflections:
            recent_insights = [r["insight"] for r in self.reflections[-3:]]
            context_parts.append(f"## Key insights:\n" + "\n".join(f"- {i}" for i in recent_insights))

        # Add learned preferences
        prefs = [f"- {k}: {v}" for k, v in self.preferences.items() if v is not None]
        if prefs:
            context_parts.append(f"## User preferences:\n" + "\n".join(prefs))

        return "\n\n".join(context_parts)

    def _save(self):
        """Persist memory to disk."""
        path = Path(f"data/memories/{self.user_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump({
                "user_id": self.user_id,
                "successful_interventions": self.successful_interventions,
                "failed_interventions": self.failed_interventions,
                "reflections": self.reflections,
                "preferences": self.preferences,
            }, f, indent=2)

    @classmethod
    def load(cls, user_id: str) -> "UserMemory":
        """Load memory from disk or create new."""
        path = Path(f"data/memories/{user_id}.json")
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            memory = cls(user_id)
            memory.successful_interventions = data.get("successful_interventions", [])
            memory.failed_interventions = data.get("failed_interventions", [])
            memory.reflections = data.get("reflections", [])
            memory.preferences = data.get("preferences", {})
            return memory
        return cls(user_id)
```

### 6.3 End-of-Session Reflection (memory/reflection.py)

```python
import weave
from google.adk import Agent

reflection_agent = Agent(
    name="reflection_agent",
    model="gemini-2.0-flash",
    instruction="""You are analyzing a support session for someone with ADHD/autism.

    Review the session and extract:
    1. What interventions worked well? (led to task completion or re-engagement)
    2. What didn't work? (user ignored, got frustrated, or disengaged)
    3. Any patterns you notice about this user's preferences?
    4. One key insight to remember for next time.

    Be specific and actionable. This will be used to improve future sessions.
    """
)

@weave.op()
async def generate_session_reflection(
    user_memory: "UserMemory",
    session_transcript: list[dict],
    outcomes: list[dict]
) -> str:
    """Generate reflection at end of session."""

    # Format session for analysis
    session_summary = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in session_transcript[-20:]  # Last 20 messages
    ])

    outcome_summary = "\n".join([
        f"- Intervention: '{o['intervention']}' → Outcome: {o['outcome']}"
        for o in outcomes
    ])

    prompt = f"""
    SESSION TRANSCRIPT:
    {session_summary}

    INTERVENTION OUTCOMES:
    {outcome_summary}

    PREVIOUS INSIGHTS ABOUT THIS USER:
    {user_memory.get_context_for_prompt()}

    Generate a brief insight (1-2 sentences) about what we learned from this session.
    """

    result = await reflection_agent.run_async(prompt)
    insight = result.output

    # Store the reflection
    user_memory.add_reflection(
        insight=insight,
        session_summary=session_summary[:500]  # Truncate for storage
    )

    return insight
```

### 6.4 Integrating Memory into Agents

```python
# agents/main_agent.py - Updated with memory integration

from memory.user_memory import UserMemory
import weave

class MemoryAwareAgent:
    """Wrapper that injects user memory into agent prompts."""

    def __init__(self, base_agent, user_id: str):
        self.base_agent = base_agent
        self.user_memory = UserMemory.load(user_id)
        self.session_outcomes = []

    @weave.op()
    async def run(self, user_input: str, context: dict) -> str:
        # Get personalized context from memory
        memory_context = self.user_memory.get_context_for_prompt()

        # Get relevant past examples
        examples = self.user_memory.get_relevant_examples(user_input)
        examples_str = "\n".join([
            f"Example: When user said '{e['context']}', "
            f"responding with '{e['intervention_text']}' worked well."
            for e in examples
        ])

        # Inject into prompt
        enhanced_prompt = f"""
        {user_input}

        ---
        PERSONALIZED CONTEXT FOR THIS USER:
        {memory_context}

        RELEVANT PAST SUCCESSES:
        {examples_str}
        ---
        """

        # Run agent
        response = await self.base_agent.run_async(enhanced_prompt)

        return response.output

    @weave.op()
    def record_outcome(self, intervention: str, context: str, task: str, outcome: str):
        """Record intervention outcome for learning."""
        self.user_memory.record_intervention(
            intervention_text=intervention,
            context=context,
            task=task,
            outcome=outcome
        )
        self.session_outcomes.append({
            "intervention": intervention,
            "outcome": outcome
        })

    async def end_session(self, transcript: list[dict]):
        """Generate reflection when session ends."""
        from memory.reflection import generate_session_reflection
        await generate_session_reflection(
            self.user_memory,
            transcript,
            self.session_outcomes
        )
```

### 6.5 Self-Improvement Metrics (for Weave Dashboard)

```python
# observability/improvement_metrics.py

import weave
from weave import Scorer

class ImprovementOverTimeScorer(Scorer):
    """Tracks if the agent is actually improving for each user."""

    @weave.op()
    def score(
        self,
        user_id: str,
        session_number: int,
        task_completion_rate: float,
        avg_interventions_needed: float
    ):
        return {
            "user_id": user_id,
            "session": session_number,
            "completion_rate": task_completion_rate,
            "interventions_per_task": avg_interventions_needed,
            # Lower interventions + higher completion = improvement
            "efficiency_score": task_completion_rate / max(avg_interventions_needed, 1)
        }

class MemoryUtilizationScorer(Scorer):
    """Tracks how effectively memory is being used."""

    @weave.op()
    def score(
        self,
        memory_examples_used: int,
        intervention_success_rate: float
    ):
        return {
            "examples_retrieved": memory_examples_used,
            "success_rate": intervention_success_rate,
            "memory_helping": memory_examples_used > 0 and intervention_success_rate > 0.6
        }
```

### 6.6 Demo Flow (for Hackathon Presentation)

```
Session 1 (New User):
├── Agent uses generic prompts
├── Tries gamification → User responds well ✓
├── Tries long explanation → User zones out ✗
├── End: Reflection stored
│   └── "User responds to gamification, keep messages short"

Session 2 (Same User):
├── Agent loads memory
├── Prompt includes: "This user responds to gamification"
├── Relevant example: "Quest mode worked for dishes"
├── Agent uses game language → Task completed faster ✓
├── End: More successes added to memory

Session 3+:
├── Memory grows with proven techniques
├── Agent becomes personalized expert for this user
└── Weave dashboard shows improvement over sessions
```

---

## Phase 7: Implementation Milestones (Hackathon Timeline)

Given WeaveHacks 3 is Jan 31 - Feb 1 (24 hours), here's a compressed timeline:

### Hour 0-3: Foundation
- [ ] Set up project structure with `uv`
- [ ] Configure API keys (.env)
- [ ] Get basic Pipecat voice loop working (speak → echo back)

### Hour 3-6: Voice + Basic Agent
- [ ] Integrate STT (Deepgram) and TTS (Cartesia/OpenAI)
- [ ] Create single ADK agent with supportive prompt
- [ ] Connect Pipecat pipeline with ADK agent
- [ ] Test: speak → agent responds → hear response

### Hour 6-10: Multi-Agent + Core Features
- [ ] Add specialized agents (feedback_loop, task, emotional)
- [ ] Implement task breakdown logic
- [ ] Add check-in timing system
- [ ] Test core use case: task completion with micro-feedback

### Hour 10-14: Self-Improvement System ⭐
- [ ] Implement UserMemory class
- [ ] Add intervention recording with outcomes
- [ ] Implement end-of-session reflection
- [ ] Inject memory context into prompts
- [ ] Test: simulate 2-3 sessions, verify memory improves responses

### Hour 14-18: Weave Integration + Polish
- [ ] Add Weave tracing throughout pipeline
- [ ] Implement improvement scorers
- [ ] Create evaluation dataset (sample sessions)
- [ ] Run evaluations, capture metrics

### Hour 18-22: Demo Prep
- [ ] Create compelling demo script
- [ ] Record demo video (for social media prize)
- [ ] Prepare Weave dashboard screenshots
- [ ] Write README with architecture diagram

### Hour 22-24: Submission
- [ ] Final testing
- [ ] Clean up code
- [ ] Submit to Devpost/GitHub
- [ ] Prepare 2-minute pitch

---

## Key Technical Decisions

### 1. Transport Choice
- **Development:** Use `LocalAudioTransport` or `SmallWebRTCTransport`
- **Production:** Use `DailyTransport` for reliability and features

### 2. LLM Provider
- **Primary:** Gemini 2.0 Flash via Google ADK (fast, cost-effective)
- **Alternative:** OpenAI GPT-4o-mini (if Gemini issues)

### 3. Speech Services
- **STT:** Deepgram Nova-2 (accurate, fast)
- **TTS:** Cartesia Sonic (natural voice, low latency)
- **Alternative:** OpenAI Whisper + TTS (single vendor)

### 4. State Management
- **MVP:** In-memory dictionary per session
- **Scale:** Redis or SQLite for persistence

---

## Resources

### Official Documentation
- [Pipecat Docs](https://docs.pipecat.ai)
- [Google ADK Docs](https://google.github.io/adk-docs/)
- [W&B Weave Docs](https://docs.wandb.ai/weave)
- [Daily.co Docs](https://docs.daily.co)

### Quick Commands
```bash
# Install dependencies
uv sync

# Run locally
uv run python voice/bot.py

# Run ADK dev UI
adk web

# Run with Weave tracing
WANDB_API_KEY=xxx uv run python voice/bot.py
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Latency issues | Use local STT/TTS first; optimize prompt length |
| Agent response quality | Extensive prompt engineering; Weave evaluations |
| Multi-agent coordination | Start with single agent; add complexity gradually |
| Cost management | Use Gemini Flash; implement response caching |
| User engagement drop | Implement distraction detection early |

---

## Next Steps

1. **Validate setup:** Get basic Pipecat voice loop working locally
2. **Test ADK:** Create simple agent and test with `adk web`
3. **Integrate:** Connect Pipecat pipeline with ADK agent
4. **Iterate:** Add agents one at a time, testing each

---

## Why This Project Wins WeaveHacks 3

### Theme Alignment: Self-Improving Agents ✓
| Hackathon Criteria | Our Implementation |
|-------------------|-------------------|
| "Better memory systems" | Per-user memory bank with successful interventions |
| "Dynamic tool creation" | Agent learns which techniques work per user |
| "Autonomous improvement loops" | Weave traces → Memory → Better prompts → Weave traces |
| "Reinforcement learning" | Memory acts as implicit reward signal (success → stored) |

### Prize Targeting

**Grand Prize ($4k + $2k):** Novel architecture combining voice + multi-agent + self-improvement

**Best Use of Weave ($1k):**
- Weave traces feed directly into memory system
- Custom scorers measure improvement over time
- Dashboard shows before/after effectiveness
- Full observability of self-improvement loop

**Social Media Demo ($1k):** Voice demo is inherently engaging - user talks, agent learns

### Competitive Advantages

1. **Practical application:** Autism/ADHD support is meaningful and demo-able
2. **Clear improvement metric:** Task completion rate goes up over sessions
3. **Novel angle:** Most projects don't personalize per-user
4. **Full Weave integration:** Traces → Memory → Evaluation loop
5. **Daily founder is a judge:** Using Pipecat (their framework) prominently
