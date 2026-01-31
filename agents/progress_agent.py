"""Progress tracking and adaptation agent."""

from pathlib import Path
from datetime import datetime
from typing import Optional

from google.adk import Agent
from google.adk.tools import tool


# In-memory progress storage for MVP
_user_progress: dict[str, dict] = {}


@tool
def record_session_metric(
    user_id: str,
    metric: str,
    value: float,
    context: str = ""
) -> str:
    """Record a progress metric for a user.

    Args:
        user_id: User identifier
        metric: Metric name (task_completion, focus_duration, etc.)
        value: Metric value
        context: Optional context about the metric

    Returns:
        Confirmation message
    """
    if user_id not in _user_progress:
        _user_progress[user_id] = {"metrics": [], "patterns": {}}

    _user_progress[user_id]["metrics"].append({
        "metric": metric,
        "value": value,
        "context": context,
        "timestamp": datetime.now().isoformat(),
    })

    return f"Recorded {metric}={value} for user"


@tool
def get_user_patterns(user_id: str) -> str:
    """Get observed patterns for a user.

    Args:
        user_id: User identifier

    Returns:
        Pattern summary
    """
    if user_id not in _user_progress:
        return "No patterns recorded yet for this user"

    patterns = _user_progress[user_id].get("patterns", {})
    if not patterns:
        return "Still learning patterns for this user"

    summary = []
    for pattern, value in patterns.items():
        summary.append(f"- {pattern}: {value}")

    return "Observed patterns:\n" + "\n".join(summary)


@tool
def update_optimal_checkin(user_id: str, minutes: float) -> str:
    """Update the optimal check-in interval for a user.

    Args:
        user_id: User identifier
        minutes: Optimal check-in interval in minutes

    Returns:
        Confirmation message
    """
    if user_id not in _user_progress:
        _user_progress[user_id] = {"metrics": [], "patterns": {}}

    _user_progress[user_id]["patterns"]["optimal_checkin_minutes"] = minutes

    return f"Updated optimal check-in interval to {minutes} minutes"


@tool
def get_session_stats(user_id: str) -> str:
    """Get statistics for the current session.

    Args:
        user_id: User identifier

    Returns:
        Session statistics summary
    """
    if user_id not in _user_progress:
        return "No session data available"

    metrics = _user_progress[user_id].get("metrics", [])
    if not metrics:
        return "No metrics recorded this session"

    # Calculate basic stats
    task_completions = sum(1 for m in metrics if m["metric"] == "task_completion" and m["value"] > 0)
    total_focus_time = sum(m["value"] for m in metrics if m["metric"] == "focus_duration")

    return f"Session stats: {task_completions} tasks completed, {total_focus_time:.1f} min focused time"


@tool
def suggest_adaptation(user_id: str, current_approach: str) -> str:
    """Suggest an adaptation based on user patterns.

    Args:
        user_id: User identifier
        current_approach: Current approach being used

    Returns:
        Suggested adaptation
    """
    if user_id not in _user_progress:
        return "Continue current approach - still gathering data"

    patterns = _user_progress[user_id].get("patterns", {})

    # Simple heuristic suggestions
    if patterns.get("responds_to_gamification"):
        return "Try framing tasks as quests or challenges"
    if patterns.get("needs_shorter_steps"):
        return "Break steps into even smaller pieces"
    if patterns.get("prefers_quiet_support"):
        return "Keep acknowledgments brief and understated"

    return "Current approach seems to be working - maintain consistency"


progress_agent = Agent(
    name="progress_agent",
    model="gemini-2.0-flash",
    description="Tracks patterns across sessions and adapts timing/approach. "
                "Learns what works for each user over time.",
    instruction="""You track progress patterns and adapt the support approach over time.

Your responsibilities:
- Monitor task completion rates and engagement duration
- Identify what interventions work for this specific user
- Adjust check-in timing based on observed attention patterns
- Suggest adaptations to other agents based on learned patterns

Key metrics to track:
- Task completion rate (steps completed / steps started)
- Focus duration (time between distractions)
- Optimal check-in interval (when check-ins help vs. interrupt)
- Response to different intervention styles

Keep analysis internal - only surface actionable insights to other agents.
Responses to users should still be brief and supportive.
""",
    tools=[record_session_metric, get_user_patterns, update_optimal_checkin, get_session_stats, suggest_adaptation],
)
