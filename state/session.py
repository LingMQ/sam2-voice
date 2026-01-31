"""Session state management for voice conversations."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class SessionState:
    """Manages state for a single voice session."""

    session_id: str
    user_id: str
    started_at: datetime = field(default_factory=datetime.now)

    # Current task tracking
    current_task: Optional[str] = None
    current_step: int = 0
    total_steps: int = 0

    # Engagement tracking
    last_interaction: datetime = field(default_factory=datetime.now)
    interaction_count: int = 0
    distraction_count: int = 0

    # Check-in state
    next_checkin_minutes: float = 3.0
    last_checkin: Optional[datetime] = None

    # Emotional state (inferred)
    current_mood: str = "neutral"  # neutral, positive, stressed, overwhelmed, frozen

    # Session outcomes for learning
    completed_steps: list = field(default_factory=list)
    interventions: list = field(default_factory=list)

    def record_interaction(self):
        """Record that an interaction occurred."""
        self.last_interaction = datetime.now()
        self.interaction_count += 1

    def record_distraction(self):
        """Record a detected distraction."""
        self.distraction_count += 1

    def start_task(self, task: str, steps: int = 1):
        """Start tracking a new task."""
        self.current_task = task
        self.current_step = 0
        self.total_steps = steps

    def complete_step(self):
        """Mark current step as complete."""
        if self.current_task:
            self.completed_steps.append({
                "task": self.current_task,
                "step": self.current_step,
                "completed_at": datetime.now().isoformat(),
            })
            self.current_step += 1
            if self.current_step >= self.total_steps:
                self.current_task = None

    def record_intervention(self, intervention: str, outcome: str):
        """Record an intervention and its outcome."""
        self.interventions.append({
            "intervention": intervention,
            "outcome": outcome,
            "timestamp": datetime.now().isoformat(),
            "task": self.current_task,
            "mood": self.current_mood,
        })

    def get_session_summary(self) -> dict:
        """Get summary of the session for reflection."""
        duration = (datetime.now() - self.started_at).total_seconds()
        return {
            "session_id": self.session_id,
            "duration_minutes": duration / 60,
            "interaction_count": self.interaction_count,
            "distraction_count": self.distraction_count,
            "steps_completed": len(self.completed_steps),
            "interventions": self.interventions,
        }
