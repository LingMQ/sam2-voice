"""Audio event handlers for the voice bot."""

from typing import Callable, Optional
from pipecat.frames.frames import TextFrame


class VoiceEventHandlers:
    """Handles voice transport events."""

    def __init__(self, task, adk_processor=None):
        """Initialize event handlers.

        Args:
            task: The PipelineTask instance
            adk_processor: Optional ADKAgentProcessor for session access
        """
        self.task = task
        self.adk_processor = adk_processor
        self._on_session_end: Optional[Callable] = None

    def set_session_end_callback(self, callback: Callable):
        """Set callback for session end (for reflection generation)."""
        self._on_session_end = callback

    async def on_first_participant_joined(self, transport, participant):
        """Handle first participant joining - greet them.

        Args:
            transport: The transport instance
            participant: Participant info dict
        """
        print(f"Participant joined: {participant.get('id', 'unknown')}")

        # Queue the greeting
        await self.task.queue_frames([
            TextFrame(
                "Hi! I'm here to help you stay on track. "
                "What are you working on today?"
            )
        ])

    async def on_participant_joined(self, transport, participant):
        """Handle any participant joining.

        Args:
            transport: The transport instance
            participant: Participant info dict
        """
        print(f"Participant joined: {participant.get('id', 'unknown')}")

    async def on_participant_left(self, transport, participant, reason):
        """Handle participant leaving.

        Args:
            transport: The transport instance
            participant: Participant info dict
            reason: Reason for leaving
        """
        print(f"Participant left: {participant.get('id', 'unknown')}, reason: {reason}")

        # Trigger session end callback for reflection
        if self._on_session_end and self.adk_processor:
            summary = self.adk_processor.get_session_summary()
            transcript = self.adk_processor.get_transcript()
            await self._on_session_end(summary, transcript)

    async def on_call_state_updated(self, transport, state):
        """Handle call state changes.

        Args:
            transport: The transport instance
            state: New call state
        """
        print(f"Call state: {state}")

        if state == "left":
            await self.task.cancel()

    async def on_dialin_ready(self, transport, sip_endpoint):
        """Handle dial-in ready (for phone integration).

        Args:
            transport: The transport instance
            sip_endpoint: SIP endpoint for dial-in
        """
        print(f"Dial-in ready: {sip_endpoint}")

    async def on_error(self, transport, error):
        """Handle transport errors.

        Args:
            transport: The transport instance
            error: Error information
        """
        print(f"Transport error: {error}")

    def register_handlers(self, transport):
        """Register all event handlers with the transport.

        Args:
            transport: The transport to register handlers with
        """
        transport.event_handler("on_first_participant_joined")(
            self.on_first_participant_joined
        )
        transport.event_handler("on_participant_joined")(
            self.on_participant_joined
        )
        transport.event_handler("on_participant_left")(
            self.on_participant_left
        )
        transport.event_handler("on_call_state_updated")(
            self.on_call_state_updated
        )

        # Optional handlers - check if transport supports them
        if hasattr(transport, "on_dialin_ready"):
            transport.event_handler("on_dialin_ready")(
                self.on_dialin_ready
            )
