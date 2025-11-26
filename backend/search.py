"""
Production vector search with async pgvector queries.
Uses HNSW index for sub-100ms searches on 50M+ items.
"""
from typing import List, Dict, Any

try:
    from . import db
    from .config import EMBEDDING_DIMENSION
except ImportError:
    import db
    from config import EMBEDDING_DIMENSION


def _normalize_distances(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize distance scores to 0-1 similarity scores."""
    if not rows:
        return rows
    max_distance = max(r["distance"] for r in rows) or 1.0
    for r in rows:
        r["similarity"] = 1.0 - (r["distance"] / max_distance)
    return rows


async def search_similar(embedding: List[float], limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search for similar items using pgvector cosine distance.
    
    The HNSW index on `embedding` makes this query fast even with 50M rows.
    Query time: ~10-50ms with HNSW index vs 5000ms+ without.
    
    Args:
        embedding: 768-dim vector from OpenCLIP or OpenAI
        limit: Max results to return
        
    Returns:
        List of items sorted by similarity, with redirect URLs for deep linking
    """
    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(f"Embedding must be {EMBEDDING_DIMENSION}-dimensional, got {len(embedding)}")

    # Convert list to pgvector format string
    embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
    
    query = """
        SELECT 
            id, 
            external_id, 
            title, 
            description, 
            price, 
            url, 
            image_url,
            source,
            (embedding <=> $1::vector) AS distance
        FROM fashion_items
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT $2;
    """
    
    rows = await db.fetch_all(query, [embedding_str, limit])
    rows = _normalize_distances(rows)
    
    # Build platform-specific deep links
    for r in rows:
        external_id = r.get("external_id")
        source = r.get("source", "").lower()
        
        if source == "depop" and external_id:
            r["redirect_url"] = f"depop://product/{external_id}"
        elif source == "grailed" and external_id:
            r["redirect_url"] = f"https://www.grailed.com/listings/{external_id}"
        elif source == "vinted" and external_id:
            r["redirect_url"] = f"https://www.vinted.com/items/{external_id}"
        else:
            r["redirect_url"] = r.get("url")
    
    return rows
