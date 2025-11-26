"""
Enhanced search with filters for category, brand, price, color, etc.
Optimized for 30K+ item database with CLIP metadata.
"""
from typing import List, Dict, Any, Optional

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


async def search_similar_with_filters(
    embedding: List[float],
    limit: int = 20,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    color: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sources: Optional[List[str]] = None,
    condition: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Enhanced visual search with metadata filters.
    
    Now you can search by image AND filter by:
    - category (e.g., 'jacket', 'bag', 'shoes')
    - brand (e.g., 'Nike', 'Prada', 'Supreme')
    - color (e.g., 'black', 'navy', 'olive')
    - price range
    - sources (e.g., ['depop', 'grailed'])
    - condition (e.g., 'Good', 'New')
    
    Args:
        embedding: 768-dim CLIP vector
        limit: Max results
        category: Filter by category
        brand: Filter by brand
        color: Filter by color
        min_price: Minimum price
        max_price: Maximum price
        sources: List of sources to search (depop, grailed, vinted)
        condition: Filter by condition
        
    Returns:
        List of similar items matching all filters
    """
    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(f"Embedding must be {EMBEDDING_DIMENSION}-dimensional")

    embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
    
    # Build dynamic WHERE clause
    where_conditions = ["embedding IS NOT NULL"]
    params = [embedding_str, limit]
    param_idx = 3
    
    if category:
        where_conditions.append(f"category = ${param_idx}")
        params.append(category)
        param_idx += 1
    
    if brand:
        where_conditions.append(f"brand ILIKE ${param_idx}")
        params.append(f"%{brand}%")
        param_idx += 1
    
    if color:
        where_conditions.append(f"color = ${param_idx}")
        params.append(color)
        param_idx += 1
    
    if min_price is not None:
        where_conditions.append(f"price >= ${param_idx}")
        params.append(min_price)
        param_idx += 1
    
    if max_price is not None:
        where_conditions.append(f"price <= ${param_idx}")
        params.append(max_price)
        param_idx += 1
    
    if sources:
        placeholders = ', '.join([f"${i}" for i in range(param_idx, param_idx + len(sources))])
        where_conditions.append(f"source IN ({placeholders})")
        params.extend(sources)
        param_idx += len(sources)
    
    if condition:
        where_conditions.append(f"condition = ${param_idx}")
        params.append(condition)
        param_idx += 1
    
    where_clause = " AND ".join(where_conditions)
    
    query = f"""
        SELECT 
            id, 
            external_id, 
            title, 
            description, 
            price,
            currency,
            url, 
            image_url,
            source,
            brand,
            category,
            color,
            condition,
            size,
            (embedding <=> $1::vector) AS distance
        FROM fashion_items
        WHERE {where_clause}
        ORDER BY embedding <=> $1::vector
        LIMIT $2;
    """
    
    rows = await db.fetch_all(query, params)
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


async def get_filter_options() -> Dict[str, List[str]]:
    """
    Get available filter options from the database.
    Useful for building UI dropdowns.
    
    Returns:
        Dict with categories, brands, colors, conditions, sources
    """
    categories = await db.fetch_all(
        "SELECT DISTINCT category FROM fashion_items WHERE category IS NOT NULL ORDER BY category"
    )
    brands = await db.fetch_all(
        "SELECT DISTINCT brand FROM fashion_items WHERE brand IS NOT NULL ORDER BY brand LIMIT 100"
    )
    colors = await db.fetch_all(
        "SELECT DISTINCT color FROM fashion_items WHERE color IS NOT NULL ORDER BY color"
    )
    conditions = await db.fetch_all(
        "SELECT DISTINCT condition FROM fashion_items WHERE condition IS NOT NULL ORDER BY condition"
    )
    sources = await db.fetch_all(
        "SELECT DISTINCT source FROM fashion_items ORDER BY source"
    )
    
    return {
        "categories": [r["category"] for r in categories],
        "brands": [r["brand"] for r in brands],
        "colors": [r["color"] for r in colors],
        "conditions": [r["condition"] for r in conditions],
        "sources": [r["source"] for r in sources],
    }
