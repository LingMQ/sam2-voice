"""Emotional regulation and support agent."""

from pathlib import Path
from google.adk import Agent
from google.adk.tools import FunctionTool


def _load_prompt(name: str) -> str:
    """Load a prompt from the config/prompts directory."""
    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / f"{name}.txt"
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


def start_breathing_exercise(breaths: int = 3) -> str:
    """Start a quick breathing exercise.

    Args:
        breaths: Number of breaths (default 3 for quick reset)

    Returns:
        Instruction to guide the exercise
    """
    if breaths <= 3:
        return "Quick reset: Breathe in slowly... hold... breathe out. Let's do that together."
    return f"Let's take {breaths} slow breaths together. I'll count with you."


def sensory_check() -> str:
    """Prompt a quick sensory environment check.

    Returns:
        Prompts for sensory assessment
    """
    return "Quick sensory check - is it the noise, the light, or something in your body that's bothering you?"


def grounding_exercise(technique: str = "5-4-3-2-1") -> str:
    """Start a grounding exercise.

    Args:
        technique: Type of grounding (5-4-3-2-1, body scan, or simple)

    Returns:
        Grounding instruction
    """
    techniques = {
        "5-4-3-2-1": "Name 5 things you can see right now.",
        "body_scan": "Notice your feet on the floor. Feel your hands.",
        "simple": "What's one thing you can see right in front of you?",
    }
    return techniques.get(technique, techniques["simple"])


def suggest_break(duration_minutes: int = 5) -> str:
    """Suggest a structured break.

    Args:
        duration_minutes: Suggested break duration

    Returns:
        Break suggestion
    """
    if duration_minutes <= 2:
        return "Quick 2-minute reset - step away, stretch, come back fresh."
    elif duration_minutes <= 5:
        return f"Take {duration_minutes} minutes. Get some water, move around a bit."
    else:
        return f"Let's take a proper {duration_minutes}-minute break. Set a timer and really step away."


def reframe_thought(thought_type: str) -> str:
    """Provide a cognitive reframe for common negative thought patterns.

    Args:
        thought_type: Type of thought (perfectionism, catastrophizing, rsd, overwhelm)

    Returns:
        Reframe suggestion
    """
    reframes = {
        "perfectionism": "This is prototype mode - it just needs to exist, not be perfect.",
        "catastrophizing": "What do we actually know for sure vs. what we're imagining?",
        "rsd": "That feeling is real and intense. Let's separate the feeling from the facts.",
        "overwhelm": "You don't have to solve everything. What's ONE tiny thing?",
        "imposter": "You're learning. Everyone starts somewhere.",
    }
    return reframes.get(thought_type, "Let's pause and look at this from a different angle.")


# Load prompt from file
instruction = _load_prompt("emotional_agent")

emotional_agent = Agent(
    name="emotional_agent",
    model="gemini-2.0-flash",
    description="Provides emotional regulation support, calming techniques, "
                "and sensory overload detection.",
    instruction=instruction or """You provide emotional regulation support for ADHD/autism.

Handle:
- Sensory overload: Quick check, simple accommodation
- Freeze states: Acknowledge, 2-minute reset, smallest next step
- Overwhelm: Validate, one tiny action
- Anxiety: Reframe, time-box, lower the bar
- RSD: Normalize, reality check, self-compassion

Keep interventions SHORT and actionable. Voice-friendly only.
""",
    tools=[
        FunctionTool(start_breathing_exercise),
        FunctionTool(sensory_check),
        FunctionTool(grounding_exercise),
        FunctionTool(suggest_break),
        FunctionTool(reframe_thought),
    ],
)
