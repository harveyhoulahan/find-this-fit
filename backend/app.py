"""
Find This Fit - Production FastAPI backend.
Handles image upload, embedding generation, and vector search.
"""
import base64
import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:
    from .embeddings import embed_image, preload_models
    from .models import DepopItem, SearchRequest, SearchResponse
    from .search import search_similar
    from . import db
except ImportError:
    from embeddings import embed_image, preload_models
    from models import DepopItem, SearchRequest, SearchResponse
    from search import search_similar
    import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown lifecycle.
    Preloads embedding models and initializes DB pool.
    """
    logger.info("Starting Find This Fit API...")
    
    # Initialize database pool
    await db.init_pool(min_size=2, max_size=10)
    logger.info("Database pool initialized")
    
    # Preload embedding models (avoids 5+ second delay on first request)
    preload_models()
    logger.info("Embedding models preloaded")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down...")
    await db.close_pool()


app = FastAPI(
    title="Find This Fit API",
    version="1.0.0",
    description="Visual search for fashion items across resale marketplaces",
    lifespan=lifespan
)

# CORS for iOS Mini App and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/search_by_image", response_model=SearchResponse)
async def search_by_image(payload: SearchRequest):
    """
    Upload an image and get visually similar Depop items.
    
    Flow:
    1. Decode base64 image
    2. Generate 768-dim embedding (OpenAI or CLIP)
    3. Query pgvector for nearest neighbors
    4. Return top 20 matches with deep links
    
    Typical latency: 100-500ms (50ms embedding + 10-50ms search + network)
    """
    try:
        image_bytes = base64.b64decode(payload.image_base64)
    except Exception as exc:
        logger.error(f"Base64 decode failed: {exc}")
        raise HTTPException(status_code=400, detail="Invalid base64 image data") from exc

    try:
        # Generate multimodal embedding (image only for photo search)
        # Note: We don't have text for user-uploaded photos,
        # but our database items have multimodal embeddings (image + title + description)
        embedding = embed_image(image_bytes, text=None)
        logger.info(f"Generated embedding: {len(embedding)} dimensions")
    except Exception as exc:
        logger.error(f"Embedding generation failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(exc)}") from exc

    try:
        # Vector search with HNSW index
        results = await search_similar(embedding, limit=20)
        logger.info(f"Found {len(results)} similar items")
    except Exception as exc:
        logger.error(f"Search failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(exc)}") from exc

    # Map to Pydantic models
    items: List[DepopItem] = []
    for r in results:
        distance_val = r.get("distance")
        items.append(
            DepopItem(
                id=r["id"],
                external_id=r.get("external_id"),
                title=r.get("title"),
                description=r.get("description"),
                price=float(r["price"]) if r.get("price") is not None else None,
                url=r.get("url"),
                image_url=r.get("image_url"),
                distance=float(distance_val) if distance_val is not None else None,
                redirect_url=r.get("redirect_url"),
            )
        )
    
    return SearchResponse(items=items)


@app.post("/search_by_text", response_model=SearchResponse)
async def search_by_text(payload: dict):
    """
    Search for fashion items by text description.
    
    Flow:
    1. Extract text query from payload
    2. Generate text-only embedding using CLIP
    3. Query pgvector for nearest neighbors
    4. Return top 20 matches
    
    Example: "vintage black hoodie with graphic print"
    """
    query = payload.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query text is required")
    
    try:
        # Generate text-only embedding (no image)
        # CLIP can embed text without an image
        embedding = embed_image(image_bytes=None, text=query)
        logger.info(f"Generated text embedding for: '{query}'")
    except Exception as exc:
        logger.error(f"Text embedding generation failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(exc)}") from exc

    try:
        # Vector search with HNSW index
        results = await search_similar(embedding, limit=20)
        logger.info(f"Found {len(results)} similar items for text query")
    except Exception as exc:
        logger.error(f"Search failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(exc)}") from exc

    # Map to Pydantic models
    items: List[DepopItem] = []
    for r in results:
        distance_val = r.get("distance")
        items.append(
            DepopItem(
                id=r["id"],
                external_id=r.get("external_id"),
                title=r.get("title"),
                description=r.get("description"),
                price=float(r["price"]) if r.get("price") is not None else None,
                url=r.get("url"),
                image_url=r.get("image_url"),
                distance=float(distance_val) if distance_val is not None else None,
                redirect_url=r.get("redirect_url"),
            )
        )
    
    return SearchResponse(items=items)


@app.post("/search_combined", response_model=SearchResponse)
async def search_combined(payload: dict):
    """
    Search for fashion items using both image and text description.
    
    Flow:
    1. Decode base64 image and extract text query
    2. Generate multimodal embedding using both image and text
    3. Query pgvector for nearest neighbors
    4. Return top 20 matches
    
    This provides the most accurate results by combining visual and textual information.
    Example: image of a jacket + "vintage distressed denim"
    """
    query = payload.get("query", "").strip()
    image_base64 = payload.get("image_base64", "")
    
    if not query and not image_base64:
        raise HTTPException(
            status_code=400, 
            detail="At least one of 'query' or 'image_base64' is required"
        )
    
    image_bytes = None
    if image_base64:
        try:
            image_bytes = base64.b64decode(image_base64)
        except Exception as exc:
            logger.error(f"Base64 decode failed: {exc}")
            raise HTTPException(status_code=400, detail="Invalid base64 image data") from exc
    
    try:
        # Generate multimodal embedding with both image and text
        embedding = embed_image(image_bytes=image_bytes, text=query if query else None)
        logger.info(f"Generated combined embedding (image: {image_bytes is not None}, text: '{query}')")
    except Exception as exc:
        logger.error(f"Combined embedding generation failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(exc)}") from exc

    try:
        # Vector search with HNSW index
        results = await search_similar(embedding, limit=20)
        logger.info(f"Found {len(results)} similar items for combined query")
    except Exception as exc:
        logger.error(f"Search failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(exc)}") from exc

    # Map to Pydantic models
    items: List[DepopItem] = []
    for r in results:
        distance_val = r.get("distance")
        items.append(
            DepopItem(
                id=r["id"],
                external_id=r.get("external_id"),
                title=r.get("title"),
                description=r.get("description"),
                price=float(r["price"]) if r.get("price") is not None else None,
                url=r.get("url"),
                image_url=r.get("image_url"),
                distance=float(distance_val) if distance_val is not None else None,
                redirect_url=r.get("redirect_url"),
            )
        )
    
    return SearchResponse(items=items)


@app.get("/health")
async def health():
    """Health check endpoint for load balancers."""
    return {
        "status": "ok",
        "service": "find-this-fit",
        "version": "1.0.0"
    }


@app.get("/metrics")
async def metrics():
    """
    Basic metrics endpoint.
    In production: integrate Prometheus or DataDog.
    """
    # Get DB pool stats
    pool = db._pool
    if pool:
        pool_stats = {
            "pool_size": pool.get_size(),
            "pool_free": pool.get_idle_size(),
        }
    else:
        pool_stats = {"error": "pool_not_initialized"}
    
    return {
        "database": pool_stats,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
