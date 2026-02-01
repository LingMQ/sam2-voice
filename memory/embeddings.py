"""Gemini embeddings for semantic search."""

import os
from typing import List
from google import genai
import weave

# Initialize Gemini client
_client = None


def _get_client():
    """Get or create Gemini client."""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        _client = genai.Client(api_key=api_key)
    return _client


@weave.op()
async def get_embedding(text: str) -> List[float]:
    """Get embedding from Gemini text-embedding-004 model.
    
    Args:
        text: Text to embed
        
    Returns:
        List of float values representing the embedding vector
        
    Raises:
        ValueError: If GOOGLE_API_KEY is not set
        Exception: If embedding generation fails
    """
    client = _get_client()
    
    try:
        result = await client.aio.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        
        if not result.embeddings or len(result.embeddings) == 0:
            raise ValueError("No embeddings returned from Gemini API")
        
        embedding = result.embeddings[0].values
        
        # Verify we got a valid embedding
        if not embedding or len(embedding) == 0:
            raise ValueError("Empty embedding returned")
        
        return embedding
        
    except Exception as e:
        # Log error but don't crash - return empty list as fallback
        print(f"Error generating embedding: {e}")
        raise


async def get_embedding_dimension() -> int:
    """Get the dimension of embeddings from the model.
    
    Returns:
        Embedding dimension (typically 768 for text-embedding-004)
    """
    # Generate a test embedding to get dimension
    test_emb = await get_embedding("test")
    return len(test_emb)
