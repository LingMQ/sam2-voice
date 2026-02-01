#!/usr/bin/env python3
"""Health check script for memory system."""

import os
import sys
import json
from dotenv import load_dotenv
from memory.health import MemoryHealthCheck

load_dotenv()


def main():
    """Run health checks."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("❌ REDIS_URL not set")
        sys.exit(1)
    
    user_id = sys.argv[1] if len(sys.argv) > 1 else "default_user"
    
    print("=" * 60)
    print("Memory System Health Check")
    print("=" * 60)
    print()
    
    health = MemoryHealthCheck(redis_url)
    status = health.get_comprehensive_health(user_id)
    
    # Print results
    print(f"Overall Status: {status['overall_status'].upper()}")
    print()
    
    for check_name, check_result in status["checks"].items():
        status_icon = "✅" if check_result["status"] == "healthy" else "⚠️" if check_result["status"] == "warning" else "❌"
        print(f"{status_icon} {check_name}: {check_result['status']}")
        print(f"   Latency: {check_result['latency_ms']}ms")
        if check_result.get("error"):
            print(f"   Error: {check_result['error']}")
        print()
    
    # Exit code based on status
    if status["overall_status"] == "healthy":
        sys.exit(0)
    elif status["overall_status"] == "degraded":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
