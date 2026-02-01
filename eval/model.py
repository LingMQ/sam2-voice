"""Weave Model wrapper for sam2-voice evaluation."""

import os
from textwrap import dedent

import weave
from google import genai
from google.genai import types


class Sam2VoiceModel(weave.Model):
    """Weave Model wrapper for evaluating the sam2-voice bot.

    This model uses the Gemini API in text mode for evaluation,
    simulating the voice bot's responses to user inputs.
    """

    model_name: str = "gemini-2.0-flash"
    voice: str = "Puck"
    system_prompt: str = dedent("""
        You are a supportive voice assistant for people with ADHD and autism.

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

        Never be preachy or give long explanations. Quick, supportive responses only.

        When you want to use a tool, respond with the tool name in brackets like:
        [TOOL: tool_name] followed by your response.

        Available tools: schedule_checkin, create_microsteps, mark_step_complete,
        log_win, start_breathing_exercise, sensory_check
    """).strip()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    @weave.op
    def predict(self, user_input: str, context: str = "") -> dict:
        """Generate a response to user input.

        Args:
            user_input: The user's message
            context: Optional context about the user's current state/task

        Returns:
            dict with 'response', 'tool_used', and 'tool_name' keys
        """
        messages = []

        if context:
            full_input = f"Context: {context}\n\nUser says: {user_input}"
        else:
            full_input = user_input

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=[full_input],
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                temperature=0.7,
                max_output_tokens=150,
            ),
        )

        response_text = response.text if response.text else ""

        # Parse tool usage from response
        tool_used = "[TOOL:" in response_text
        tool_name = None
        if tool_used:
            import re
            tool_match = re.search(r"\[TOOL:\s*(\w+)\]", response_text)
            if tool_match:
                tool_name = tool_match.group(1)

        return {
            "response": response_text,
            "tool_used": tool_used,
            "tool_name": tool_name,
        }
