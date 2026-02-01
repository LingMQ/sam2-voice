"""Debugging utilities for memory system."""

import json
from typing import Dict, List, Optional
from datetime import datetime
import redis
from memory.redis_memory import RedisUserMemory
from memory.logger import get_logger

logger = get_logger()


class MemoryDebugger:
    """Debugging utilities for memory system."""
    
    def __init__(self, memory: RedisUserMemory):
        """Initialize debugger.
        
        Args:
            memory: RedisUserMemory instance
        """
        self.memory = memory
        self.client = memory.client
    
    def inspect_interventions(self, limit: int = 10) -> List[Dict]:
        """Inspect stored interventions.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of intervention data
        """
        pattern = f"user:{self.memory.user_id}:intervention:*"
        keys = list(self.client.scan_iter(pattern, count=1000))
        keys = sorted(keys, reverse=True)[:limit]
        
        interventions = []
        for key in keys:
            try:
                data = self.client.json().get(key)
                if data:
                    # Convert bytes key to string if needed
                    key_str = key.decode() if isinstance(key, bytes) else key
                    interventions.append({
                        "key": key_str,
                        "data": data,
                        "ttl": self.client.ttl(key)
                    })
            except Exception as e:
                logger.warning(f"Error reading intervention {key}: {e}")
        
        return interventions
    
    def inspect_reflections(self, limit: int = 10) -> List[Dict]:
        """Inspect stored reflections.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of reflection data
        """
        pattern = f"user:{self.memory.user_id}:reflection:*"
        keys = list(self.client.scan_iter(pattern, count=1000))
        keys = sorted(keys, reverse=True)[:limit]
        
        reflections = []
        for key in keys:
            try:
                data = self.client.json().get(key)
                if data:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    reflections.append({
                        "key": key_str,
                        "data": data,
                        "ttl": self.client.ttl(key)
                    })
            except Exception as e:
                logger.warning(f"Error reading reflection {key}: {e}")
        
        return reflections
    
    def get_index_info(self) -> Optional[Dict]:
        """Get vector search index information.
        
        Returns:
            Index information dict or None
        """
        try:
            info = self.client.ft(self.memory.index_name).info()
            return {
                "index_name": self.memory.index_name,
                "num_docs": info.get("num_docs", 0),
                "index_definition": info.get("index_definition", {}),
                "attributes": info.get("attributes", [])
            }
        except Exception as e:
            logger.warning(f"Error getting index info: {e}")
            return None
    
    def get_memory_summary(self) -> Dict:
        """Get comprehensive memory summary.
        
        Returns:
            Summary dictionary
        """
        stats = self.memory.get_stats()
        index_info = self.get_index_info()
        
        summary = {
            "user_id": self.memory.user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": stats,
            "index_info": index_info,
            "recent_interventions": len(self.inspect_interventions(5)),
            "recent_reflections": len(self.inspect_reflections(5))
        }
        
        return summary
    
    def export_memory_data(self, output_file: Optional[str] = None) -> str:
        """Export all memory data to JSON.
        
        Args:
            output_file: Optional output file path
            
        Returns:
            JSON string of exported data
        """
        export_data = {
            "user_id": self.memory.user_id,
            "export_timestamp": datetime.utcnow().isoformat(),
            "interventions": self.inspect_interventions(limit=1000),
            "reflections": self.inspect_reflections(limit=1000),
            "index_info": self.get_index_info(),
            "statistics": self.memory.get_stats()
        }
        
        json_str = json.dumps(export_data, indent=2, default=str)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(json_str)
            logger.info(f"Exported memory data to {output_file}")
        
        return json_str
    
    def clear_all_data(self, confirm: bool = False) -> bool:
        """Clear all memory data for this user.
        
        Args:
            confirm: Must be True to actually clear
            
        Returns:
            True if cleared, False otherwise
        """
        if not confirm:
            logger.warning("clear_all_data called without confirm=True")
            return False
        
        try:
            # Delete interventions
            pattern = f"user:{self.memory.user_id}:intervention:*"
            keys = list(self.client.scan_iter(pattern, count=1000))
            if keys:
                self.client.delete(*keys)
                logger.info(f"Deleted {len(keys)} interventions")
            
            # Delete reflections
            pattern = f"user:{self.memory.user_id}:reflection:*"
            keys = list(self.client.scan_iter(pattern, count=1000))
            if keys:
                self.client.delete(*keys)
                logger.info(f"Deleted {len(keys)} reflections")
            
            # Drop index
            try:
                self.client.ft(self.memory.index_name).dropindex()
                logger.info(f"Dropped index: {self.memory.index_name}")
            except Exception as e:
                logger.warning(f"Could not drop index: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            return False
