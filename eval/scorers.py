"""Scorer functions for evaluating sam2-voice responses."""

import re
import weave


@weave.op
def brevity_scorer(output: dict) -> dict:
    """Score response brevity (should be 1-2 sentences for voice).

    Args:
        output: Model output dict with 'response' key

    Returns:
        dict with 'brevity_score' (0-1) and 'word_count'
    """
    response = output.get("response", "")

    # Count words
    words = len(response.split())

    # Count sentences (rough approximation)
    sentences = len(re.findall(r'[.!?]+', response)) or 1

    # Ideal: 10-30 words, 1-2 sentences
    # Score decreases for longer responses
    if words <= 30 and sentences <= 2:
        score = 1.0
    elif words <= 50 and sentences <= 3:
        score = 0.7
    elif words <= 80:
        score = 0.4
    else:
        score = 0.2

    return {
        "brevity_score": score,
        "word_count": words,
        "sentence_count": sentences,
    }


@weave.op
def supportiveness_scorer(output: dict) -> dict:
    """Score how supportive and encouraging the response is.

    Args:
        output: Model output dict with 'response' key

    Returns:
        dict with 'supportiveness_score' (0-1) and details
    """
    response = output.get("response", "").lower()

    # Positive indicators
    positive_phrases = [
        "great", "good job", "well done", "nice", "awesome", "excellent",
        "you've got this", "you can do it", "proud", "amazing",
        "that's okay", "it's okay", "no worries", "let's", "we can",
        "together", "help", "support", "understand", "i hear you",
    ]

    # Negative indicators (judgmental, dismissive)
    negative_phrases = [
        "you should", "you need to", "you must", "just do it",
        "stop", "don't", "wrong", "bad", "failure", "lazy",
        "obviously", "simply", "just", "easy",
    ]

    positive_count = sum(1 for phrase in positive_phrases if phrase in response)
    negative_count = sum(1 for phrase in negative_phrases if phrase in response)

    # Calculate score
    if negative_count > 0:
        score = max(0.2, 0.5 - (negative_count * 0.1))
    elif positive_count >= 2:
        score = 1.0
    elif positive_count == 1:
        score = 0.8
    else:
        score = 0.6  # Neutral is okay

    return {
        "supportiveness_score": score,
        "positive_indicators": positive_count,
        "negative_indicators": negative_count,
    }


@weave.op
def tool_usage_scorer(output: dict, expected_tool: str = None) -> dict:
    """Score appropriate tool usage.

    Args:
        output: Model output dict with 'tool_used' and 'tool_name' keys
        expected_tool: Expected tool name (optional)

    Returns:
        dict with 'tool_score' and details
    """
    tool_used = output.get("tool_used", False)
    tool_name = output.get("tool_name")

    if expected_tool:
        # If we expect a specific tool
        if tool_name == expected_tool:
            score = 1.0
            correct = True
        elif tool_used:
            score = 0.5  # Used a tool, but wrong one
            correct = False
        else:
            score = 0.0  # Should have used a tool but didn't
            correct = False
    else:
        # No specific expectation, just check if tool usage makes sense
        score = 0.7 if tool_used else 0.5
        correct = None

    return {
        "tool_score": score,
        "tool_used": tool_used,
        "tool_name": tool_name,
        "expected_tool": expected_tool,
        "correct_tool": correct,
    }


@weave.op
def response_quality_scorer(
    user_input: str,
    output: dict,
    expected_tool: str = None,
) -> dict:
    """Combined quality score for sam2-voice responses.

    Args:
        user_input: Original user input
        output: Model output dict
        expected_tool: Expected tool to be used (optional)

    Returns:
        dict with overall 'quality_score' and component scores
    """
    brevity = brevity_scorer(output)
    supportiveness = supportiveness_scorer(output)
    tool = tool_usage_scorer(output, expected_tool)

    # Weighted average
    weights = {
        "brevity": 0.3,
        "supportiveness": 0.4,
        "tool": 0.3,
    }

    quality_score = (
        brevity["brevity_score"] * weights["brevity"] +
        supportiveness["supportiveness_score"] * weights["supportiveness"] +
        tool["tool_score"] * weights["tool"]
    )

    return {
        "quality_score": quality_score,
        "brevity": brevity,
        "supportiveness": supportiveness,
        "tool_usage": tool,
    }
