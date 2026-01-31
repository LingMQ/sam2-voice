"""Task breakdown and management agent."""

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


# In-memory task storage for MVP
_current_tasks: dict[str, dict] = {}


@tool
def create_microsteps(task: str, count: int = 3, session_id: str = "default") -> str:
    """Break a task into micro-steps and store them.

    Args:
        task: The task to break down
        count: Number of micro-steps to create (default 3)
        session_id: Session identifier

    Returns:
        Confirmation of micro-steps created
    """
    _current_tasks[session_id] = {
        "task": task,
        "total_steps": count,
        "current_step": 0,
        "started_at": datetime.now().isoformat(),
    }
    return f"Created {count} micro-steps for: {task}"


@tool
def get_current_step(session_id: str = "default") -> str:
    """Get the current step the user should work on.

    Args:
        session_id: Session identifier

    Returns:
        Current step information
    """
    if session_id not in _current_tasks:
        return "No active task"

    task_info = _current_tasks[session_id]
    step = task_info["current_step"] + 1
    total = task_info["total_steps"]

    if step > total:
        return f"All {total} steps complete for: {task_info['task']}"

    return f"Step {step} of {total} for: {task_info['task']}"


@tool
def mark_step_complete(session_id: str = "default") -> str:
    """Mark the current micro-step as complete.

    Args:
        session_id: Session identifier

    Returns:
        Confirmation and next step info
    """
    if session_id not in _current_tasks:
        return "No active task to update"

    task_info = _current_tasks[session_id]
    task_info["current_step"] += 1
    step = task_info["current_step"]
    total = task_info["total_steps"]

    if step >= total:
        task_name = task_info["task"]
        del _current_tasks[session_id]
        return f"All done! Completed all {total} steps for: {task_name}"

    return f"Step {step} complete! {total - step} steps remaining."


@tool
def get_current_time() -> str:
    """Get the current time for time-awareness.

    Returns:
        Current time string
    """
    return datetime.now().strftime("%I:%M %p")


@tool
def create_reminder(task: str, minutes: int) -> str:
    """Create a reminder for a task.

    Args:
        task: What to remind about
        minutes: Minutes until reminder

    Returns:
        Confirmation message
    """
    # In MVP, just acknowledge - actual reminder would need timer integration
    return f"Reminder set: '{task}' in {minutes} minutes"


# Load prompt from file
instruction = _load_prompt("task_agent")

task_agent = Agent(
    name="task_agent",
    model="gemini-2.0-flash",
    description="Breaks down tasks into micro-steps, manages reminders, "
                "and tracks task completion.",
    instruction=instruction or """You break tasks into tiny, achievable micro-steps.

Key principles:
- Each step should take 2-5 minutes MAX
- Steps must be CONCRETE and ACTIONABLE
- Start with the SMALLEST possible first step
- One step at a time - don't overwhelm with lists

Example:
User: "I need to clean my room"
You: "Step 1: Pick up just 3 items from the floor. Tell me when done."

Keep responses under 2 sentences.
""",
    tools=[create_microsteps, get_current_step, mark_step_complete, get_current_time, create_reminder],
)
