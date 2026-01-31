"""Feedback loop agent for micro-reinforcements and check-ins."""

from pathlib import Path
from datetime import datetime
from typing import Optional

from google.adk import Agent
from google.adk.tools import tool


def _load_prompt(name: str) -> str:
    """Load a prompt from the config/prompts directory."""
    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / f"{name}.txt"
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


# Store for scheduled check-ins (in-memory for MVP)
_scheduled_checkins: dict[str, datetime] = {}


@tool
def schedule_checkin(minutes: int, session_id: str = "default") -> str:
    """Schedule a check-in with the user after specified minutes.

    Args:
        minutes: Number of minutes until check-in (typically 2-5)
        session_id: Session identifier

    Returns:
        Confirmation message
    """
    from datetime import timedelta
    checkin_time = datetime.now() + timedelta(minutes=minutes)
    _scheduled_checkins[session_id] = checkin_time
    return f"Check-in scheduled for {minutes} minutes from now"


@tool
def get_time_since_last_checkin(session_id: str = "default") -> str:
    """Get time since the last check-in.

    Args:
        session_id: Session identifier

    Returns:
        Time information
    """
    if session_id in _scheduled_checkins:
        last = _scheduled_checkins[session_id]
        elapsed = (datetime.now() - last).total_seconds() / 60
        return f"{elapsed:.1f} minutes since last check-in"
    return "No previous check-in recorded"


@tool
def log_micro_win(description: str, category: str = "general") -> str:
    """Log a micro-win for the user to track progress.

    Args:
        description: Brief description of what they accomplished
        category: Category of win (task, emotional, focus, etc.)

    Returns:
        Confirmation message
    """
    # In MVP, just acknowledge - could integrate with memory system later
    return f"Win logged ({category}): {description}"


# Load prompt from file
instruction = _load_prompt("feedback_loop")

feedback_loop_agent = Agent(
    name="feedback_loop_agent",
    model="gemini-2.0-flash",
    description="Manages micro-interactions, timing, and reinforcement schedules. "
                "Tracks attention span and provides timely check-ins.",
    instruction=instruction or """You manage micro-feedback loops for sustained engagement.

Your job:
- Provide small, frequent positive reinforcements
- Celebrate micro-wins enthusiastically but briefly
- Suggest optimal check-in intervals (2-5 minutes typically)
- Help recover from distractions with gentle redirection

Keep responses under 2 sentences. Be warm and genuine.
""",
    tools=[schedule_checkin, get_time_since_last_checkin, log_micro_win],
)
