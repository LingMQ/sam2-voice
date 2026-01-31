"""Conversation context storage for agent interactions."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Message:
    """A single conversation message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    agent: Optional[str] = None  # Which agent responded


@dataclass
class ConversationContext:
    """Stores conversation history and context for agents."""

    messages: list[Message] = field(default_factory=list)
    max_messages: int = 50  # Keep last N messages

    # Context injected into prompts
    user_preferences: dict = field(default_factory=dict)
    successful_interventions: list = field(default_factory=list)
    recent_insights: list = field(default_factory=list)

    def add_user_message(self, content: str):
        """Add a user message to the conversation."""
        self.messages.append(Message(role="user", content=content))
        self._trim_messages()

    def add_assistant_message(self, content: str, agent: Optional[str] = None):
        """Add an assistant message to the conversation."""
        self.messages.append(Message(role="assistant", content=content, agent=agent))
        self._trim_messages()

    def _trim_messages(self):
        """Keep only the last max_messages."""
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_recent_messages(self, n: int = 10) -> list[dict]:
        """Get the last N messages as dicts."""
        return [
            {"role": m.role, "content": m.content}
            for m in self.messages[-n:]
        ]

    def get_transcript(self) -> list[dict]:
        """Get full transcript for reflection."""
        return [
            {
                "role": m.role,
                "content": m.content,
                "agent": m.agent,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in self.messages
        ]

    def inject_memory_context(
        self,
        preferences: dict,
        successful_interventions: list,
        insights: list
    ):
        """Inject memory-based context for personalization."""
        self.user_preferences = preferences
        self.successful_interventions = successful_interventions[-5:]  # Last 5
        self.recent_insights = insights[-3:]  # Last 3

    def get_personalized_context(self) -> str:
        """Generate context string to inject into agent prompts."""
        parts = []

        if self.user_preferences:
            prefs = [f"- {k}: {v}" for k, v in self.user_preferences.items() if v is not None]
            if prefs:
                parts.append("## User preferences:\n" + "\n".join(prefs))

        if self.successful_interventions:
            examples = "\n".join([
                f"- '{i.get('intervention_text', '')}' → {i.get('outcome', '')}"
                for i in self.successful_interventions
            ])
            parts.append(f"## What works for this user:\n{examples}")

        if self.recent_insights:
            insights_str = "\n".join(f"- {i}" for i in self.recent_insights)
            parts.append(f"## Key insights:\n{insights_str}")

        return "\n\n".join(parts) if parts else ""
