"""Main voice bot using Gemini Live API."""

import asyncio
import os
import signal
import time
from typing import Optional

from dotenv import load_dotenv

from voice.gemini_live import GeminiLiveClient, GeminiLiveConfig
from voice.audio import AudioCapture, AudioPlayback, VoiceActivityDetector


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

        # Gemini Live client
        config = GeminiLiveConfig(
            voice=voice,
            sample_rate=16000,
        )
        self.client = GeminiLiveClient(
            config=config,
            session_id=session_id,
            user_id=user_id,
        )

        # Audio components
        self.audio_capture: Optional[AudioCapture] = None
        self.audio_playback: Optional[AudioPlayback] = None
        self.vad: Optional[VoiceActivityDetector] = None

        # State
        self._is_running = False
        self._is_model_speaking = False
        self._turns_completed = 0
        self._last_response_at = 0.0

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

        await self.client.disconnect()

        # Print session summary
        summary = self.client.get_session_summary()
        print(f"\nSession summary: {summary}")
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
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Receive error: {e}")
            if self._on_error_cb:
                self._on_error_cb(str(e))


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
