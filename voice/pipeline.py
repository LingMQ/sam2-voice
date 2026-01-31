"""Pipecat voice pipeline with ADK agent integration."""

import os
from typing import Optional

from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import Frame, TextFrame, TranscriptionFrame, LLMFullResponseEndFrame
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.transports.services.daily import DailyTransport, DailyParams
from pipecat.transports.local.audio import LocalAudioTransport
from pipecat.vad.silero import SileroVADAnalyzer

from agents.main_agent import root_agent, run_agent
from state.session import SessionState
from state.context import ConversationContext


class ADKAgentProcessor(FrameProcessor):
    """Bridge between Pipecat pipeline and Google ADK agents.

    This processor:
    1. Receives TranscriptionFrame from STT (user's transcribed speech)
    2. Sends the text to the ADK orchestrator agent
    3. Returns the agent's response as TextFrame for TTS
    """

    def __init__(
        self,
        agent=None,
        session_id: str = "default",
        user_id: str = "user"
    ):
        super().__init__()
        self.agent = agent or root_agent
        self.session_id = session_id
        self.user_id = user_id

        # State management
        self.session_state = SessionState(session_id=session_id, user_id=user_id)
        self.context = ConversationContext()

    async def process_frame(self, frame: Frame, direction):
        """Process incoming frames and route to ADK agents.

        Args:
            frame: The incoming Pipecat frame
            direction: Frame direction (upstream/downstream)
        """
        await super().process_frame(frame, direction)

        # Handle transcription frames (user speech converted to text)
        if isinstance(frame, TranscriptionFrame):
            user_text = frame.text

            if user_text and user_text.strip():
                # Record the interaction
                self.session_state.record_interaction()
                self.context.add_user_message(user_text)

                try:
                    # Get personalized context
                    personalized_context = self.context.get_personalized_context()

                    # Run through ADK agent
                    response = await run_agent(
                        self.agent,
                        user_text,
                        session_id=self.session_id,
                        context=personalized_context if personalized_context else None
                    )

                    if response:
                        # Record assistant response
                        self.context.add_assistant_message(response, agent="main_agent")

                        # Output as text frame for TTS
                        await self.push_frame(TextFrame(text=response))
                        await self.push_frame(LLMFullResponseEndFrame())

                except Exception as e:
                    print(f"Error processing with ADK: {e}")
                    # Provide fallback response
                    fallback = "I'm here with you. Could you say that again?"
                    await self.push_frame(TextFrame(text=fallback))
                    await self.push_frame(LLMFullResponseEndFrame())
        else:
            # Pass through other frame types unchanged
            await self.push_frame(frame, direction)

    def get_session_summary(self) -> dict:
        """Get summary of the current session."""
        return self.session_state.get_session_summary()

    def get_transcript(self) -> list:
        """Get the conversation transcript."""
        return self.context.get_transcript()


async def create_pipeline(
    transport_type: str = "daily",
    room_url: Optional[str] = None,
    token: Optional[str] = None,
    session_id: str = "default",
    user_id: str = "user"
):
    """Create the voice processing pipeline.

    Pipeline flow:
    Audio In → STT (Deepgram) → ADK Agent → TTS (Cartesia) → Audio Out

    Args:
        transport_type: "daily" for WebRTC or "local" for local audio
        room_url: Daily.co room URL (required for daily transport)
        token: Optional Daily.co meeting token
        session_id: Session identifier for state management
        user_id: User identifier

    Returns:
        Tuple of (pipeline, transport, adk_processor) for running the voice bot
    """
    # Create transport based on type
    if transport_type == "local":
        transport = LocalAudioTransport(
            mic_enabled=True,
            speaker_enabled=True,
        )
    else:
        # Daily WebRTC transport
        if not room_url:
            raise ValueError("room_url is required for Daily transport")

        transport = DailyTransport(
            room_url=room_url,
            token=token,
            bot_name="Support Assistant",
            params=DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                transcription_enabled=False,  # We use our own STT
            )
        )

    # Deepgram Speech-to-Text service
    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
    )

    # Cartesia Text-to-Speech service
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id=os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091"),  # Default: Barbershop Man
    )

    # ADK Agent processor
    adk_processor = ADKAgentProcessor(
        session_id=session_id,
        user_id=user_id
    )

    # Build the processing pipeline
    pipeline = Pipeline([
        transport.input(),   # Audio from transport
        stt,                 # Convert speech to text
        adk_processor,       # Process with ADK agents
        tts,                 # Convert response to speech
        transport.output(),  # Audio back to transport
    ])

    return pipeline, transport, adk_processor
