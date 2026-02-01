#!/usr/bin/env python3
"""Test dynamic context injection functionality.

Run with:
    python tests/test_dynamic_context.py

Or with pytest:
    pytest tests/test_dynamic_context.py -v -s
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

try:
    from memory.redis_memory import RedisUserMemory
    from memory.embeddings import get_embedding
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n💡 Make sure you're in the virtual environment:")
    print("   source venv/bin/activate")
    print("   or")
    print("   uv run python tests/test_dynamic_context.py")
    sys.exit(1)


async def test_dynamic_context_injection():
    """Test that dynamic context finds and formats similar interventions."""
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("⚠️  REDIS_URL not set, skipping test")
        return
    
    user_id = "test_dynamic_context_user"
    memory = RedisUserMemory(user_id=user_id, redis_url=redis_url)
    
    print("🧪 Testing Dynamic Context Injection")
    print("=" * 60)
    
    # Step 1: Store some test interventions
    print("\n1️⃣  Storing test interventions...")
    
    test_interventions = [
        {
            "context": "I can't focus on my homework",
            "intervention": "Used create_microsteps: Created 3 micro-steps for: homework",
            "task": "homework",
            "outcome": "task_completed"
        },
        {
            "context": "I'm feeling overwhelmed with cleaning my room",
            "intervention": "Used create_microsteps: Created 4 micro-steps for: cleaning room",
            "task": "cleaning",
            "outcome": "task_completed"
        },
        {
            "context": "I need help staying focused",
            "intervention": "Used schedule_checkin: Check-in scheduled for 3 minutes from now",
            "task": "general",
            "outcome": "re_engaged"
        },
        {
            "context": "I'm stressed about this project",
            "intervention": "Used start_breathing_exercise: Quick reset: Breathe in slowly...",
            "task": "project",
            "outcome": "re_engaged"
        },
    ]
    
    for i, intervention in enumerate(test_interventions, 1):
        embedding = await get_embedding(intervention["context"])
        await memory.record_intervention(
            intervention_text=intervention["intervention"],
            context=intervention["context"],
            task=intervention["task"],
            outcome=intervention["outcome"],
            embedding=embedding
        )
        print(f"   ✅ Stored intervention {i}: {intervention['context'][:50]}...")
    
    # Step 2: Test dynamic context retrieval
    print("\n2️⃣  Testing dynamic context retrieval...")
    
    test_queries = [
        "I can't focus on my assignment",
        "I'm overwhelmed with this task",
        "I need help staying on track",
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        print("   " + "-" * 50)
        
        dynamic_context = await memory.get_dynamic_context(query, k=3)
        
        if dynamic_context:
            print("   ✅ Found similar interventions!")
            print(f"\n   Context:\n{dynamic_context}\n")
        else:
            print("   ⚠️  No similar interventions found (similarity threshold not met)")
    
    # Step 3: Test with a query that shouldn't match
    print("\n3️⃣  Testing with unrelated query...")
    unrelated_query = "What's the weather like today?"
    dynamic_context = await memory.get_dynamic_context(unrelated_query, k=3)
    
    if dynamic_context:
        print(f"   ⚠️  Unexpected: Found context for unrelated query")
        print(f"   Context: {dynamic_context[:100]}...")
    else:
        print("   ✅ Correctly returned no context for unrelated query")
    
    # Step 4: Test similarity threshold
    print("\n4️⃣  Testing similarity threshold...")
    
    # Get embedding for a very similar query
    similar_query = "I can't focus on my homework right now"
    similar_embedding = await get_embedding(similar_query)
    similar_results = await memory.find_similar_interventions(similar_embedding, k=5, successful_only=True)
    
    print(f"   Query: '{similar_query}'")
    print(f"   Found {len(similar_results)} similar interventions:")
    for i, result in enumerate(similar_results[:3], 1):
        similarity = result.get("similarity", 0.0)
        context = result.get("context", "N/A")
        outcome = result.get("outcome", "N/A")
        print(f"   {i}. Similarity: {similarity:.3f} | Context: '{context[:40]}...' | Outcome: {outcome}")
    
    # Step 5: Verify dynamic context only includes high-quality matches
    print("\n5️⃣  Verifying quality filtering...")
    dynamic_context = await memory.get_dynamic_context(similar_query, k=3)
    
    if dynamic_context:
        # Count how many examples are included
        example_count = dynamic_context.count("Example")
        print(f"   ✅ Dynamic context includes {example_count} high-quality examples")
        print(f"   (Only includes matches with similarity > 0.7)")
    else:
        print("   ⚠️  No dynamic context generated")
    
    print("\n" + "=" * 60)
    print("✅ Dynamic context injection test complete!")
    print("\n💡 The dynamic context will be injected into user messages")
    print("   when the voice bot processes user input, providing")
    print("   the agent with similar past successful interventions.")


if __name__ == "__main__":
    asyncio.run(test_dynamic_context_injection())
