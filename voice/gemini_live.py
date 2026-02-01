"""Gemini Live API client for real-time voice conversations."""

import asyncio
import base64
import json
import os
from dataclasses import dataclass, field
from typing import AsyncIterator, Callable, Optional

import weave
from google import genai
from google.genai import types

from state.session import SessionState
from state.context import ConversationContext


@dataclass
class GeminiLiveConfig:
    """Configuration for Gemini Live API session."""

    model: str = field(
        default_factory=lambda: os.getenv(
            "GEMINI_LIVE_MODEL",
            "gemini-2.5-flash-native-audio-latest",
        )
    )
    voice: str = "Puck"  # Puck, Charon, Kore, Fenrir, Aoede
    system_instruction: Optional[str] = None

    # Audio settings
    sample_rate: int = 16000
    channels: int = 1

    # Response settings
    response_modalities: list[str] = field(default_factory=lambda: ["AUDIO"])

    # Tool definitions for agent capabilities
    tools: list = field(default_factory=list)


class GeminiLiveClient:
    """Client for Gemini Live API real-time voice conversations.

    This client handles:
    - WebSocket connection to Gemini Live API
    - Bidirectional audio streaming
    - Tool calling for agent integration
    - Session state management
    """

    def __init__(
        self,
        config: Optional[GeminiLiveConfig] = None,
        session_id: str = "default",
        user_id: str = "user",
    ):
        self.config = config or GeminiLiveConfig()
        self.session_id = session_id
        self.user_id = user_id

        # Initialize Google GenAI client
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

        # State management
        self.session_state = SessionState(session_id=session_id, user_id=user_id)
        self.context = ConversationContext()

        # Session handle
        self._session = None
        self._session_cm = None
        self._is_connected = False

        # Callbacks
        self._on_audio: Optional[Callable[[bytes], None]] = None
        self._on_text: Optional[Callable[[str], None]] = None
        self._on_tool_call: Optional[Callable[[str, dict], str]] = None
        self._on_turn_complete: Optional[Callable[[], None]] = None

    def set_audio_callback(self, callback: Callable[[bytes], None]):
        """Set callback for receiving audio data."""
        self._on_audio = callback

    def set_text_callback(self, callback: Callable[[str], None]):
        """Set callback for receiving text transcripts."""
        self._on_text = callback

    def set_tool_callback(self, callback: Callable[[str, dict], str]):
        """Set callback for handling tool calls."""
        self._on_tool_call = callback

    def set_turn_complete_callback(self, callback: Callable[[], None]):
        """Set callback for when model finishes responding."""
        self._on_turn_complete = callback

    def _build_system_instruction(self) -> str:
        """Build the system instruction with personalized context."""
        base_instruction = self.config.system_instruction or self._get_default_instruction()

        # Add personalized context from memory
        personalized = self.context.get_personalized_context()
        if personalized:
            return f"{base_instruction}\n\n---\nPERSONALIZED CONTEXT:\n{personalized}\n---"

        return base_instruction

    def _get_default_instruction(self) -> str:
        """Get the default system instruction."""
        return """You are a supportive voice assistant for people with ADHD and autism.

Your core purpose is to provide an EXTERNAL FEEDBACK LOOP that compensates for
dysregulated internal feedback mechanisms.

Key behaviors:
- Provide frequent micro-reinforcements (small positive acknowledgments)
- Break tasks into tiny, achievable steps (2-5 minutes each)
- Check in regularly to maintain engagement
- Offer gentle redirection when users get distracted
- Be warm, patient, and non-judgmental
- Keep responses SHORT (1-2 sentences) for natural voice conversation

You have access to tools for:
- Scheduling check-ins and reminders
- Breaking down tasks into micro-steps
- Tracking progress and wins
- Providing emotional regulation techniques

Use tools proactively to help the user stay on track. Always prioritize
the user's current emotional state and engagement level.

Never be preachy or give long explanations. Quick, supportive responses only."""

    def _build_tools(self) -> list:
        """Build tool definitions for Gemini Live API."""
        return [
            {
                "function_declarations": [
                    {
                        "name": "schedule_checkin",
                        "description": "Schedule a check-in with the user after specified minutes",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "minutes": {
                                    "type": "integer",
                                    "description": "Minutes until check-in (typically 2-5)"
                                }
                            },
                            "required": ["minutes"]
                        }
                    },
                    {
                        "name": "create_microsteps",
                        "description": "Break a task into micro-steps",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "task": {
                                    "type": "string",
                                    "description": "The task to break down"
                                },
                                "count": {
                                    "type": "integer",
                                    "description": "Number of steps (default 3)"
                                }
                            },
                            "required": ["task"]
                        }
                    },
                    {
                        "name": "mark_step_complete",
                        "description": "Mark the current step as complete",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "log_win",
                        "description": "Log a micro-win for positive reinforcement",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "description": {
                                    "type": "string",
                                    "description": "What the user accomplished"
                                }
                            },
                            "required": ["description"]
                        }
                    },
                    {
                        "name": "start_breathing_exercise",
                        "description": "Guide a quick breathing exercise for regulation",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "breaths": {
                                    "type": "integer",
                                    "description": "Number of breaths (default 3)"
                                }
                            }
                        }
                    },
                    {
                        "name": "sensory_check",
                        "description": "Prompt a sensory environment check",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        ]

    @weave.op
    async def connect(self) -> bool:
        """Connect to Gemini Live API.

        Returns:
            True if connection successful
        """
        try:
            # Build live connect config
            config = types.LiveConnectConfig(
                response_modalities=self.config.response_modalities,
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.config.voice
                        )
                    )
                ),
                system_instruction=types.Content(
                    parts=[types.Part(text=self._build_system_instruction())]
                ),
                tools=self._build_tools(),
            )

            # Connect to Live API
            # `connect` returns an async context manager; enter it for a live session
            self._session_cm = self.client.aio.live.connect(
                model=self.config.model,
                config=config,
            )
            self._session = await self._session_cm.__aenter__()

            self._is_connected = True
            print(f"Connected to Gemini Live API ({self.config.model})")
            return True

        except Exception as e:
            print(f"Failed to connect to Gemini Live API: {e}")
            return False

    @weave.op
    async def disconnect(self):
        """Disconnect from Gemini Live API."""
        if self._session_cm:
            await self._session_cm.__aexit__(None, None, None)
            self._session_cm = None
            self._session = None
        self._is_connected = False
        print("Disconnected from Gemini Live API")

    @property
    def is_connected(self) -> bool:
        """Check if connected to Gemini Live API."""
        return self._is_connected

    @weave.op
    async def send_audio(self, audio_data: bytes):
        """Send audio data to Gemini Live API.

        Args:
            audio_data: Raw PCM audio bytes
        """
        if not self._session:
            return

        # Send as realtime input
        await self._session.send_realtime_input(
            media=types.Blob(
                mime_type=f"audio/pcm;rate={self.config.sample_rate}",
                data=audio_data,
            )
        )

    @weave.op
    async def send_text(self, text: str):
        """Send text message to Gemini Live API.

        Args:
            text: Text message to send
        """
        if not self._session:
            return

        self.context.add_user_message(text)

        await self._session.send_client_content(
            turns=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=text)],
                )
            ],
            turn_complete=True,
        )

    async def receive_responses(self) -> AsyncIterator[dict]:
        """Receive responses from Gemini Live API.

        Yields:
            Response events with type and data
        """
        if not self._session:
            return

        while self._session:
            async for response in self._session.receive():
                # Handle different response types
                if response.server_content:
                    content = response.server_content

                    # Audio response
                    if content.model_turn:
                        for part in content.model_turn.parts:
                            if part.inline_data:
                                # Audio data
                                audio_payload = part.inline_data.data
                                if isinstance(audio_payload, str):
                                    audio_bytes = base64.b64decode(audio_payload)
                                else:
                                    audio_bytes = audio_payload
                                if self._on_audio:
                                    self._on_audio(audio_bytes)
                                yield {"type": "audio", "data": audio_bytes}

                            elif part.text:
                                # Text response
                                if self._on_text:
                                    self._on_text(part.text)
                                self.context.add_assistant_message(part.text)
                                yield {"type": "text", "data": part.text}

                    # Turn complete
                    if content.turn_complete:
                        if self._on_turn_complete:
                            self._on_turn_complete()
                        yield {"type": "turn_complete", "data": None}

                # Tool call
                elif response.tool_call:
                    tool_call = response.tool_call
                    for fc in tool_call.function_calls:
                        result = await self._handle_tool_call(fc.name, fc.args)
                        yield {"type": "tool_call", "name": fc.name, "result": result}

                        # Send tool response back
                        response_kwargs = {
                            "name": fc.name,
                            "response": {"result": result},
                        }
                        if getattr(fc, "id", None):
                            response_kwargs["id"] = fc.id

                        await self._session.send_tool_response(
                            function_responses=[types.FunctionResponse(**response_kwargs)]
                        )

    @weave.op
    async def _handle_tool_call(self, name: str, args: dict) -> str:
        """Handle a tool call from the model.

        Args:
            name: Tool name
            args: Tool arguments

        Returns:
            Tool result string
        """
        # Use external callback if set
        if self._on_tool_call:
            return self._on_tool_call(name, args)

        # Default tool implementations
        if name == "schedule_checkin":
            minutes = args.get("minutes", 3)
            return f"Check-in scheduled for {minutes} minutes from now"

        elif name == "create_microsteps":
            task = args.get("task", "task")
            count = args.get("count", 3)
            self.session_state.start_task(task, count)
            return f"Created {count} micro-steps for: {task}"

        elif name == "mark_step_complete":
            self.session_state.complete_step()
            step = self.session_state.current_step
            total = self.session_state.total_steps
            if step >= total:
                return "All steps complete!"
            return f"Step {step} complete. {total - step} remaining."

        elif name == "log_win":
            desc = args.get("description", "accomplishment")
            self.session_state.record_intervention(desc, "task_completed")
            return f"Win logged: {desc}"

        elif name == "start_breathing_exercise":
            breaths = args.get("breaths", 3)
            return f"Starting {breaths}-breath exercise"

        elif name == "sensory_check":
            return "Prompting sensory check: noise, light, or body?"

        return f"Unknown tool: {name}"

    def get_session_summary(self) -> dict:
        """Get summary of the current session."""
        return self.session_state.get_session_summary()

    def get_transcript(self) -> list:
        """Get the conversation transcript."""
        return self.context.get_transcript()
