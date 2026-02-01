"""Session tracking and summary for Weave observability."""

import weave
from datetime import datetime
from typing import Optional, Dict, List, Any


class SessionTracker:
    """Tracks session metrics and logs summaries to Weave.

    Captures:
    - Session duration
    - Tools called and their outcomes
    - Task completion events
    - Emotional regulation events
    - Overall session effectiveness
    """

    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.started_at = datetime.now()
        self.tools_called: List[Dict[str, Any]] = []
        self.tasks_completed = 0
        self.steps_completed = 0
        self.emotional_interventions = 0
        self.checkins_scheduled = 0

    def record_tool_call(self, tool_name: str, args: dict, result: str):
        """Record a tool call for session summary."""
        self.tools_called.append({
            "tool": tool_name,
            "args": args,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        })

        # Track specific metrics
        if tool_name == "mark_step_complete":
            self.steps_completed += 1
            if "All done" in result or "All steps complete" in result:
                self.tasks_completed += 1
        elif tool_name in {"start_breathing_exercise", "grounding_exercise", "reframe_thought", "sensory_check"}:
            self.emotional_interventions += 1
        elif tool_name == "schedule_checkin":
            self.checkins_scheduled += 1

    @weave.op
    def log_session_summary(self) -> dict:
        """Log session summary to Weave.

        Call this at end of session to capture metrics.

        Returns:
            Session summary dict
        """
        duration = (datetime.now() - self.started_at).total_seconds()

        # Count tools by category
        tool_counts = {}
        for call in self.tools_called:
            tool = call["tool"]
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        summary = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "duration_seconds": duration,
            "duration_minutes": round(duration / 60, 2),
            "total_tool_calls": len(self.tools_called),
            "tools_breakdown": tool_counts,
            "tasks_completed": self.tasks_completed,
            "steps_completed": self.steps_completed,
            "emotional_interventions": self.emotional_interventions,
            "checkins_scheduled": self.checkins_scheduled,
            "started_at": self.started_at.isoformat(),
            "ended_at": datetime.now().isoformat(),
        }

        # Add weave attributes for filtering
        weave.attributes({
            "session_id": self.session_id,
            "user_id": self.user_id,
            "session_duration_minutes": summary["duration_minutes"],
            "session_productive": self.steps_completed > 0 or self.tasks_completed > 0,
        })

        return summary

    def get_effectiveness_score(self) -> float:
        """Calculate overall session effectiveness.

        Returns:
            Score from 0.0 to 1.0
        """
        if not self.tools_called:
            return 0.0

        # Weight different outcomes
        score = 0.0
        score += self.tasks_completed * 1.0  # Full task = high value
        score += self.steps_completed * 0.3  # Each step = some value
        score += self.emotional_interventions * 0.2  # Emotional support = value
        score += self.checkins_scheduled * 0.1  # Engagement = value

        # Normalize by tool calls (more efficient = better)
        return min(1.0, score / max(1, len(self.tools_called)))


@weave.op
def log_intervention_feedback(
    call_id: str,
    feedback_type: str,
    reason: Optional[str] = None,
) -> dict:
    """Log feedback on an intervention.

    Args:
        call_id: The Weave call ID to attach feedback to
        feedback_type: "thumbs_up" or "thumbs_down"
        reason: Optional reason for the feedback

    Returns:
        Feedback confirmation
    """
    return {
        "call_id": call_id,
        "feedback_type": feedback_type,
        "reason": reason,
        "recorded_at": datetime.now().isoformat(),
    }


@weave.op
def mark_intervention_successful(
    tool_name: str,
    session_id: str,
    user_id: str,
    outcome: str,
) -> dict:
    """Mark an intervention as successful for learning.

    This creates a trace that can be used to:
    1. Track successful patterns in Weave
    2. Feed into Redis memory (when implemented)
    3. Train better interventions over time

    Args:
        tool_name: The tool that was successful
        session_id: Session where success occurred
        user_id: User who benefited
        outcome: Description of the positive outcome

    Returns:
        Success record
    """
    weave.attributes({
        "intervention_successful": True,
        "tool_name": tool_name,
        "session_id": session_id,
        "user_id": user_id,
    })

    return {
        "tool_name": tool_name,
        "session_id": session_id,
        "user_id": user_id,
        "outcome": outcome,
        "recorded_at": datetime.now().isoformat(),
        "should_store_in_memory": True,  # Flag for Redis integration
    }
