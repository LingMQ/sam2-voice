#!/usr/bin/env python3
"""Test the complete memory system."""

import asyncio
import os
from dotenv import load_dotenv

from memory.embeddings import get_embedding
from memory.redis_memory import RedisUserMemory

load_dotenv()


async def test_memory_system():
    """Test the complete memory system."""
    print("=" * 60)
    print("Memory System Test")
    print("=" * 60)
    print()
    
    # Check Redis URL
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("❌ REDIS_URL not found in .env")
        return False
    
    # Test embedding generation
    print("1. Testing embedding generation...")
    try:
        test_text = "I can't focus on my homework"
        embedding = await get_embedding(test_text)
        print(f"   ✅ Embedding generated: {len(embedding)} dimensions")
        print(f"   First few values: {embedding[:5]}")
    except Exception as e:
        print(f"   ❌ Embedding generation failed: {e}")
        return False
    
    # Test memory initialization
    print("\n2. Testing memory initialization...")
    try:
        memory = RedisUserMemory(user_id="test_user", redis_url=redis_url)
        print("   ✅ Memory initialized")
    except Exception as e:
        print(f"   ❌ Memory initialization failed: {e}")
        return False
    
    # Test storing intervention
    print("\n3. Testing intervention storage...")
    try:
        key = await memory.record_intervention(
            intervention_text="Let's break this into 3 tiny steps",
            context="I can't focus on my homework",
            task="homework",
            outcome="task_completed",
            embedding=embedding
        )
        print(f"   ✅ Intervention stored: {key}")
    except Exception as e:
        print(f"   ❌ Intervention storage failed: {e}")
        return False
    
    # Test vector search
    print("\n4. Testing vector search...")
    try:
        # Create a similar query
        query_text = "I'm struggling to concentrate on my studies"
        query_embedding = await get_embedding(query_text)
        
        similar = await memory.find_similar_interventions(
            query_embedding=query_embedding,
            k=3,
            successful_only=True
        )
        print(f"   ✅ Found {len(similar)} similar interventions")
        if similar:
            print(f"   Top match: '{similar[0]['intervention']}' (similarity: {similar[0]['similarity']:.2f})")
    except Exception as e:
        print(f"   ❌ Vector search failed: {e}")
        return False
    
    # Test reflection storage
    print("\n5. Testing reflection storage...")
    try:
        memory.store_reflection(
            insight="User responds well to task breakdown into micro-steps",
            session_summary="User said they can't focus. Agent broke task into steps. User completed task."
        )
        print("   ✅ Reflection stored")
    except Exception as e:
        print(f"   ❌ Reflection storage failed: {e}")
        return False
    
    # Test context generation
    print("\n6. Testing context generation...")
    try:
        context = await memory.get_context_for_prompt()
        print("   ✅ Context generated:")
        print(f"   {context[:200]}...")
    except Exception as e:
        print(f"   ❌ Context generation failed: {e}")
        return False
    
    # Test stats
    print("\n7. Testing memory stats...")
    try:
        stats = memory.get_stats()
        print(f"   ✅ Stats: {stats}")
    except Exception as e:
        print(f"   ❌ Stats failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! Memory system is working correctly.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_memory_system())
    exit(0 if success else 1)
