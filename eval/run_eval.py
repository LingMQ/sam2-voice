"""Run evaluation for sam2-voice bot using Weave.

Usage:
    python -m eval.run_eval                    # Run full evaluation
    python -m eval.run_eval --category task    # Run specific category
"""

import argparse
import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import weave
from dotenv import load_dotenv

from eval.model import Sam2VoiceModel
from eval.scorers import (
    brevity_scorer,
    supportiveness_scorer,
    tool_usage_scorer,
    response_quality_scorer,
)
from eval.dataset import get_dataset, get_dataset_by_category


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run sam2-voice evaluation with Weave"
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        choices=["task_breakdown", "progress", "emotional", "checkin", "general", "onboarding"],
        help="Filter evaluation by category",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-flash-preview-05-20",
        help="Gemini model to use for evaluation",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="sam2-voice-eval",
        help="Name for the evaluation run",
    )
    return parser.parse_args()


async def main():
    """Run the evaluation."""
    load_dotenv()

    # Check for required API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY environment variable is required")
        print("Get your API key from: https://aistudio.google.com")
        return

    args = parse_args()

    # Initialize Weave
    weave.init("lingmiaojiayou-/hackathon")

    print("=" * 60)
    print("Sam2 Voice - Evaluation Runner")
    print("Using Weave for observability and evaluation")
    print("=" * 60)

    # Get dataset
    if args.category:
        dataset_list = get_dataset_by_category(args.category)
        print(f"\nRunning evaluation for category: {args.category}")
    else:
        dataset_list = get_dataset()
        print("\nRunning full evaluation")

    print(f"Dataset size: {len(dataset_list)} examples")

    # Create Weave dataset
    dataset = weave.Dataset(
        name="sam2-voice-eval-dataset",
        rows=dataset_list,
    )

    # Create model
    model = Sam2VoiceModel(model_name=args.model)
    print(f"Model: {args.model}")

    # Create evaluation with scorers
    evaluation = weave.Evaluation(
        name=args.name,
        dataset=dataset,
        scorers=[
            brevity_scorer,
            supportiveness_scorer,
            tool_usage_scorer,
            response_quality_scorer,
        ],
    )

    print("\nStarting evaluation...")
    print("-" * 60)

    # Run evaluation
    results = await evaluation.evaluate(model)

    print("-" * 60)
    print("\nEvaluation complete!")
    print(f"View results at: https://wandb.ai/lingmiaojiayou-/hackathon")

    return results


if __name__ == "__main__":
    asyncio.run(main())
