"""Entry point for the sam2-voice bot.

This starts the Pipecat voice pipeline with Daily.co WebRTC
and connects it to the Google ADK agent system.

Usage:
    python main.py                    # Auto-detect transport
    python main.py --local            # Use local audio
    python main.py --room URL         # Use specific Daily room
"""

import argparse
import asyncio

from dotenv import load_dotenv

from voice.bot import run_bot, main as bot_main


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Sam2 Voice - ADHD/Autism Support Voice Agent"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local audio instead of Daily WebRTC"
    )
    parser.add_argument(
        "--room",
        type=str,
        help="Daily.co room URL to join"
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default="default",
        help="Session identifier for state management"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default="user",
        help="User identifier"
    )
    return parser.parse_args()


async def main():
    """Main entry point with argument parsing."""
    load_dotenv()
    args = parse_args()

    if args.local:
        transport_type = "local"
    else:
        transport_type = "daily"

    await run_bot(
        transport_type=transport_type,
        room_url=args.room,
        session_id=args.session_id,
        user_id=args.user_id,
    )


if __name__ == "__main__":
    asyncio.run(main())
