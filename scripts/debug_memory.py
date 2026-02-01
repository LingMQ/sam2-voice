#!/usr/bin/env python3
"""Debug utility for memory system."""

import os
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from memory.redis_memory import RedisUserMemory
from memory.debug import MemoryDebugger

load_dotenv()


def main():
    """Debug memory system."""
    if len(sys.argv) < 2:
        print("Usage: python debug_memory.py <user_id> [command]")
        print("Commands:")
        print("  summary - Get memory summary")
        print("  interventions - List interventions")
        print("  reflections - List reflections")
        print("  export - Export all data")
        print("  clear - Clear all data (requires --confirm)")
        sys.exit(1)
    
    user_id = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else "summary"
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("❌ REDIS_URL not set")
        sys.exit(1)
    
    memory = RedisUserMemory(user_id=user_id, redis_url=redis_url)
    debugger = MemoryDebugger(memory)
    
    if command == "summary":
        summary = debugger.get_memory_summary()
        print(json.dumps(summary, indent=2, default=str))
    
    elif command == "interventions":
        interventions = debugger.inspect_interventions(limit=20)
        print(f"Found {len(interventions)} interventions:")
        for iv in interventions:
            print(f"\nKey: {iv['key']}")
            print(f"TTL: {iv['ttl']} seconds")
            print(f"Data: {json.dumps(iv['data'], indent=2, default=str)}")
    
    elif command == "reflections":
        reflections = debugger.inspect_reflections(limit=20)
        print(f"Found {len(reflections)} reflections:")
        for rf in reflections:
            print(f"\nKey: {rf['key']}")
            print(f"TTL: {rf['ttl']} seconds")
            print(f"Data: {json.dumps(rf['data'], indent=2, default=str)}")
    
    elif command == "export":
        output_file = f"memory_export_{user_id}.json"
        export_data = debugger.export_memory_data(output_file)
        print(f"✅ Exported to {output_file}")
        print(f"Data size: {len(export_data)} characters")
    
    elif command == "clear":
        if "--confirm" not in sys.argv:
            print("❌ Must use --confirm flag to clear data")
            sys.exit(1)
        if debugger.clear_all_data(confirm=True):
            print("✅ All data cleared")
        else:
            print("❌ Failed to clear data")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
