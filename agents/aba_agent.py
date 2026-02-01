"""ABA (Applied Behavior Analysis) therapy agent."""

from pathlib import Path
from google.adk import Agent
from google.adk.tools import FunctionTool


def _load_prompt(name: str) -> str:
    """Load a prompt from the config/prompts directory."""
    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / f"{name}.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


def record_behavior(behavior: str, antecedent: str, consequence: str) -> str:
    """Record an ABC (Antecedent-Behavior-Consequence) observation.

    Args:
        behavior: The behavior observed
        antecedent: What happened before the behavior
        consequence: What happened after the behavior

    Returns:
        Confirmation message
    """
    # In MVP, just acknowledge - could integrate with tracking later
    return f"Recorded: {antecedent} → {behavior} → {consequence}"


def suggest_reinforcement(behavior_type: str) -> str:
    """Suggest an appropriate reinforcement for a behavior type.

    Args:
        behavior_type: Type of behavior (initiation, completion, recovery, persistence)

    Returns:
        Suggested reinforcement approach
    """
    reinforcements = {
        "initiation": "Acknowledge starting without prompting - this builds independence",
        "completion": "Celebrate the finish with specific praise about the accomplishment",
        "recovery": "Praise the self-correction - noticing and returning is a skill",
        "persistence": "Acknowledge effort and duration - stamina is being built",
    }
    return reinforcements.get(behavior_type, "Provide warm, specific acknowledgment")


def get_prompt_level(independence_level: int) -> str:
    """Get the appropriate prompt level based on user's current independence.

    Args:
        independence_level: 1-5 scale (1=needs full support, 5=independent)

    Returns:
        Recommended prompt approach
    """
    prompts = {
        1: "Full verbal prompt - tell them exactly what to do step by step",
        2: "Partial prompt - start the instruction, let them complete it",
        3: "Indirect prompt - ask guiding questions",
        4: "Minimal prompt - brief reminder or cue",
        5: "No prompt needed - just be available if needed",
    }
    return prompts.get(independence_level, prompts[3])


# Load prompt from file
instruction = _load_prompt("aba_agent")

aba_agent = Agent(
    name="aba_agent",
    model="gemini-2.0-flash",
    description="Implements ABA therapy techniques: positive reinforcement, "
                "prompting, shaping, and task analysis.",
    instruction=instruction or """You implement ABA therapy techniques for voice interaction.

Core techniques:
- Positive reinforcement: Immediately acknowledge desired behaviors
- Prompting: Provide appropriate level of support (full to minimal)
- Shaping: Reinforce successive approximations toward goal
- Task analysis: Break complex behaviors into teachable steps

Keep all interventions voice-friendly (short, clear) and non-punitive.
Focus on building independence respectfully.
""",
    tools=[
        FunctionTool(record_behavior),
        FunctionTool(suggest_reinforcement),
        FunctionTool(get_prompt_level),
    ],
)
