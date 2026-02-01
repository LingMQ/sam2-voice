"""Evaluation dataset for sam2-voice bot."""

# Sample evaluation dataset covering different scenarios
EVAL_DATASET = [
    # Task breakdown scenarios
    {
        "user_input": "I need to clean my room but I don't know where to start",
        "context": "User has ADHD and struggles with task initiation",
        "expected_tool": "create_microsteps",
        "category": "task_breakdown",
    },
    {
        "user_input": "I have to write a report for work",
        "context": "User often gets overwhelmed by large tasks",
        "expected_tool": "create_microsteps",
        "category": "task_breakdown",
    },

    # Progress tracking scenarios
    {
        "user_input": "I just finished organizing my desk!",
        "context": "User completed first micro-step",
        "expected_tool": "log_win",
        "category": "progress",
    },
    {
        "user_input": "Done with that step",
        "context": "User is working through micro-steps",
        "expected_tool": "mark_step_complete",
        "category": "progress",
    },

    # Emotional regulation scenarios
    {
        "user_input": "I'm feeling really overwhelmed right now",
        "context": "User showing signs of distress",
        "expected_tool": "start_breathing_exercise",
        "category": "emotional",
    },
    {
        "user_input": "Everything feels too loud and bright",
        "context": "User experiencing sensory overload",
        "expected_tool": "sensory_check",
        "category": "emotional",
    },
    {
        "user_input": "I can't focus, my mind is racing",
        "context": "User having difficulty with attention",
        "expected_tool": "start_breathing_exercise",
        "category": "emotional",
    },

    # Check-in scenarios
    {
        "user_input": "I'm going to start working on my project now",
        "context": "User beginning a task",
        "expected_tool": "schedule_checkin",
        "category": "checkin",
    },
    {
        "user_input": "Can you remind me to check back in a few minutes?",
        "context": "User explicitly requesting check-in",
        "expected_tool": "schedule_checkin",
        "category": "checkin",
    },

    # General support scenarios (no specific tool expected)
    {
        "user_input": "I'm having a good day today",
        "context": "User sharing positive update",
        "expected_tool": None,
        "category": "general",
    },
    {
        "user_input": "Thanks for helping me",
        "context": "User expressing gratitude",
        "expected_tool": None,
        "category": "general",
    },
    {
        "user_input": "I got distracted again",
        "context": "User acknowledging distraction",
        "expected_tool": None,
        "category": "general",
    },

    # Edge cases
    {
        "user_input": "What can you help me with?",
        "context": "New user asking about capabilities",
        "expected_tool": None,
        "category": "onboarding",
    },
    {
        "user_input": "I don't want to do anything right now",
        "context": "User showing low motivation",
        "expected_tool": None,
        "category": "emotional",
    },
    {
        "user_input": "I keep failing at everything",
        "context": "User expressing negative self-talk",
        "expected_tool": None,
        "category": "emotional",
    },
]


def get_dataset() -> list[dict]:
    """Get the evaluation dataset."""
    return EVAL_DATASET


def get_dataset_by_category(category: str) -> list[dict]:
    """Get evaluation examples filtered by category."""
    return [ex for ex in EVAL_DATASET if ex["category"] == category]
