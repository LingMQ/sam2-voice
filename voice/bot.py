"""Main voice bot using Gemini Live API."""

import asyncio
import os
import signal
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
    ):
        self.session_id = session_id
        self.user_id = user_id

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

    async def start(self):
        """Start the voice bot."""
        print("Starting voice bot...")

        # Connect to Gemini Live API
        if not await self.client.connect():
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

    async def stop(self):
        """Stop the voice bot."""
        print("\nStopping voice bot...")
        self._is_running = False

        if self.audio_capture:
            self.audio_capture.terminate()
        if self.audio_playback:
            self.audio_playback.terminate()

        await self.client.disconnect()

        # Print session summary
        summary = self.client.get_session_summary()
        print(f"\nSession summary: {summary}")

    def _on_audio_response(self, audio_data: bytes):
        """Handle audio response from Gemini."""
        self._is_model_speaking = True
        if self.audio_playback:
            self.audio_playback.play(audio_data)

    def _on_text_response(self, text: str):
        """Handle text response from Gemini."""
        print(f"Assistant: {text}")

    def _on_turn_complete(self):
        """Handle turn completion."""
        self._is_model_speaking = False

    async def run(self):
        """Main run loop."""
        await self.start()

        # Start receive task
        receive_task = asyncio.create_task(self._receive_loop())

        # Main audio capture loop
        try:
            while self._is_running:
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


async def run_bot(
    session_id: str = "default",
    user_id: str = "user",
    voice: str = "Puck",
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
