"""Main voice bot entry point."""

import asyncio
import os
import time
from typing import Optional

import aiohttp
from dotenv import load_dotenv

from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams

from voice.pipeline import create_pipeline
from voice.handlers import VoiceEventHandlers


async def create_daily_room() -> str:
    """Create a temporary Daily.co room for testing.

    Returns:
        The room URL to join
    """
    api_key = os.getenv("DAILY_API_KEY")
    if not api_key:
        raise ValueError("DAILY_API_KEY environment variable is required")

    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {api_key}"}
        room_config = {
            "properties": {
                "exp": int(time.time()) + 3600,  # Expires in 1 hour
                "enable_chat": False,
                "enable_screenshare": False,
                "start_video_off": True,
                "start_audio_off": False,
            }
        }

        async with session.post(
            "https://api.daily.co/v1/rooms",
            headers=headers,
            json=room_config,
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise RuntimeError(f"Failed to create Daily room: {error}")

            data = await resp.json()
            return data["url"]


async def run_bot(
    transport_type: str = "daily",
    room_url: Optional[str] = None,
    session_id: str = "default",
    user_id: str = "user",
):
    """Run the voice bot.

    Args:
        transport_type: "daily" for WebRTC or "local" for local audio
        room_url: Optional Daily.co room URL (creates one if not provided)
        session_id: Session identifier
        user_id: User identifier
    """
    # Handle Daily room creation
    if transport_type == "daily":
        if not room_url:
            room_url = os.getenv("DAILY_ROOM_URL")

        if not room_url:
            print("Creating temporary Daily room...")
            room_url = await create_daily_room()

        print(f"\n{'='*60}")
        print(f"Voice bot is ready!")
        print(f"Join the room: {room_url}")
        print(f"{'='*60}\n")

    # Create the voice pipeline
    pipeline, transport, adk_processor = await create_pipeline(
        transport_type=transport_type,
        room_url=room_url,
        session_id=session_id,
        user_id=user_id,
    )

    # Create pipeline task with interruption support
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
        )
    )

    # Set up event handlers
    handlers = VoiceEventHandlers(task, adk_processor)

    # Optional: Set up session end callback for reflection
    async def on_session_end(summary, transcript):
        print(f"\nSession ended. Summary: {summary}")
        # Here you could trigger reflection generation
        # from memory.reflection import generate_session_reflection
        # await generate_session_reflection(...)

    handlers.set_session_end_callback(on_session_end)
    handlers.register_handlers(transport)

    # Run the pipeline
    runner = PipelineRunner()

    print("Waiting for participants..." if transport_type == "daily" else "Starting local audio...")

    try:
        await runner.run(task)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Bot stopped.")

        # Print session summary
        if adk_processor:
            summary = adk_processor.get_session_summary()
            print(f"\nSession summary: {summary}")


async def main():
    """Main entry point - validates config and runs the bot."""
    load_dotenv()

    # Check for required environment variables
    required_vars = ["DEEPGRAM_API_KEY", "CARTESIA_API_KEY", "GOOGLE_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your API keys.")
        return

    # Determine transport type
    if os.getenv("DAILY_API_KEY"):
        transport_type = "daily"
    else:
        print("No DAILY_API_KEY found, using local audio transport")
        transport_type = "local"

    await run_bot(transport_type=transport_type)


if __name__ == "__main__":
    asyncio.run(main())
