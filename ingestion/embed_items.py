"""
Batch embedding generation for Depop items.
Downloads images and generates embeddings for items missing vectors.
"""
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image

import sys
import os

# Add backend to path
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))

# Set database URL
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from db import execute_sync, fetch_all_sync  # noqa: E402
from embeddings import embed_image  # noqa: E402

REQUEST_TIMEOUT = 20  # Default timeout for downloads

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _download_image(url: str, timeout: int = 10) -> Optional[bytes]:
    """
    Download and validate image from URL.
    Returns None if download fails or image is invalid.
    """
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            logger.warning(f"HTTP {resp.status_code} for {url}")
            return None
        
        # Validate image can be decoded
        Image.open(BytesIO(resp.content)).verify()
        return resp.content
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return None


def embed_single_item(item: dict) -> bool:
    """
    Embed a single item. Returns True if successful.
    Creates multimodal embedding from image + title + description.
    """
    external_id = item.get("external_id")
    image_url = item.get("image_url")
    title = item.get("title", "")
    description = item.get("description", "")
    
    if not image_url:
        logger.warning(f"No image_url for {external_id}")
        return False
    
    # Download image
    image_bytes = _download_image(image_url)
    if not image_bytes:
        return False
    
    # Combine title and description for text embedding
    text_content = f"{title}. {description}".strip()
    
    # Generate multimodal embedding (image + text)
    try:
        vector = embed_image(image_bytes, text=text_content if text_content else None)
    except Exception as e:
        logger.error(f"Embedding failed for {external_id}: {e}")
        return False
    
    # Update database
    try:
        execute_sync(
            "UPDATE fashion_items SET embedding = %s, updated_at = NOW() WHERE id = %s;",
            (vector, item["id"])
        )
        logger.info(f"✓ Embedded {external_id}")
        return True
    except Exception as e:
        logger.error(f"DB update failed for {external_id}: {e}")
        return False


def embed_missing(limit: int = 100, parallel: int = 4):
    """
    Find items without embeddings and generate them.
    
    Args:
        limit: Max items to process in this run (use 0 or None for all items)
        parallel: Number of concurrent downloads (not embedding - that's CPU/GPU bound)
    
    Performance notes:
    - For 1000s of items, consider GPU batching
    - For 10M+ items, use distributed workers (Celery, Ray)
    - Cache embeddings in Redis for faster retries
    """
    # If limit is 0 or None, process all items
    if limit == 0 or limit is None:
        items = fetch_all_sync(
            """
            SELECT id, external_id, image_url, title, description
            FROM fashion_items
            WHERE embedding IS NULL
              AND image_url IS NOT NULL
            ORDER BY created_at DESC;
            """
        )
    else:
        items = fetch_all_sync(
            """
            SELECT id, external_id, image_url, title, description
            FROM fashion_items
            WHERE embedding IS NULL
              AND image_url IS NOT NULL
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (limit,),
        )
    
    if not items:
        logger.info("✅ All items already have embeddings!")
        return
    
    logger.info("="*70)
    logger.info(f"🧠 GENERATING EMBEDDINGS FOR {len(items)} ITEMS")
    logger.info("="*70)
    
    success_count = 0
    fail_count = 0
    
    # Process items sequentially (embedding is the bottleneck, not download)
    # For production at scale: use GPU batching and parallel workers
    for idx, item in enumerate(items, 1):
        logger.info(f"[{idx}/{len(items)}] Processing {item['external_id']}")
        if embed_single_item(item):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info("="*70)
    logger.info(f"✅ EMBEDDING COMPLETE")
    logger.info(f"   Success: {success_count}/{len(items)}")
    logger.info(f"   Failed: {fail_count}/{len(items)}")
    logger.info(f"   Success rate: {(success_count/len(items)*100):.1f}%")
    logger.info("="*70)


if __name__ == "__main__":
    # Process ALL items (set limit=0 or None for no limit)
    # Use limit=50 for testing, or 0 for production batch processing
    import sys
    
    # Check if user wants to process all items
    limit = 0 if len(sys.argv) > 1 and sys.argv[1] == "all" else 50
    
    if limit == 0:
        logger.info("Processing ALL items without limit")
    else:
        logger.info(f"Processing up to {limit} items")
    
    embed_missing(limit=limit, parallel=4)
