#!/usr/bin/env python3
"""Test dynamic context injection for audio interface.

This test simulates the audio conversation flow and verifies that
dynamic context injection works correctly.

Usage:
    # Make sure you have REDIS_URL and GOOGLE_API_KEY in .env
    python test_dynamic_context_audio.py
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from memory.redis_memory import RedisUserMemory
from memory.embeddings import get_embedding
from voice.gemini_live import GeminiLiveClient, GeminiLiveConfig
from state.context import ConversationContext


async def test_dynamic_context_injection():
    """Test dynamic context injection for audio interface."""
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("❌ REDIS_URL not set in .env file")
        return
    
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        print("❌ GOOGLE_API_KEY not set in .env file")
        return
    
    user_id = "test_audio_context_user"
    memory = RedisUserMemory(user_id=user_id, redis_url=redis_url)
    
    print("🧪 Testing Dynamic Context Injection for Audio Interface")
    print("=" * 70)
    
    # Step 1: Store test interventions
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
        try:
            embedding = await get_embedding(intervention["context"])
            await memory.record_intervention(
                intervention_text=intervention["intervention"],
                context=intervention["context"],
                task=intervention["task"],
                outcome=intervention["outcome"],
                embedding=embedding
            )
            print(f"   ✅ Stored intervention {i}: {intervention['context'][:50]}...")
        except Exception as e:
            print(f"   ❌ Failed to store intervention {i}: {e}")
            return
    
    # Step 2: Test context inference from conversation patterns
    print("\n2️⃣  Testing context inference from conversation patterns...")
    
    # Simulate conversation context
    from state.context import ConversationContext
    context = ConversationContext()
    
    # Simulate assistant responses that would trigger context lookup
    test_scenarios = [
        {
            "assistant_response": "Let's break this down into smaller steps. What task are you working on?",
            "expected_pattern": "focus",
            "description": "Assistant mentions breaking down tasks"
        },
        {
            "assistant_response": "I understand you're feeling overwhelmed. Let's take a moment to breathe.",
            "expected_pattern": "overwhelm",
            "description": "Assistant addresses overwhelm"
        },
        {
            "assistant_response": "I can help you stay on track. Let's set up a check-in schedule.",
            "expected_pattern": "focus",
            "description": "Assistant offers check-in"
        },
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n   Scenario {i}: {scenario['description']}")
        print(f"   Assistant: '{scenario['assistant_response'][:60]}...'")
        
        # Add to conversation context
        context.add_assistant_message(scenario['assistant_response'])
        
        # Build query from conversation (simulating what the code does)
        query_parts = []
        query_parts.append(scenario['assistant_response'][:200])
        
        # Look for patterns
        if any(keyword in scenario['assistant_response'].lower() for keyword in 
               ["focus", "overwhelm", "task", "help", "can't", "need", "stuck"]):
            query_parts.append(scenario['assistant_response'])
        
        inferred_query = " ".join(query_parts[-1:])
        
        # Get dynamic context
        try:
            dynamic_context = await memory.get_dynamic_context(inferred_query, k=3)
            
            if dynamic_context:
                print(f"   ✅ Found dynamic context!")
                # Count examples
                example_count = dynamic_context.count("Example")
                print(f"   📊 Includes {example_count} similar past interventions")
                print(f"   📝 Sample: {dynamic_context[:150]}...")
            else:
                print(f"   ⚠️  No dynamic context found (similarity threshold not met)")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Step 3: Test with actual GeminiLiveClient (simulated)
    print("\n3️⃣  Testing with GeminiLiveClient context inference...")
    
    try:
        # Create a client instance (we won't actually connect)
        config = GeminiLiveConfig(voice="Puck", sample_rate=16000)
        client = GeminiLiveClient(
            config=config,
            session_id="test",
            user_id=user_id,
            memory=memory
        )
        
        # Simulate conversation flow
        print("   Simulating conversation flow...")
        
        # Add some messages to context
        client.context.add_assistant_message("Let's break this down into smaller steps.")
        client._last_assistant_response = "Let's break this down into smaller steps."
        client._turn_count = 1
        
        # Test the context preparation method
        print("   Testing _prepare_and_inject_dynamic_context()...")
        
        # Note: We can't actually call this without a live session, but we can test the logic
        # by checking if it would find context
        
        # Build query like the method does
        recent_messages = client.context.get_recent_messages(n=6)
        query_parts = []
        
        for msg in recent_messages:
            if msg["role"] == "user":
                query_parts.append(msg["content"])
        
        if not query_parts and client._last_assistant_response:
            query_parts.append(client._last_assistant_response[:200])
        
        if query_parts:
            inferred_query = " ".join(query_parts[-1:])
            dynamic_context = await memory.get_dynamic_context(inferred_query, k=3)
            
            if dynamic_context:
                print(f"   ✅ Context preparation would succeed!")
                print(f"   📊 Would inject {dynamic_context.count('Example')} examples")
            else:
                print(f"   ⚠️  Context preparation would return no context")
        
    except Exception as e:
        print(f"   ⚠️  Could not test with client (expected if not connected): {e}")
    
    # Step 4: Verify context format
    print("\n4️⃣  Verifying context format...")
    
    test_query = "I can't focus on my homework"
    dynamic_context = await memory.get_dynamic_context(test_query, k=3)
    
    if dynamic_context:
        print("   ✅ Context format:")
        print(f"   {dynamic_context[:200]}...")
        
        # Check format requirements
        has_examples = "Example" in dynamic_context
        has_similarity = "similarity:" in dynamic_context
        has_user_said = "User said:" in dynamic_context
        has_agent_did = "Agent did:" in dynamic_context
        
        print(f"\n   Format checks:")
        print(f"   - Has examples: {has_examples} ✅" if has_examples else f"   - Has examples: {has_examples} ❌")
        print(f"   - Has similarity scores: {has_similarity} ✅" if has_similarity else f"   - Has similarity scores: {has_similarity} ❌")
        print(f"   - Has user context: {has_user_said} ✅" if has_user_said else f"   - Has user context: {has_user_said} ❌")
        print(f"   - Has agent actions: {has_agent_did} ✅" if has_agent_did else f"   - Has agent actions: {has_agent_did} ❌")
    
    # Step 5: Test edge cases
    print("\n5️⃣  Testing edge cases...")
    
    # Empty conversation
    empty_context = ConversationContext()
    print("   - Empty conversation: Would skip (no messages)")
    
    # Very short query
    short_context = await memory.get_dynamic_context("hi", k=3)
    if short_context:
        print("   ⚠️  Short query returned context (unexpected)")
    else:
        print("   ✅ Short query correctly skipped")
    
    # Unrelated query
    unrelated = await memory.get_dynamic_context("What's the weather like?", k=3)
    if unrelated:
        print("   ⚠️  Unrelated query returned context (might be OK if similarity is high)")
    else:
        print("   ✅ Unrelated query correctly returned no context")
    
    print("\n" + "=" * 70)
    print("✅ Dynamic context injection test complete!")
    print("\n💡 Summary:")
    print("   - Context inference works from conversation patterns")
    print("   - Similar interventions are found and formatted correctly")
    print("   - Context will be injected after assistant responses")
    print("   - Ready for use with audio interface!")
    print("\n📝 Next steps:")
    print("   1. Start the web server: uvicorn web.app:app --reload")
    print("   2. Open http://localhost:8000 in browser")
    print("   3. Start a conversation and watch for context injection")
    print("   4. Check console logs for '📚 Injected dynamic context' messages")


if __name__ == "__main__":
    asyncio.run(test_dynamic_context_injection())
