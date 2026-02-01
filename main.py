"""Entry point for the sam2-voice bot.

This starts the Gemini Live API voice bot for real-time
audio conversations with ADHD/autism support.

Usage:
    python main.py                    # Default settings
    python main.py --voice Kore       # Use different voice
    python main.py --session-id test  # Custom session ID
"""

import argparse
import asyncio

import weave
from dotenv import load_dotenv
from voice.bot import main as bot_main, run_bot


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Sam2 Voice - ADHD/Autism Support Voice Agent (Gemini Live API)"
    )
    parser.add_argument(
        "--voice",
        type=str,
        default="Puck",
        choices=["Puck", "Charon", "Kore", "Fenrir", "Aoede"],
        help="Gemini voice to use (default: Puck)",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default="default",
        help="Session identifier for state management",
    )
    parser.add_argument("--user-id", type=str, default="user", help="User identifier")
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Stop after N model turns (use 1 for single-turn mode)",
    )
    return parser.parse_args()


async def main():
    """Main entry point with argument parsing."""
    load_dotenv()

    # Initialize Weave for observability (optional - skip if not logged in)
    try:
        weave.init('lingmiaojiayou-/hackathon')
    except Exception as e:
        print(f"Weave initialization skipped: {e}")

    args = parse_args()

    await run_bot(
        session_id=args.session_id,
        user_id=args.user_id,
        voice=args.voice,
        max_turns=args.max_turns,
    )


if __name__ == "__main__":
    asyncio.run(main())
