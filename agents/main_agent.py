"""Main ADK coordinator agent with sub-agents."""

from pathlib import Path
from typing import Optional, List

from google.adk import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

from agents.feedback_loop_agent import feedback_loop_agent
from agents.aba_agent import aba_agent
from agents.task_agent import task_agent
from agents.emotional_agent import emotional_agent
from agents.progress_agent import progress_agent


def get_all_sub_agents() -> List[Agent]:
    """Get all registered sub-agents for the root agent.
    
    This centralizes agent registration and makes it easy to add/remove agents.
    Agents are listed in order of priority/precedence for routing decisions.
    
    Returns:
        List of all sub-agents to be registered with the root agent
    """
    return [
        feedback_loop_agent,  # Micro-feedback, timing, reinforcement
        aba_agent,            # ABA therapy techniques
        task_agent,           # Task breakdown and reminders
        emotional_agent,      # Emotional regulation support
        progress_agent,       # Progress tracking and adaptation
    ]


def _load_prompt(name: str) -> str:
    """Load a prompt from the config/prompts directory."""
    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / f"{name}.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


def create_root_agent() -> Agent:
    """Create the root coordinator agent with all sub-agents.

    The root agent routes requests to specialized agents:
    - feedback_loop_agent: Micro-feedback, timing, reinforcement
    - aba_agent: ABA therapy techniques
    - task_agent: Task breakdown and reminders
    - emotional_agent: Emotional regulation support
    - progress_agent: Progress tracking and adaptation

    Returns:
        Configured ADK Agent
    """
    instruction = _load_prompt("main_agent")

    return Agent(
        name="main_agent",
        model="gemini-2.0-flash",
        description="Main conversation coordinator for autism/ADHD support.",
        instruction=instruction or """You are a supportive voice assistant helping users with
autism and ADHD. Your role is to:

1. Understand user needs and route to appropriate specialized agents
2. Maintain a warm, encouraging tone
3. Provide micro-feedback loops to maintain engagement
4. Keep responses SHORT (1-2 sentences) for natural voice conversation

Available specialists:
- feedback_loop_agent: For timing, check-ins, micro-reinforcements
- aba_agent: For behavioral techniques and positive reinforcement
- task_agent: For task breakdown and reminders
- emotional_agent: For calming and emotional regulation
- progress_agent: For tracking patterns and adapting timing

Always prioritize the user's current emotional state and engagement level.
""",
        sub_agents=get_all_sub_agents(),
    )


# Create default instance
root_agent = create_root_agent()

# Session service for maintaining conversation context
_session_service = InMemorySessionService()
_runner: Optional[Runner] = None


async def run_agent(
    agent: Agent,
    user_input: str,
    session_id: Optional[str] = None,
    context: Optional[str] = None
) -> str:
    """Run the agent with user input and return the response.

    Args:
        agent: The ADK agent to run
        user_input: User's transcribed speech
        session_id: Optional session ID for context continuity
        context: Optional additional context to inject

    Returns:
        Agent's text response
    """
    global _runner

    # Create runner if needed
    if _runner is None:
        _runner = Runner(
            agent=agent,
            app_name="sam2-voice",
            session_service=_session_service,
        )

    # Use default session if not specified
    if session_id is None:
        session_id = "default-session"

    # Ensure session exists
    session = await _session_service.get_session(
        app_name="sam2-voice",
        user_id="user",
        session_id=session_id,
    )

    if session is None:
        session = await _session_service.create_session(
            app_name="sam2-voice",
            user_id="user",
            session_id=session_id,
        )

    # Prepare the message with optional context
    message = user_input
    if context:
        message = f"{user_input}\n\n---\nCONTEXT:\n{context}\n---"

    # Run the agent and collect response
    response_parts = []

    async for event in _runner.run_async(
        user_id="user",
        session_id=session_id,
        new_message=message,
    ):
        # Collect text responses from the agent
        if hasattr(event, 'text') and event.text:
            response_parts.append(event.text)
        elif hasattr(event, 'content') and event.content:
            for part in event.content:
                if hasattr(part, 'text') and part.text:
                    response_parts.append(part.text)

    return " ".join(response_parts) if response_parts else ""
