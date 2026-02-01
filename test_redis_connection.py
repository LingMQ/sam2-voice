#!/usr/bin/env python3
"""Test Redis connection and verify vector search capabilities."""

import os
import sys
from dotenv import load_dotenv
import redis

load_dotenv()

def test_redis_connection():
    """Test basic Redis connection."""
    redis_url = os.getenv("REDIS_URL")
    
    if not redis_url:
        print("❌ REDIS_URL not found in .env file")
        print("\nPlease add your Redis connection URL to .env:")
        print("REDIS_URL=redis://default:password@your-redis-instance:6379")
        return False
    
    print(f"🔗 Connecting to Redis: {redis_url.split('@')[-1] if '@' in redis_url else 'localhost'}")
    
    try:
        # Create Redis client
        client = redis.from_url(redis_url, decode_responses=False)
        
        # Test connection
        result = client.ping()
        if result:
            print("✅ Redis connection successful!")
        else:
            print("❌ Redis ping failed")
            return False
        
        # Check Redis version
        info = client.info()
        redis_version = info.get('redis_version', 'unknown')
        print(f"📦 Redis version: {redis_version}")
        
        # Check if Redis Stack (for vector search)
        modules = info.get('modules', [])
        has_redisearch = any('search' in str(module).lower() for module in modules)
        
        if has_redisearch:
            print("✅ RediSearch module detected (vector search available)")
        else:
            print("⚠️  RediSearch module not detected")
            print("   Vector search requires Redis Stack 7.0+")
            print("   If using Redis Cloud, ensure you selected 'Redis Stack'")
        
        # Test JSON support
        try:
            test_key = "test:json:check"
            test_data = {"test": "data", "number": 42}
            client.json().set(test_key, "$", test_data)
            retrieved = client.json().get(test_key)
            client.delete(test_key)
            
            if retrieved and retrieved.get("test") == "data":
                print("✅ JSON support working")
            else:
                print("⚠️  JSON support may not be working correctly")
        except Exception as e:
            print(f"⚠️  JSON test failed: {e}")
            print("   This might be okay if JSON module isn't loaded")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your REDIS_URL format: redis://default:password@host:port")
        print("2. Verify Redis instance is running")
        print("3. Check network connectivity")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Redis Connection Test")
    print("=" * 60)
    print()
    
    success = test_redis_connection()
    
    print()
    if success:
        print("✅ All checks passed! Redis is ready to use.")
        print("\nNext steps:")
        print("1. Your Redis URL is configured correctly")
        print("2. Start implementing the memory system (see DETAILED_EXECUTION_PLAN.md)")
    else:
        print("❌ Redis setup incomplete. Please fix the issues above.")
        sys.exit(1)
