"""Main voice bot using Gemini Live API."""

import asyncio
import os
import signal
import time
from typing import Optional

import weave
import os
from dotenv import load_dotenv

from voice.gemini_live import GeminiLiveClient, GeminiLiveConfig
from voice.audio import AudioCapture, AudioPlayback, VoiceActivityDetector
from memory.redis_memory import RedisUserMemory
from memory.reflection import generate_reflection
from observability.session_tracker import SessionTracker


class VoiceBot:
    """Voice bot using Gemini Live API for real-time conversations."""

    def __init__(
        self,
        session_id: str = "default",
        user_id: str = "user",
        voice: str = "Puck",
        max_turns: Optional[int] = None,
        on_text: Optional[callable] = None,
        on_status: Optional[callable] = None,
        on_error: Optional[callable] = None,
        on_turn_complete: Optional[callable] = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.max_turns = max_turns
        self._on_text_cb = on_text
        self._on_status_cb = on_status
        self._on_error_cb = on_error
        self._on_turn_complete_cb = on_turn_complete

        # Initialize memory if Redis URL is available
        self.memory = None
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                self.memory = RedisUserMemory(user_id=user_id, redis_url=redis_url)
                print(f"✅ Memory system initialized for user: {user_id}")
            except Exception as e:
                print(f"⚠️  Warning: Could not initialize memory system: {e}")
                print("   Continuing without memory...")

        # Gemini Live client
        config = GeminiLiveConfig(
            voice=voice,
            sample_rate=16000,
        )
        self.client = GeminiLiveClient(
            config=config,
            session_id=session_id,
            user_id=user_id,
            memory=self.memory,  # Pass memory to client
        )

        # Session tracker for Weave observability
        self.session_tracker = SessionTracker(session_id=session_id, user_id=user_id)

        # Audio components
        self.audio_capture: Optional[AudioCapture] = None
        self.audio_playback: Optional[AudioPlayback] = None
        self.vad: Optional[VoiceActivityDetector] = None

        # State
        self._is_running = False
        self._is_model_speaking = False
        self._turns_completed = 0
        self._last_response_at = 0.0

    @weave.op
    async def start(self):
        """Start the voice bot."""
        print("Starting voice bot...")
        if self._on_status_cb:
            self._on_status_cb("starting")

        # Connect to Gemini Live API
        if not await self.client.connect():
            if self._on_error_cb:
                self._on_error_cb("Failed to connect to Gemini Live API")
            raise RuntimeError("Failed to connect to Gemini Live API")

        # Initialize audio components
        self.audio_capture = AudioCapture(sample_rate=16000)
        self.audio_playback = AudioPlayback(sample_rate=24000)  # Gemini outputs 24kHz
        self.vad = VoiceActivityDetector()

        # Set up callbacks
        self.client.set_audio_callback(self._on_audio_response)
        self.client.set_text_callback(self._on_text_response)
        self.client.set_turn_complete_callback(self._on_turn_complete)

        # Start audio
        self.audio_capture.start()
        self.audio_playback.start()

        self._is_running = True
        print("\nVoice bot ready! Start speaking...")
        print("Press Ctrl+C to stop.\n")
        if self._on_status_cb:
            self._on_status_cb("ready")

    @weave.op
    async def stop(self):
        """Stop the voice bot."""
        print("\nStopping voice bot...")
        if self._on_status_cb:
            self._on_status_cb("stopping")
        self._is_running = False

        if self.audio_capture:
            self.audio_capture.terminate()
        if self.audio_playback:
            self.audio_playback.terminate()

        # Generate end-of-session reflection if memory is available
        if self.memory:
            try:
                print("\n📝 Generating session reflection...")
                transcript = self.client.get_transcript()
                if transcript:
                    reflection = await generate_reflection(self.memory, transcript)
                    print(f"💡 Insight: {reflection}")
            except Exception as e:
                print(f"⚠️  Reflection generation failed: {e}")

        await self.client.disconnect()

        # Log session summary to Weave
        weave_summary = self.session_tracker.log_session_summary()
        effectiveness = self.session_tracker.get_effectiveness_score()
        print(f"\n📊 Session Summary:")
        print(f"   Duration: {weave_summary['duration_minutes']:.1f} minutes")
        print(f"   Tool calls: {weave_summary['total_tool_calls']}")
        print(f"   Steps completed: {weave_summary['steps_completed']}")
        print(f"   Tasks completed: {weave_summary['tasks_completed']}")
        print(f"   Effectiveness: {effectiveness:.0%}")

        # Also print basic session summary
        summary = self.client.get_session_summary()
        if self._on_status_cb:
            self._on_status_cb("stopped")

    def _on_audio_response(self, audio_data: bytes):
        """Handle audio response from Gemini."""
        self._is_model_speaking = True
        self._last_response_at = time.monotonic()
        if self.audio_playback:
            self.audio_playback.play(audio_data)

    def _on_text_response(self, text: str):
        """Handle text response from Gemini."""
        print(f"Assistant: {text}")
        self._last_response_at = time.monotonic()
        if self._on_text_cb:
            self._on_text_cb(text)

    def _on_turn_complete(self):
        """Handle turn completion."""
        self._is_model_speaking = False
        self._last_response_at = time.monotonic()
        if self._on_turn_complete_cb:
            self._on_turn_complete_cb()
        if self.max_turns is not None:
            self._turns_completed += 1
            if self._turns_completed >= self.max_turns:
                self._is_running = False

    @weave.op
    async def run(self):
        """Main run loop."""
        await self.start()

        # Start receive task
        receive_task = asyncio.create_task(self._receive_loop())

        # Main audio capture loop
        try:
            while self._is_running:
                if self._is_model_speaking and self._last_response_at:
                    if time.monotonic() - self._last_response_at > 4.0:
                        # If the model never sends turn_complete, unlock input.
                        self._is_model_speaking = False

                # Read audio from microphone
                audio_data = await self.audio_capture.read_audio_blocking(timeout=0.05)

                if audio_data:
                    # Check VAD
                    is_speaking = self.vad.process(audio_data)

                    # Only send audio when user is speaking and model is not
                    if is_speaking and not self._is_model_speaking:
                        await self.client.send_audio(audio_data)

                await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            pass
        finally:
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass
            await self.stop()

    async def _receive_loop(self):
        """Background task for receiving responses."""
        try:
            async for response in self.client.receive_responses():
                if response["type"] == "tool_call":
                    print(f"Tool called: {response['name']} -> {response['result']}")
                    # Record tool call for session tracking
                    self.session_tracker.record_tool_call(
                        tool_name=response['name'],
                        args=response.get('args', {}),
                        result=response['result'],
                    )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Receive error: {e}")
            if self._on_error_cb:
                self._on_error_cb(str(e))


@weave.op
async def run_bot(
    session_id: str = "default",
    user_id: str = "user",
    voice: str = "Puck",
    max_turns: Optional[int] = None,
):
    """Run the voice bot.

    Args:
        session_id: Session identifier
        user_id: User identifier
        voice: Gemini voice to use (Puck, Charon, Kore, Fenrir, Aoede)
    """
    bot = VoiceBot(
        session_id=session_id,
        user_id=user_id,
        voice=voice,
        max_turns=max_turns,
    )

    # Handle Ctrl+C gracefully
    loop = asyncio.get_event_loop()

    def signal_handler():
        print("\nReceived interrupt signal...")
        asyncio.create_task(bot.stop())

    loop.add_signal_handler(signal.SIGINT, signal_handler)

    try:
        await bot.run()
    except Exception as e:
        print(f"Error: {e}")
        if bot._on_error_cb:
            bot._on_error_cb(str(e))
        await bot.stop()


async def main():
    """Main entry point - validates config and runs the bot."""
    load_dotenv()

    # Check for required environment variables
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY environment variable is required")
        print("Get your API key from: https://aistudio.google.com")
        return

    print("=" * 60)
    print("Sam2 Voice - ADHD/Autism Support Voice Agent")
    print("Using Gemini Live API")
    print("=" * 60)

    await run_bot()


if __name__ == "__main__":
    asyncio.run(main())
