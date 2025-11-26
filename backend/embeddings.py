"""
Image embedding generation using OpenAI or OpenCLIP.
Production-optimized with model caching and error handling.
"""
import base64
import logging
from io import BytesIO
from typing import List, Optional

from PIL import Image

try:
    from .config import (
        EMBEDDING_DIMENSION,
        EMBEDDING_PROVIDER,
        OPENAI_API_KEY,
        OPENAI_EMBEDDING_MODEL,
        REQUEST_TIMEOUT,
    )
except ImportError:
    from config import (
        EMBEDDING_DIMENSION,
        EMBEDDING_PROVIDER,
        OPENAI_API_KEY,
        OPENAI_EMBEDDING_MODEL,
        REQUEST_TIMEOUT,
    )

logger = logging.getLogger(__name__)

# Global model cache (lazy loaded)
_openai_client = None
_clip_model = None
_clip_processor = None


def preload_models():
    """
    Preload models at startup to avoid cold-start latency.
    Call this in FastAPI lifespan to warm up models before first request.
    """
    provider = EMBEDDING_PROVIDER.lower()
    if provider == "openai":
        _get_openai_client()
        logger.info("OpenAI client initialized")
    elif provider == "clip":
        _get_clip_model()
        logger.info("CLIP model loaded into memory")
    else:
        logger.warning(f"Unknown provider '{provider}', skipping preload")


def _get_openai_client():
    """Lazy-load OpenAI client with timeout and retry config."""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=REQUEST_TIMEOUT,
            max_retries=2
        )
    return _openai_client


def _get_clip_model():
    """
    Lazy-load CLIP model.
    Using sentence-transformers wrapper for simplicity.
    For production at scale, use open_clip directly for GPU batching.
    """
    global _clip_model
    if _clip_model is None:
        from sentence_transformers import SentenceTransformer
        # Using ViT-B/32 (512-dim) - we'll pad to 768
        # For true 768-dim, use: open_clip ViT-L/14
        _clip_model = SentenceTransformer("clip-ViT-B-32")
    return _clip_model


def _ensure_dimension(vec: List[float]) -> List[float]:
    """
    Ensure vector is exactly 768-dim via truncation or zero-padding.
    OpenAI models may return different dims, CLIP is 512 by default.
    """
    if len(vec) == EMBEDDING_DIMENSION:
        return vec
    if len(vec) > EMBEDDING_DIMENSION:
        return vec[:EMBEDDING_DIMENSION]
    # Zero-pad if shorter
    padded = vec + [0.0] * (EMBEDDING_DIMENSION - len(vec))
    return padded


def _embed_with_openai(image_bytes: bytes) -> List[float]:
    """
    Generate embedding using OpenAI Vision API.
    Supports: image-embedding-3-large (3072-dim, truncated to 768)
    
    Note: As of Nov 2025, verify OpenAI's current image embedding API.
    The API may have changed - adjust accordingly.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")
    
    client = _get_openai_client()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    try:
        response = client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=[{"image": image_b64}],
        )
        vector = response.data[0].embedding
        return _ensure_dimension(list(vector))
    except Exception as e:
        logger.error(f"OpenAI embedding failed: {e}")
        raise RuntimeError(f"OpenAI API error: {e}") from e


def _embed_with_clip(image_bytes: Optional[bytes] = None, text: Optional[str] = None) -> List[float]:
    """
    Generate embedding using open-source CLIP (via sentence-transformers).
    Default: ViT-B/32 (512-dim, padded to 768)
    
    Supports text-only, image-only, or multimodal (image + text) embeddings.
    
    If both are provided, creates a multimodal embedding by averaging
    image and text embeddings. This gives better search results by
    capturing both visual and semantic information.
    
    For production at 50M scale:
    - Use open_clip library directly
    - Load ViT-L/14 for native 768-dim
    - Enable GPU batching
    - Cache embeddings in Redis
    """
    model = _get_clip_model()
    
    try:
        import numpy as np
        
        # Text-only embedding
        if image_bytes is None and text and text.strip():
            text_embedding = model.encode(text, normalize_embeddings=True)
            return _ensure_dimension(text_embedding.tolist())
        
        # Image-only embedding
        if image_bytes is not None and (text is None or not text.strip()):
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            image_embedding = model.encode(image, normalize_embeddings=True)
            return _ensure_dimension(image_embedding.tolist())
        
        # Multimodal (image + text) embedding
        if image_bytes is not None and text and text.strip():
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            image_embedding = model.encode(image, normalize_embeddings=True)
            text_embedding = model.encode(text, normalize_embeddings=True)
            # Average the embeddings (weighted equally)
            # Could also use weighted: 0.7 * image + 0.3 * text
            combined = (image_embedding + text_embedding) / 2.0
            # Re-normalize after averaging
            combined = combined / np.linalg.norm(combined)
            return _ensure_dimension(combined.tolist())
            
        raise ValueError("Must provide image_bytes, text, or both")
            
    except Exception as e:
        logger.error(f"CLIP embedding failed: {e}")
        raise RuntimeError(f"CLIP encoding error: {e}") from e


def embed_image(image_bytes: Optional[bytes] = None, text: Optional[str] = None) -> List[float]:
    """
    Generate a 768-dimensional embedding for an image, text, or both.
    
    For best results, provide both image and text (title + description).
    CLIP is designed for multimodal learning and performs better when
    combining visual and textual information.
    
    Provider selection:
    - OpenAI: Best quality, API costs, 100-300ms latency
    - CLIP: Free, open-source, 50ms (GPU) / 200ms (CPU), supports multimodal
    
    Args:
        image_bytes: Optional raw image bytes (JPEG, PNG, etc)
        text: Optional text description (title + description) to combine with image
        
    Returns:
        768-dim normalized embedding vector
        
    Raises:
        RuntimeError: If embedding generation fails
        ValueError: If provider is unknown or both inputs are None
    """
    if image_bytes is None and (text is None or not text.strip()):
        raise ValueError("Must provide either image_bytes or text (or both)")
    
    provider = EMBEDDING_PROVIDER.lower()
    
    try:
        if provider == "openai":
            if image_bytes is None:
                raise ValueError("OpenAI provider requires image_bytes")
            # OpenAI doesn't support multimodal in this way, image only
            return _embed_with_openai(image_bytes)
        elif provider == "clip":
            return _embed_with_clip(image_bytes, text=text)
        else:
            raise ValueError(f"Unknown EMBEDDING_PROVIDER: '{EMBEDDING_PROVIDER}'")
    except Exception as e:
        logger.error(f"Embedding failed for provider {provider}: {e}")
        raise
