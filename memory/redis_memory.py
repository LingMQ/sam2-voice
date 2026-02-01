"""Redis-backed memory with vector search for semantic retrieval."""

import os
import json
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict
import redis
from redis.commands.search import field, index_definition
from redis.commands.search.query import Query
import weave

VectorField = field.VectorField
TextField = field.TextField
TagField = field.TagField
NumericField = field.NumericField
IndexDefinition = index_definition.IndexDefinition
IndexType = index_definition.IndexType


class RedisUserMemory:
    """User memory backed by Redis with vector search for semantic retrieval."""

    def __init__(self, user_id: str, redis_url: str):
        """Initialize user memory.
        
        Args:
            user_id: User identifier
            redis_url: Redis connection URL
        """
        self.user_id = user_id
        self.client = redis.from_url(redis_url, decode_responses=False)
        self.index_name = f"idx:user:{user_id}"
        self._ensure_index()

    def _ensure_index(self):
        """Create vector search index if it doesn't exist."""
        try:
            # Check if index exists
            self.client.ft(self.index_name).info()
        except redis.ResponseError:
            # Index doesn't exist, create it
            # Note: Embedding dimension is 768 for text-embedding-004
            # We'll verify this when we create the first embedding
            schema = (
                TextField("$.intervention", as_name="intervention"),
                TextField("$.context", as_name="context"),
                TagField("$.outcome", as_name="outcome"),
                TextField("$.task", as_name="task"),
                NumericField("$.timestamp", as_name="timestamp"),
                VectorField(
                    "$.embedding",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": 768,  # text-embedding-004 dimension
                        "DISTANCE_METRIC": "COSINE"
                    },
                    as_name="embedding"
                )
            )
            
            definition = IndexDefinition(
                prefix=[f"user:{self.user_id}:intervention:"],
                index_type=IndexType.JSON
            )
            
            try:
                self.client.ft(self.index_name).create_index(schema, definition=definition)
                print(f"✅ Created vector search index: {self.index_name}")
            except Exception as e:
                print(f"⚠️  Warning: Could not create vector index: {e}")
                print("   Memory will work but vector search may not be available")

    @weave.op()
    async def record_intervention(
        self,
        intervention_text: str,
        context: str,
        task: str,
        outcome: str,
        embedding: List[float]
    ) -> str:
        """Store intervention with embedding for vector search.
        
        Args:
            intervention_text: What the agent said/did
            context: User's situation/request
            task: Task being worked on
            outcome: Result (task_completed, re_engaged, distracted, abandoned)
            embedding: Pre-computed embedding vector
            
        Returns:
            Redis key where intervention was stored
        """
        timestamp_ms = int(datetime.now().timestamp() * 1000)
        key = f"user:{self.user_id}:intervention:{timestamp_ms}"

        data = {
            "intervention": intervention_text,
            "context": context,
            "task": task,
            "outcome": outcome,
            "timestamp": datetime.now().timestamp(),
            "embedding": embedding
        }

        try:
            # Store with JSON
            self.client.json().set(key, "$", data)
            
            # Set TTL: 30 days (memory decay)
            self.client.expire(key, 60 * 60 * 24 * 30)
            
            return key
        except Exception as e:
            print(f"Error storing intervention: {e}")
            raise

    @weave.op()
    async def find_similar_interventions(
        self,
        query_embedding: List[float],
        k: int = 5,
        successful_only: bool = True
    ) -> List[Dict]:
        """Find semantically similar past interventions using vector search.
        
        Args:
            query_embedding: Embedding of current user message
            k: Number of results to return
            successful_only: Only return successful outcomes
            
        Returns:
            List of similar interventions with similarity scores
        """
        try:
            # Convert embedding to bytes
            query_vector = np.array(query_embedding, dtype=np.float32).tobytes()

            # Build filter for outcomes
            if successful_only:
                filter_str = "@outcome:{task_completed|re_engaged}"
            else:
                filter_str = "*"

            # Build KNN query
            query = Query(
                f"({filter_str})=>[KNN {k} @embedding $query_vector AS distance]"
            ).sort_by("distance").return_fields(
                "intervention", "context", "outcome", "task", "distance"
            ).dialect(2)

            # Execute search
            results = self.client.ft(self.index_name).search(
                query,
                query_params={"query_vector": query_vector}
            )

            # Transform results
            similar = []
            for doc in results.docs:
                similar.append({
                    "intervention": doc.intervention,
                    "context": doc.context,
                    "outcome": doc.outcome,
                    "task": doc.task,
                    "similarity": 1 - float(doc.distance)  # Convert distance to similarity
                })

            return similar

        except Exception as e:
            print(f"Vector search error: {e}")
            # Return empty list on error (graceful degradation)
            return []

    @weave.op()
    def store_reflection(self, insight: str, session_summary: str):
        """Store session reflection.
        
        Args:
            insight: Generated insight from reflection
            session_summary: Summary of the session
        """
        timestamp_ms = int(datetime.now().timestamp() * 1000)
        key = f"user:{self.user_id}:reflection:{timestamp_ms}"

        data = {
            "insight": insight,
            "session_summary": session_summary[:500],  # Truncate if too long
            "timestamp": datetime.now().isoformat()
        }

        try:
            self.client.json().set(key, "$", data)
            # Reflections last 90 days
            self.client.expire(key, 60 * 60 * 24 * 90)
        except Exception as e:
            print(f"Error storing reflection: {e}")

    @weave.op()
    def get_recent_reflections(self, limit: int = 5) -> List[str]:
        """Get recent session reflections.
        
        Args:
            limit: Maximum number of reflections to return
            
        Returns:
            List of insight strings
        """
        pattern = f"user:{self.user_id}:reflection:*"
        
        try:
            keys = list(self.client.scan_iter(pattern, count=100))
            # Sort by key (which includes timestamp) in reverse order
            keys = sorted(keys, reverse=True)[:limit]

            reflections = []
            for key in keys:
                try:
                    data = self.client.json().get(key)
                    if data and "insight" in data:
                        reflections.append(data["insight"])
                except Exception as e:
                    print(f"Error reading reflection {key}: {e}")
                    continue

            return reflections
        except Exception as e:
            print(f"Error getting reflections: {e}")
            return []

    @weave.op()
    async def get_context_for_prompt(self) -> str:
        """Generate context string to include in agent prompts.
        
        Returns:
            Context string with insights and memory status
        """
        context_parts = []

        # Get recent reflections
        reflections = self.get_recent_reflections(3)
        if reflections:
            context_parts.append(
                "## Key insights from past sessions:\n" +
                "\n".join(f"- {r}" for r in reflections)
            )

        # Count successful interventions
        pattern = f"user:{self.user_id}:intervention:*"
        try:
            intervention_count = len(list(self.client.scan_iter(pattern, count=1000)))
            
            if intervention_count > 0:
                context_parts.append(
                    f"## Memory status:\n- {intervention_count} past interventions stored"
                )
        except Exception as e:
            print(f"Error counting interventions: {e}")

        return "\n\n".join(context_parts) if context_parts else "New user - no history yet."

    def get_stats(self) -> Dict:
        """Get memory statistics for this user.
        
        Returns:
            Dictionary with memory statistics
        """
        intervention_pattern = f"user:{self.user_id}:intervention:*"
        reflection_pattern = f"user:{self.user_id}:reflection:*"

        try:
            return {
                "user_id": self.user_id,
                "total_interventions": len(list(self.client.scan_iter(intervention_pattern, count=1000))),
                "total_reflections": len(list(self.client.scan_iter(reflection_pattern, count=1000)))
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                "user_id": self.user_id,
                "total_interventions": 0,
                "total_reflections": 0
            }
