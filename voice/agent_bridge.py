"""Bridge between Gemini Live tools and ADK agent tool implementations."""

from typing import Callable, Dict, Any

import weave

# Import ADK tool functions directly from agent modules
# These are the underlying functions, not the @tool decorated versions
from agents.task_agent import (
    _current_tasks,
)
from agents.feedback_loop_agent import (
    _scheduled_checkins,
)

from datetime import datetime, timedelta


class AgentToolBridge:
    """Routes Gemini Live tool calls to ADK agent tool implementations.

    This bridge enables Gemini Live to use the same tool implementations
    as the ADK agents, ensuring consistent behavior and shared state.
    """

    def __init__(self, session_id: str = "default", user_id: str = "user"):
        """Initialize the bridge with session context.

        Args:
            session_id: Session identifier for tool state
            user_id: User identifier
        """
        self.session_id = session_id
        self.user_id = user_id

    @weave.op
    def handle_tool_call(self, name: str, args: dict) -> str:
        """Route a tool call to the appropriate implementation.

        Args:
            name: Tool name
            args: Tool arguments (from Gemini Live)

        Returns:
            Tool result string
        """
        # Add metadata for filtering in Weave dashboard
        weave.attributes({
            "user_id": self.user_id,
            "session_id": self.session_id,
            "tool_name": name,
            "tool_category": self._get_tool_category(name),
        })
        # Task agent tools
        if name == "create_microsteps":
            return self._create_microsteps(args)
        elif name == "get_current_step":
            return self._get_current_step(args)
        elif name == "mark_step_complete":
            return self._mark_step_complete(args)
        elif name == "get_current_time":
            return self._get_current_time(args)
        elif name == "create_reminder":
            return self._create_reminder(args)

        # Feedback loop agent tools
        elif name == "schedule_checkin":
            return self._schedule_checkin(args)
        elif name == "get_time_since_last_checkin":
            return self._get_time_since_last_checkin(args)
        elif name == "log_micro_win":
            return self._log_micro_win(args)
        # Keep log_win as alias for backwards compatibility
        elif name == "log_win":
            return self._log_micro_win({"description": args.get("description", "")})

        # Emotional agent tools
        elif name == "start_breathing_exercise":
            return self._start_breathing_exercise(args)
        elif name == "sensory_check":
            return self._sensory_check(args)
        elif name == "grounding_exercise":
            return self._grounding_exercise(args)
        elif name == "suggest_break":
            return self._suggest_break(args)
        elif name == "reframe_thought":
            return self._reframe_thought(args)

        return f"Unknown tool: {name}"

    # ==================== Task Agent Tools ====================

    def _create_microsteps(self, args: dict) -> str:
        """Break a task into micro-steps and store them."""
        task = args.get("task", "task")
        count = args.get("count", 3)

        _current_tasks[self.session_id] = {
            "task": task,
            "total_steps": count,
            "current_step": 0,
            "started_at": datetime.now().isoformat(),
        }
        return f"Created {count} micro-steps for: {task}"

    def _get_current_step(self, args: dict) -> str:
        """Get the current step the user should work on."""
        if self.session_id not in _current_tasks:
            return "No active task"

        task_info = _current_tasks[self.session_id]
        step = task_info["current_step"] + 1
        total = task_info["total_steps"]

        if step > total:
            return f"All {total} steps complete for: {task_info['task']}"

        return f"Step {step} of {total} for: {task_info['task']}"

    def _mark_step_complete(self, args: dict) -> str:
        """Mark the current micro-step as complete."""
        if self.session_id not in _current_tasks:
            return "No active task to update"

        task_info = _current_tasks[self.session_id]
        task_info["current_step"] += 1
        step = task_info["current_step"]
        total = task_info["total_steps"]

        if step >= total:
            task_name = task_info["task"]
            del _current_tasks[self.session_id]
            return f"All done! Completed all {total} steps for: {task_name}"

        return f"Step {step} complete! {total - step} steps remaining."

    def _get_current_time(self, args: dict) -> str:
        """Get the current time for time-awareness."""
        return datetime.now().strftime("%I:%M %p")

    def _create_reminder(self, args: dict) -> str:
        """Create a reminder for a task."""
        task = args.get("task", "task")
        minutes = args.get("minutes", 5)
        return f"Reminder set: '{task}' in {minutes} minutes"

    # ==================== Feedback Loop Agent Tools ====================

    def _schedule_checkin(self, args: dict) -> str:
        """Schedule a check-in with the user after specified minutes."""
        minutes = args.get("minutes", 3)
        checkin_time = datetime.now() + timedelta(minutes=minutes)
        _scheduled_checkins[self.session_id] = checkin_time
        return f"Check-in scheduled for {minutes} minutes from now"

    def _get_time_since_last_checkin(self, args: dict) -> str:
        """Get time since the last check-in."""
        if self.session_id in _scheduled_checkins:
            last = _scheduled_checkins[self.session_id]
            elapsed = (datetime.now() - last).total_seconds() / 60
            return f"{elapsed:.1f} minutes since last check-in"
        return "No previous check-in recorded"

    def _log_micro_win(self, args: dict) -> str:
        """Log a micro-win for the user to track progress."""
        description = args.get("description", "accomplishment")
        category = args.get("category", "general")
        return f"Win logged ({category}): {description}"

    # ==================== Emotional Agent Tools ====================

    def _start_breathing_exercise(self, args: dict) -> str:
        """Start a quick breathing exercise."""
        breaths = args.get("breaths", 3)
        if breaths <= 3:
            return "Quick reset: Breathe in slowly... hold... breathe out. Let's do that together."
        return f"Let's take {breaths} slow breaths together. I'll count with you."

    def _sensory_check(self, args: dict) -> str:
        """Prompt a quick sensory environment check."""
        return "Quick sensory check - is it the noise, the light, or something in your body that's bothering you?"

    def _grounding_exercise(self, args: dict) -> str:
        """Start a grounding exercise."""
        technique = args.get("technique", "5-4-3-2-1")
        techniques = {
            "5-4-3-2-1": "Name 5 things you can see right now.",
            "body_scan": "Notice your feet on the floor. Feel your hands.",
            "simple": "What's one thing you can see right in front of you?",
        }
        return techniques.get(technique, techniques["simple"])

    def _suggest_break(self, args: dict) -> str:
        """Suggest a structured break."""
        duration_minutes = args.get("duration_minutes", 5)
        if duration_minutes <= 2:
            return "Quick 2-minute reset - step away, stretch, come back fresh."
        elif duration_minutes <= 5:
            return f"Take {duration_minutes} minutes. Get some water, move around a bit."
        else:
            return f"Let's take a proper {duration_minutes}-minute break. Set a timer and really step away."

    def _reframe_thought(self, args: dict) -> str:
        """Provide a cognitive reframe for common negative thought patterns."""
        thought_type = args.get("thought_type", "overwhelm")
        reframes = {
            "perfectionism": "This is prototype mode - it just needs to exist, not be perfect.",
            "catastrophizing": "What do we actually know for sure vs. what we're imagining?",
            "rsd": "That feeling is real and intense. Let's separate the feeling from the facts.",
            "overwhelm": "You don't have to solve everything. What's ONE tiny thing?",
            "imposter": "You're learning. Everyone starts somewhere.",
        }
        return reframes.get(thought_type, "Let's pause and look at this from a different angle.")

    def _get_tool_category(self, name: str) -> str:
        """Get the category for a tool name."""
        task_tools = {"create_microsteps", "get_current_step", "mark_step_complete", "get_current_time", "create_reminder"}
        feedback_tools = {"schedule_checkin", "get_time_since_last_checkin", "log_micro_win", "log_win"}
        emotional_tools = {"start_breathing_exercise", "sensory_check", "grounding_exercise", "suggest_break", "reframe_thought"}

        if name in task_tools:
            return "task"
        elif name in feedback_tools:
            return "feedback"
        elif name in emotional_tools:
            return "emotional"
        return "unknown"
