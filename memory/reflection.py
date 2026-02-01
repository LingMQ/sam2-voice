"""End-of-session reflection generation."""

import os
from typing import List, Dict
from google import genai
import weave

from memory.redis_memory import RedisUserMemory

# Initialize Gemini client
_client = None


def _get_client():
    """Get or create Gemini client."""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        _client = genai.Client(api_key=api_key)
    return _client


@weave.op()
async def generate_reflection(
    memory: RedisUserMemory,
    transcript: List[Dict]
) -> str:
    """Generate reflection at end of session.
    
    Args:
        memory: RedisUserMemory instance
        transcript: Conversation transcript (list of message dicts)
        
    Returns:
        Generated insight string
    """
    client = _get_client()

    # Format transcript (last 20 messages)
    transcript_messages = transcript[-20:] if len(transcript) > 20 else transcript
    transcript_str = "\n".join([
        f"{msg.get('role', 'unknown').upper()}: {msg.get('content', '')}"
        for msg in transcript_messages
    ])

    # Get previous insights for context
    previous_insights = memory.get_recent_reflections(3)
    previous_str = "\n".join(f"- {i}" for i in previous_insights) if previous_insights else "None yet"

    prompt = f"""Analyze this support session for someone with ADHD/autism.

SESSION TRANSCRIPT:
{transcript_str}

PREVIOUS INSIGHTS ABOUT THIS USER:
{previous_str}

Generate ONE brief insight (1-2 sentences) about what we learned from this session.
Focus on:
- What intervention styles worked or didn't work
- User's preferences or patterns you noticed
- What to do differently next time

Keep it specific and actionable."""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        insight = response.text.strip()

        # Store the reflection
        memory.store_reflection(
            insight=insight,
            session_summary=transcript_str
        )

        return insight

    except Exception as e:
        print(f"Error generating reflection: {e}")
        # Return a default insight if generation fails
        return "Session completed. Continue monitoring user patterns and preferences."
