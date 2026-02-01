"""Custom Weave scorers for measuring intervention effectiveness."""

import weave
from typing import Optional


class InterventionEffectivenessScorer(weave.Scorer):
    """Measures if tool interventions led to positive outcomes.

    This scorer evaluates:
    - Did the intervention help the user progress?
    - Did the user complete the task?
    - Did the user stay engaged?

    Used for the "Self-Improving Agents" theme to demonstrate
    measurable improvement over time.
    """

    @weave.op
    def score(
        self,
        tool_name: str,
        tool_result: str,
        user_response: Optional[str] = None,
        task_completed: bool = False,
        user_re_engaged: bool = False,
    ) -> dict:
        """Score an intervention's effectiveness.

        Args:
            tool_name: Name of the tool that was called
            tool_result: What the tool returned
            user_response: What the user said after (if available)
            task_completed: Whether the user completed a task step
            user_re_engaged: Whether the user re-engaged after intervention

        Returns:
            Scoring dict with effectiveness metrics
        """
        # Determine intervention category
        category = self._categorize_tool(tool_name)

        # Calculate effectiveness
        effectiveness = 0.0
        if task_completed:
            effectiveness = 1.0
        elif user_re_engaged:
            effectiveness = 0.7
        elif user_response and len(user_response) > 10:
            effectiveness = 0.3  # At least got a response

        return {
            "tool_name": tool_name,
            "category": category,
            "task_completed": task_completed,
            "user_re_engaged": user_re_engaged,
            "effectiveness": effectiveness,
            "intervention_successful": effectiveness >= 0.7,
        }

    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize tool by type."""
        task_tools = {"create_microsteps", "get_current_step", "mark_step_complete"}
        emotional_tools = {"start_breathing_exercise", "grounding_exercise", "reframe_thought"}
        feedback_tools = {"schedule_checkin", "log_micro_win"}

        if tool_name in task_tools:
            return "task_management"
        elif tool_name in emotional_tools:
            return "emotional_regulation"
        elif tool_name in feedback_tools:
            return "feedback_loop"
        return "other"


class MemoryRetrievalScorer(weave.Scorer):
    """Measures quality of memory retrieval from Redis.

    Evaluates:
    - Were similar interventions found?
    - Was the retrieved context relevant?
    - Did using memory improve the response?
    """

    @weave.op
    def score(
        self,
        query: str,
        retrieved_count: int,
        top_similarity: float,
        memory_used_in_response: bool = False,
    ) -> dict:
        """Score memory retrieval quality.

        Args:
            query: The user's message that triggered retrieval
            retrieved_count: Number of similar interventions found
            top_similarity: Similarity score of best match (0-1)
            memory_used_in_response: Whether agent used memory context

        Returns:
            Scoring dict with retrieval metrics
        """
        # High similarity means good semantic match
        relevance = top_similarity if top_similarity > 0.7 else 0.0

        return {
            "retrieved_count": retrieved_count,
            "top_similarity": top_similarity,
            "memory_used": memory_used_in_response,
            "retrieval_relevant": relevance > 0.7,
            "retrieval_score": relevance,
        }
