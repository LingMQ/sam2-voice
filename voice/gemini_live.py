"""Gemini Live API client for real-time voice conversations."""

import asyncio
import base64
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Callable, Optional

import weave
from google import genai
from google.genai import types

from state.session import SessionState
from state.context import ConversationContext
from voice.agent_bridge import AgentToolBridge
from memory.redis_memory import RedisUserMemory


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
        memory: Optional[RedisUserMemory] = None,
    ):
        self.config = config or GeminiLiveConfig()
        self.session_id = session_id
        self.user_id = user_id

        # Initialize Google GenAI client
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

        # State management
        self.session_state = SessionState(session_id=session_id, user_id=user_id)
        self.context = ConversationContext()

        # Memory system
        self.memory = memory
        self._memory_context: Optional[str] = None  # Static context loaded at start
        self._dynamic_context_cache: Optional[str] = None  # Dynamic context for current turn
        self._last_user_message_for_context: Optional[str] = None  # Track for dynamic context
        self._last_assistant_response: Optional[str] = None  # Track last assistant response for context inference
        self._turn_count = 0  # Track turns for periodic context updates
        self._pending_dynamic_context: Optional[str] = None  # Context to inject on next turn

        # Session handle
        self._session = None
        self._session_cm = None
        self._is_connected = False

        # Callbacks
        self._on_audio: Optional[Callable[[bytes], None]] = None
        self._on_text: Optional[Callable[[str], None]] = None
        self._on_tool_call: Optional[Callable[[str, dict], str]] = None
        self._on_turn_complete: Optional[Callable[[], None]] = None

        # Agent bridge for ADK tool integration
        self._agent_bridge = AgentToolBridge(session_id=session_id, user_id=user_id, memory=memory)
        self.set_tool_callback(self._agent_bridge.handle_tool_call)

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

    def _load_agent_prompt(self, name: str) -> Optional[str]:
        """Load an agent prompt from the config/prompts directory.

        Args:
            name: Prompt file name (without .md extension)

        Returns:
            Prompt content or None if not found
        """
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / f"{name}.md"
        if prompt_path.exists():
            return prompt_path.read_text()
        return None

    async def _load_memory_context(self):
        """Load static memory context for this user (reflections, stats)."""
        if self.memory:
            try:
                self._memory_context = await self.memory.get_context_for_prompt()
            except Exception as e:
                print(f"Warning: Could not load memory context: {e}")
                self._memory_context = None

    async def _load_dynamic_context(self, user_message: str):
        """Load dynamic context based on current user message.
        
        Finds similar past interventions and caches them for injection into system prompt.
        This enables the agent to learn from past successful interactions in real-time.
        
        Args:
            user_message: Current user message to find similar interventions for
        """
        if not self.memory or not user_message or len(user_message.strip()) < 10:
            self._dynamic_context_cache = None
            return
        
        # Only update if message is different (avoid redundant searches)
        if self._last_user_message_for_context == user_message:
            return
        
        try:
            # Get dynamic context with similar interventions
            dynamic_context = await self.memory.get_dynamic_context(user_message, k=3)
            self._dynamic_context_cache = dynamic_context
            self._last_user_message_for_context = user_message
            
            # Log when dynamic context is found (for observability)
            if dynamic_context:
                print(f"📚 Found similar past interventions for: '{user_message[:50]}...'")
        except Exception as e:
            print(f"Warning: Could not load dynamic context: {e}")
            self._dynamic_context_cache = None

    async def _prepare_and_inject_dynamic_context(self):
        """Prepare and inject dynamic context based on recent conversation patterns.
        
        For audio streams, we infer user intent from conversation context
        and inject dynamic context to influence the next response.
        
        Strategy: 
        1. Use assistant responses and conversation patterns to infer user topics
        2. Find similar past interventions
        3. Inject as context that will influence the model's next response
        """
        if not self.memory or not self._session:
            return
        
        try:
            # Get recent conversation messages
            recent_messages = self.context.get_recent_messages(n=6)
            
            # Build query from conversation context
            query_parts = []
            
            # Look for user messages first (if any from text interactions)
            for msg in recent_messages:
                if msg["role"] == "user":
                    query_parts.append(msg["content"])
            
            # If no user messages, use assistant responses to infer topics
            # Assistant responses often reflect what the user was asking about
            if not query_parts and self._last_assistant_response:
                # Extract key phrases from assistant response
                assistant_text = self._last_assistant_response[:200]
                query_parts.append(assistant_text)
            
            # Also look for patterns in recent messages that suggest user needs
            if recent_messages:
                for msg in recent_messages[-2:]:
                    content = msg.get("content", "")
                    # Look for common patterns that indicate user needs
                    if any(keyword in content.lower() for keyword in 
                           ["focus", "overwhelm", "task", "help", "can't", "need", "stuck", "difficult"]):
                        query_parts.append(content)
            
            if not query_parts:
                return
            
            # Create query from most relevant context
            inferred_query = " ".join(query_parts[-1:])
            
            if len(inferred_query.strip()) < 10:
                return
            
            # Get dynamic context based on inferred query
            dynamic_context = await self.memory.get_dynamic_context(inferred_query, k=3)
            
            if not dynamic_context:
                return
            
            # Inject context immediately so it's ready for next user interaction
            # Format it as guidance that won't be confused with user input
            context_message = f"""<memory_context>
{dynamic_context}

Use these similar past successful interventions as reference for your responses.
</memory_context>"""
            
            # Send as a text message that provides context
            # This will be processed and influence the model's understanding
            await self._session.send_client_content(
                turns=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=context_message)],
                    )
                ],
                turn_complete=True,  # Complete turn so context is processed
            )
            
            print(f"📚 Injected dynamic context based on conversation pattern")
            
        except Exception as e:
            print(f"Warning: Could not inject dynamic context: {e}")

    def _build_system_instruction(self) -> str:
        """Build the system instruction with personalized context."""
        # Try to load the rich ADK main agent prompt
        base_instruction = self.config.system_instruction
        if not base_instruction:
            loaded_prompt = self._load_agent_prompt("main_agent")
            base_instruction = loaded_prompt if loaded_prompt else self._get_default_instruction()

        # Add static personalized context from memory (loaded during connect)
        if self._memory_context:
            base_instruction = f"{base_instruction}\n\n---\nPERSONALIZED CONTEXT FROM MEMORY:\n{self._memory_context}\n---"

        # Note: Dynamic context is injected per-message in send_text() since system instruction
        # is set once during connect(). This allows real-time context injection based on user messages.

        # Add personalized context from conversation context
        personalized = self.context.get_personalized_context()
        if personalized:
            return f"{base_instruction}\n\n---\nCURRENT SESSION CONTEXT:\n{personalized}\n---"

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
        """Build tool definitions for Gemini Live API.

        Includes all ADK agent tools for comprehensive support.
        """
        return [
            {
                "function_declarations": [
                    # === Feedback Loop Agent Tools ===
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
                        "name": "get_time_since_last_checkin",
                        "description": "Get time elapsed since the last check-in with the user",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "log_micro_win",
                        "description": "Log a micro-win to celebrate the user's progress",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "description": {
                                    "type": "string",
                                    "description": "What the user accomplished"
                                },
                                "category": {
                                    "type": "string",
                                    "description": "Category of win (task, emotional, focus, etc.)"
                                }
                            },
                            "required": ["description"]
                        }
                    },
                    # === Task Agent Tools ===
                    {
                        "name": "create_microsteps",
                        "description": "Break a task into micro-steps (2-5 minutes each)",
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
                        "name": "get_current_step",
                        "description": "Get the current step the user should work on",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "mark_step_complete",
                        "description": "Mark the current step as complete and move to next",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "get_current_time",
                        "description": "Get the current time for time-awareness",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "create_reminder",
                        "description": "Create a reminder for a task",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "task": {
                                    "type": "string",
                                    "description": "What to remind about"
                                },
                                "minutes": {
                                    "type": "integer",
                                    "description": "Minutes until reminder"
                                }
                            },
                            "required": ["task", "minutes"]
                        }
                    },
                    # === Emotional Agent Tools ===
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
                        "description": "Prompt a quick sensory environment check (noise, light, body)",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "grounding_exercise",
                        "description": "Start a grounding exercise to help with overwhelm or anxiety",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "technique": {
                                    "type": "string",
                                    "description": "Type of grounding: 5-4-3-2-1, body_scan, or simple"
                                }
                            }
                        }
                    },
                    {
                        "name": "suggest_break",
                        "description": "Suggest a structured break when user needs to reset",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "duration_minutes": {
                                    "type": "integer",
                                    "description": "Suggested break duration (2, 5, or longer)"
                                }
                            }
                        }
                    },
                    {
                        "name": "reframe_thought",
                        "description": "Provide a cognitive reframe for negative thought patterns",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "thought_type": {
                                    "type": "string",
                                    "description": "Type: perfectionism, catastrophizing, rsd, overwhelm, imposter"
                                }
                            },
                            "required": ["thought_type"]
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
            # Load memory context before building system instruction
            await self._load_memory_context()
            
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
        self._is_connected = False
        if self._session_cm:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except RuntimeError:
                # Ignore "asynchronous generator is already running" on interrupt
                pass
            self._session_cm = None
            self._session = None
        print("Disconnected from Gemini Live API")

    @property
    def is_connected(self) -> bool:
        """Check if connected to Gemini Live API."""
        return self._is_connected

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
        
        # Track user message for intervention context
        if self._agent_bridge:
            self._agent_bridge.set_last_user_message(text)

        # Load dynamic context based on current user message
        await self._load_dynamic_context(text)

        # Build message with dynamic context if available
        message_text = text
        if self._dynamic_context_cache:
            # Inject dynamic context as additional context for the agent
            # Format it clearly so the model understands it's reference material
            message_text = f"""Additional context from similar past successful interventions:
{self._dynamic_context_cache}

---
User message: {text}"""

        await self._session.send_client_content(
            turns=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=message_text)],
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
                                self._last_assistant_response = part.text
                                
                                # After assistant responds, prepare and inject dynamic context for next turn
                                # This works for audio streams by inferring user intent from conversation
                                if self.memory and self._turn_count > 0:
                                    # Prepare context asynchronously (non-blocking)
                                    asyncio.create_task(self._prepare_and_inject_dynamic_context())
                                
                                yield {"type": "text", "data": part.text}

                    # Turn complete
                    if content.turn_complete:
                        self._turn_count += 1
                        
                        if self._on_turn_complete:
                            self._on_turn_complete()
                        yield {"type": "turn_complete", "data": None}

                # Tool call
                elif response.tool_call:
                    tool_call = response.tool_call
                    for fc in tool_call.function_calls:
                        result = await self._handle_tool_call(fc.name, fc.args)
                        yield {"type": "tool_call", "name": fc.name, "result": result}
                        
                        # Record intervention in memory if available
                        if self.memory and self._agent_bridge:
                            # The agent bridge will handle recording
                            pass
                        yield {"type": "tool_call", "name": fc.name, "args": fc.args, "result": result}

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
        # Use external callback if set (now async)
        if self._on_tool_call:
            # Check if callback is async
            import asyncio
            import inspect
            if inspect.iscoroutinefunction(self._on_tool_call):
                return await self._on_tool_call(name, args)
            else:
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
        # Route to AgentToolBridge (always set in __init__)
        return self._on_tool_call(name, args)

    def get_session_summary(self) -> dict:
        """Get summary of the current session."""
        return self.session_state.get_session_summary()

    def get_transcript(self) -> list:
        """Get the conversation transcript."""
        return self.context.get_transcript()
