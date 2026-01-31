# Voice Agent for Autism/ADHD Support with ABA Therapy Integration

## Core Concept: External Feedback Loop System

**The Problem:** Autism and ADHD stem from misaligned feedback loops (dopamine, hormonal, attention regulation). People with these conditions have dysregulated internal feedback mechanisms.

**The Solution:** Create an external feedback loop system that compensates for these dysregulations by providing:

- **Micro-interactions:** Small, frequent positive reinforcements (like how reels work - small dopamine hits)
- **Attention regulation:** Helps maintain focus through timely, well-paced interventions
- **Motivation support:** Provides external motivation when internal motivation systems are dysregulated
- **Adaptive timing:** Learns optimal timing for interventions based on user's attention span and engagement patterns

> This is a general-purpose helper for dysregulated feedback loops, not just specific scenarios.

---

## Architecture Overview

The system will use a multi-agent architecture with real-time voice capabilities, leveraging essential tools only:

| Tool | Role | Priority |
|------|------|----------|
| **Daily.co/Pipecat** | Real-time voice infrastructure and conversational AI framework | Essential |
| **Google ADK** | Agent orchestration and multi-agent coordination | Essential |
| **W&B Weave** | Observability, evaluation, and continuous improvement tracking (core to "improving concept") | Essential |
| **Redis** | Session state and caching (can use simpler alternatives initially) | Phase 2 |
| **Stagehand** | Browser automation (nice-to-have for external integrations) | Phase 2 |

### Why These Three Tools Are Essential

1. **Daily.co/Pipecat** — Provides the real-time voice infrastructure needed for natural conversation. This is the core interface requirement.
2. **Google ADK** — Enables sophisticated multi-agent orchestration for specialized ABA therapy agents. Critical for the multi-agent architecture.
3. **W&B Weave** — Core to the "improving concept" from WeaveHacks. Enables tracking what works, evaluating interventions, and continuously improving the agent's effectiveness over time.

---

## System Components

### 1. Voice Interface Layer (Daily.co/Pipecat)

- Real-time voice input/output using Daily's WebRTC infrastructure
- Audio streaming with Pipecat framework
- Low-latency conversation handling
- Support for both web and mobile platforms

### 2. Agent Orchestration (Google ADK)

- **Main Conversation Agent:** Handles user interactions and routes to specialized agents
- **Feedback Loop Agent:** Core agent that manages micro-interactions, timing, and reinforcement schedules
  - Tracks attention span and engagement patterns
  - Determines optimal check-in frequency
  - Provides micro-reinforcements at strategic intervals
- **ABA Therapy Agent:** Implements ABA techniques (reinforcement, prompting, shaping)
- **Task Management Agent:** Handles reminders, scheduling, and task breakdown into micro-steps
- **Emotional Support Agent:** Provides calming techniques and emotional regulation
- **Progress Tracking Agent:** Monitors user progress, learns optimal intervention timing, adapts feedback loops

### 3. Observability & Improvement (W&B Weave)

- Conversation quality evaluation
- ABA intervention effectiveness tracking
- User progress metrics
- Agent performance monitoring
- Continuous improvement feedback loops

---

## Primary Use Case: Sustained Task Completion with Micro-Feedback Loops

**Scenario:** User with ADHD needs to complete a task (e.g., homework, work project, cleaning room) but struggles with:

- Getting distracted quickly
- Losing motivation mid-task
- Difficulty maintaining sustained attention
- Internal feedback loops not providing enough motivagtion/reward

#### Use Case B: Transition Support *(Autism-friendly)*

- **Scenario:** Task switching is hard; unexpected schedule changes cause stress.
- **Agent does:** Gives a predictable transition script: "Now → Next → After" with buffers and clear steps.
- **Demo:** *"Meeting got moved"* → agent generates a 3-step transition plan + 2-minute regulation break + new next action.

#### Use Case C: Sensory Overload Prevention & Recovery *(Autism-friendly)*

- **Scenario:** User feels overloaded (noise/light/social demands) and can't continue.
- **Agent does:** Quick sensory check-in + suggests accommodations + returns to task in a low-demand way.
- **Demo:** *"I'm overwhelmed"* → agent: *"Noise, light, body tension?"* → *"Headphones + water + sit"* → *"Resume with 1-minute step."*

#### Use Case D: "Stuck" / Shutdown / Freeze Reset *(Autism + ADHD)*

- **Scenario:** User can't start; brain feels jammed.
- **Agent does:** Offers a 2-minute reset (breathing optional), then chooses the smallest possible next step.
- **Demo:** *"I can't start"* → *"Pick 1 of these 3 tiny steps"* → user picks → immediate start.

#### Use Case E: Morning Routine Builder *(Autism/ADHD)*

- **Scenario:** Routines fall apart; decision fatigue.
- **Agent does:** Creates a fixed routine with optional branches ("If low energy → do minimum version"), then runs it with gentle prompts.
- **Demo:** *"I want a morning routine"* → agent builds 3-step "minimum viable routine" → daily run-through.

#### Use Case F: Social Communication Clarifier *(Autism-friendly)*

- **Scenario:** Ambiguous messages cause anxiety; interpreting tone is hard.
- **Agent does:** Rewrites unclear messages into concrete options and drafts clarifying questions.
- **Demo:** User reads a vague text → agent: *"Possible meanings A/B/C"* + *"Reply options"* + *"Clarify politely."*

#### Use Case G: Anxiety Around Performance / Perfectionism *(ADHD overlap)*

- **Scenario:** User spirals into "must do perfectly" → avoids starting.
- **Agent does:** Reframes as "prototype mode," sets a 10-minute imperfect sprint, rewards completion.
- **Demo:** *"I'm avoiding this"* → *"10-minute messy draft sprint"* → *"Done is a win."*

#### Use Case H: Study / Deep Work Companion *(ADHD)*

- **Scenario:** Needs structure to study; frequent distractibility.
- **Agent does:** 25/5 style timer, but with micro-checks (*"Still on task?"*) and rewards (*"token earned"*).
- **Demo:** *"I need to study"* → agent starts focus session + mid-session check + reward.

#### Use Case I: Household Chore "Game Mode" *(Autism/ADHD)*

- **Scenario:** Chores feel infinite and unrewarding.
- **Agent does:** Turns chores into small quests + visible progress + reward at milestones.
- **Demo:** *"Do dishes"* → *"Quest: 10 items"* → micro praise → *"Boss fight: 2 pans."*

#### Use Case J: Caregiver / Coach Assist *(optional)*

- **Scenario:** Parent/partner wants to support without nagging.
- **Agent does:** Consent-first check-in scripts + low-pressure reinforcement suggestions.
- **Demo:** *"Help me support my partner"* → agent drafts a consent-based support message + plan.

### How the System Helps

1. **Task Breakdown** — Agent breaks task into small, achievable micro-steps (like reels - bite-sized chunks)
2. **Micro-Reinforcements** — After each micro-step completion, provides immediate positive feedback
   - *"Great! You finished step 1. That's progress!"*
   - *"You're doing amazing - step 2 complete!"*
3. **Attention Checks** — Periodically checks in (every 2-5 minutes) to maintain engagement
   - *"How's it going? Still on track?"*
   - *"Need a quick break or keep going?"*
4. **Adaptive Timing** — Uses W&B Weave to learn optimal check-in frequency for each user
   - Some users need check-ins every 2 minutes
   - Others can go 5 minutes before needing reinforcement
5. **Distraction Recovery** — When user gets distracted, provides gentle redirection
   - *"I noticed you paused - want to get back to step 3?"*
   - *"You were doing great! Let's finish this together."*

### Feedback Loop Mechanism

- **External dopamine hits:** Frequent small wins → motivation to continue
- **Attention anchoring:** Regular check-ins prevent mind wandering
- **Progress visibility:** User sees continuous progress, not just end goal
- **Adaptive learning:** System learns what timing/frequency works best for each user

> This demonstrates the core concept: external feedback loop compensating for dysregulated internal feedback loops.

---

## Core Features

### Phase 1: MVP Core Features

#### Voice Conversation Interface
- Natural voice interaction using Daily.co/Pipecat
- Multi-turn conversations with context retention
- Support for interruptions and corrections

#### Micro-Feedback Loop System (Core Feature)
- **Micro-interactions:** Small, frequent positive reinforcements (like reels - small dopamine hits)
- **Adaptive timing:** System learns optimal check-in frequency for each user (2-5 minute intervals)
- **Attention anchoring:** Regular check-ins prevent mind wandering and maintain engagement
- **Progress micro-visibility:** Continuous progress updates, not just end goal
- **Distraction recovery:** Gentle redirection when user gets off track

#### ABA Therapy Integration
- Positive reinforcement prompts (frequent and well-timed)
- Task breakdown into micro-steps (bite-sized chunks)
- Behavioral prompting and shaping techniques
- Progress acknowledgment and celebration (micro-celebrations)

#### Task Management
- Voice-based task creation and reminders
- Micro-step task breakdown (like reels - small, achievable chunks)
- Time management support with frequent check-ins

#### Emotional Regulation Support
- Calming techniques and breathing exercises
- Sensory overload detection and response
- Emotional state recognition and appropriate responses

#### Progress Tracking
- Daily/weekly progress summaries
- Goal achievement tracking
- Behavioral pattern recognition
- W&B Weave integration for analytics

#### Visibility Dashboard (For Caregivers/Therapists)
- Real-time progress monitoring
- Feedback loop effectiveness metrics
- Attention span patterns
- Intervention timing insights
- User engagement trends
- Customizable reports for therapy sessions

### Phase 2: Extensibility Features

#### Wearable Integration (Extended Goal - After Web App)
- **Meta Quest SDK:** Proof of concept for VR/AR integration
- Heart rate and stress level monitoring
- Always-on voice activation
- Context-aware interventions based on biometric data
- Enhanced feedback loop with physiological data

#### Multi-Device Synchronization
- State sync across devices (using in-memory storage or simple database)
- Seamless handoff between devices
- Consistent experience across platforms

#### Advanced ABA Techniques
- Personalized intervention strategies
- A/B testing of different approaches via W&B Weave
- Adaptive learning based on effectiveness

---

## Technical Stack

### Backend
- Python with Google ADK for agent orchestration
- Pipecat for voice agent framework
- FastAPI for REST API endpoints
- Daily.co for WebRTC infrastructure
- Simple state storage (in-memory or SQLite for MVP, Redis optional for scale)

### Frontend
- React/Next.js for web application
- React Native for mobile apps
- Daily.co SDK for voice/video integration
- Pipecat client for agent communication

### Infrastructure
- Daily.co cloud infrastructure for voice
- Google Cloud for ADK agent deployment
- W&B Weave for observability and continuous improvement

---

## Data Flow

```
User Voice Input
    ↓
Daily.co WebRTC → Pipecat Framework
    ↓
Google ADK Main Agent (orchestration)
    ↓
Feedback Loop Agent (monitors attention, timing, engagement)
    ↓
Specialized Agents (ABA, Task, Emotional Support)
    ↓
In-Memory State/Context Storage (tracks micro-steps, check-ins, timing)
    ↓
Response Generation (micro-reinforcements, check-ins, progress updates)
    ↓
Pipecat → Daily.co → User Voice Output
    ↓
W&B Weave (logs feedback loop effectiveness, learns optimal timing)
    ↓
Feedback Loop Agent adapts timing/frequency based on effectiveness
```

---

## Key Files Structure

```
project/
├── agents/
│   ├── main_agent.py           # Google ADK main orchestrator
│   ├── feedback_loop_agent.py  # Core: Micro-interactions, timing, reinforcement schedules
│   ├── aba_agent.py            # ABA therapy techniques
│   ├── task_agent.py           # Task management
│   ├── emotional_agent.py      # Emotional support
│   └── progress_agent.py       # Progress tracking
├── voice/
│   ├── pipecat_setup.py        # Pipecat configuration
│   ├── daily_integration.py    # Daily.co WebRTC setup
│   └── audio_handlers.py       # Audio processing
├── state/
│   ├── session_manager.py      # Session state management
│   └── context_store.py        # Conversation context (in-memory or simple DB)
├── observability/
│   ├── weave_integration.py    # W&B Weave logging
│   └── metrics_collector.py    # Performance metrics
├── frontend/
│   ├── web/                    # React/Next.js web app
│   └── mobile/                 # React Native app
├── api/
│   └── main.py                 # FastAPI server
└── config/
    ├── agent_config.yaml       # ADK agent configuration
    └── environment.yaml        # Environment variables
```

---

## Implementation Approach

1. **Set up infrastructure:** Daily.co account, Google ADK environment, W&B Weave integration
2. **Build voice pipeline:** Integrate Pipecat with Daily.co for real-time voice
3. **Create agent system:** Implement Google ADK agents with specialized roles
4. **Implement ABA logic:** Code ABA therapy techniques into the ABA agent
5. **Add state management:** Simple in-memory or database storage for sessions and context
6. **Integrate observability:** W&B Weave for tracking, evaluation, and continuous improvement
7. **Build frontend:** Web and mobile interfaces for voice interaction
8. **Testing & refinement:** Use W&B Weave to evaluate and improve agent effectiveness

---

## ABA Therapy Concepts to Implement

| Concept | Description |
|---------|-------------|
| **Positive Reinforcement** | Acknowledge and reward desired behaviors |
| **Task Analysis** | Break complex tasks into smaller, manageable steps |
| **Prompting** | Provide cues and guidance when needed |
| **Shaping** | Gradually build up to complex behaviors |
| **Generalization** | Help apply skills across different contexts |
| **Data Collection** | Track progress and behavioral patterns |

---

## Success Metrics (via W&B Weave)

### Feedback Loop Effectiveness
- Optimal check-in frequency for each user
- Attention span maintenance (time between distractions)
- Micro-reinforcement impact on motivation
- Task completion rates with vs. without feedback loops

### General Metrics
- Conversation quality scores
- User engagement metrics (sustained engagement duration)
- ABA intervention effectiveness
- Response time and latency
- User satisfaction indicators

### Learning Metrics
- How well the system adapts timing/frequency to individual needs
