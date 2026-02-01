#!/usr/bin/env python3
"""Test Redis vector search capabilities."""

import os
import sys
from dotenv import load_dotenv
import redis
from redis.commands.search import field, index_definition

VectorField = field.VectorField
TextField = field.TextField
IndexDefinition = index_definition.IndexDefinition
IndexType = index_definition.IndexType

load_dotenv()

def test_vector_search():
    """Test if vector search is available."""
    redis_url = os.getenv("REDIS_URL")
    client = redis.from_url(redis_url, decode_responses=False)
    
    print("Testing vector search capabilities...")
    
    # Test index name
    test_index = "test_vector_index"
    
    try:
        # Try to get info on index (will fail if doesn't exist)
        try:
            info = client.ft(test_index).info()
            print(f"✅ Index '{test_index}' already exists")
            # Clean it up for testing
            try:
                client.ft(test_index).dropindex()
                print("   (Cleaned up for fresh test)")
            except:
                pass
        except:
            pass
        
        # Try to create a test vector index
        schema = (
            TextField("$.text", as_name="text"),
            VectorField(
                "$.embedding",
                "FLAT",
                {
                    "TYPE": "FLOAT32",
                    "DIM": 768,  # Standard embedding dimension
                    "DISTANCE_METRIC": "COSINE"
                },
                as_name="embedding"
            )
        )
        
        definition = IndexDefinition(
            prefix=["test:vector:"],
            index_type=IndexType.JSON
        )
        
        client.ft(test_index).create_index(schema, definition=definition)
        print(f"✅ Successfully created vector search index!")
        print("   Vector search is fully supported")
        
        # Clean up
        try:
            client.ft(test_index).dropindex()
            print("   (Cleaned up test index)")
        except:
            pass
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "MODULE" in error_msg or "command" in error_msg.lower():
            print(f"❌ Vector search not available: {e}")
            print("\n⚠️  Your Redis instance may not have RediSearch module enabled.")
            print("   For Redis Cloud:")
            print("   1. Go to your Redis Cloud dashboard")
            print("   2. Check if your database is 'Redis Stack' (not just 'Redis')")
            print("   3. If not, you may need to create a new Redis Stack database")
            return False
        else:
            print(f"⚠️  Unexpected error: {e}")
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("Redis Vector Search Test")
    print("=" * 60)
    print()
    
    success = test_vector_search()
    
    print()
    if success:
        print("✅ Vector search is ready! You can proceed with implementation.")
    else:
        print("❌ Vector search is not available.")
        print("   You'll need Redis Stack (not just Redis) for vector search.")
        print("   However, you can still implement basic memory storage without vectors.")
    sys.exit(0 if success else 1)
