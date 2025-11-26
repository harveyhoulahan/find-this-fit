"""
Visual Metadata Extraction using CLIP.

Uses zero-shot classification with CLIP to extract brand, category, 
color, and style directly from product images - much more reliable 
than text parsing alone!

CLIP can identify visual features that aren't in the title/description.
For example, it can detect "navy blue" even if the seller wrote "dark jacket".
"""
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from io import BytesIO
import numpy as np
from PIL import Image
import requests

# Add backend to path
project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

from embeddings import _get_clip_model

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Brand templates for zero-shot classification
BRAND_CANDIDATES = [
    'Nike', 'Adidas', 'Supreme', 'Gucci', 'Prada', 'Louis Vuitton',
    'The North Face', 'Patagonia', "Arc'teryx", 'Carhartt',
    'Ralph Lauren', 'Tommy Hilfiger', 'Calvin Klein',
    'Vans', 'Converse', 'Jordan', 'New Balance',
    'Unbranded', 'Vintage', 'Unknown brand'
]

# Category templates
CATEGORY_CANDIDATES = [
    'jacket', 'coat', 'hoodie', 'sweater', 'sweatshirt',
    't-shirt', 'shirt', 'jeans', 'pants', 'shorts',
    'dress', 'skirt', 'sneakers', 'boots', 'shoes',
    'bag', 'backpack', 'hat', 'accessories'
]

# Color templates
COLOR_CANDIDATES = [
    'black', 'white', 'grey', 'navy blue', 'blue',
    'red', 'pink', 'green', 'olive green', 'yellow',
    'orange', 'purple', 'brown', 'tan', 'beige',
    'multicolor', 'camo', 'printed'
]

# Style/condition templates
STYLE_CANDIDATES = [
    'vintage', 'retro', 'modern', 'minimalist', 'streetwear',
    'athletic', 'formal', 'casual', 'luxury'
]


def _download_image(url: str, timeout: int = 10) -> Optional[bytes]:
    """Download image from URL."""
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
    return None


def classify_with_clip(
    image_bytes: bytes,
    candidates: List[str],
    template: str = "a photo of {}",
    top_k: int = 3
) -> List[Tuple[str, float]]:
    """
    Zero-shot classification using CLIP.
    
    Args:
        image_bytes: Raw image data
        candidates: List of possible labels
        template: Text template (e.g., "a photo of {}")
        top_k: Return top K predictions
        
    Returns:
        List of (label, confidence) tuples, sorted by confidence descending
    """
    try:
        model = _get_clip_model()
        
        # Load image
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        
        # Create text prompts
        texts = [template.format(candidate) for candidate in candidates]
        
        # Get embeddings
        image_emb = model.encode(image, normalize_embeddings=True)
        text_embs = model.encode(texts, normalize_embeddings=True)
        
        # Compute similarities (cosine similarity since normalized)
        similarities = np.dot(text_embs, image_emb)
        
        # Get top K
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = [(candidates[i], float(similarities[i])) for i in top_indices]
        
        return results
        
    except Exception as e:
        logger.error(f"CLIP classification failed: {e}")
        return []


def extract_visual_metadata(
    image_bytes: bytes,
    min_confidence: float = 0.25
) -> Dict[str, Optional[str]]:
    """
    Extract brand, category, color, and style from image using CLIP.
    
    Args:
        image_bytes: Raw image data
        min_confidence: Minimum confidence threshold (0-1)
        
    Returns:
        Dict with keys: brand, category, color, style
        Values are None if confidence is below threshold
    """
    metadata = {
        'brand': None,
        'category': None,
        'color': None,
        'style': None
    }
    
    try:
        # Classify brand
        brand_results = classify_with_clip(
            image_bytes,
            BRAND_CANDIDATES,
            template="a {} product",
            top_k=1
        )
        if brand_results and brand_results[0][1] >= min_confidence:
            brand = brand_results[0][0]
            if brand not in ['Unbranded', 'Unknown brand', 'Vintage']:
                metadata['brand'] = brand
        
        # Classify category
        category_results = classify_with_clip(
            image_bytes,
            CATEGORY_CANDIDATES,
            template="a photo of a {}",
            top_k=1
        )
        if category_results and category_results[0][1] >= min_confidence:
            metadata['category'] = category_results[0][0]
        
        # Classify color (use lower threshold - colors are harder)
        color_results = classify_with_clip(
            image_bytes,
            COLOR_CANDIDATES,
            template="a {} item",
            top_k=1
        )
        if color_results and color_results[0][1] >= min_confidence * 0.8:  # 20% lower threshold
            color = color_results[0][0].split()[0]  # "navy blue" -> "navy"
            metadata['color'] = color
        
        # Classify style
        style_results = classify_with_clip(
            image_bytes,
            STYLE_CANDIDATES,
            template="{} fashion",
            top_k=1
        )
        if style_results and style_results[0][1] >= min_confidence:
            metadata['style'] = style_results[0][0]
        
    except Exception as e:
        logger.error(f"Visual metadata extraction failed: {e}")
    
    return metadata


def enhance_item_with_visual_metadata(
    item: dict,
    confidence_threshold: float = 0.25,
    prefer_visual: bool = False
) -> dict:
    """
    Enhance item with visual metadata from CLIP.
    
    Args:
        item: Item dict with 'image_url' or 'image_bytes'
        confidence_threshold: Minimum confidence for predictions
        prefer_visual: If True, always use visual predictions. 
                      If False, only fill in missing fields.
                      
    Returns:
        Enhanced item dict
    """
    # Get image
    image_bytes = item.get('image_bytes')
    if not image_bytes and item.get('image_url'):
        image_bytes = _download_image(item['image_url'])
    
    if not image_bytes:
        logger.warning(f"No image available for {item.get('external_id', 'unknown')}")
        return item
    
    # Extract visual metadata
    visual_meta = extract_visual_metadata(image_bytes, confidence_threshold)
    
    # Merge with existing metadata
    if prefer_visual:
        # Always use visual predictions if available
        for key, value in visual_meta.items():
            if value:
                item[key] = value
    else:
        # Only fill in missing fields
        for key, value in visual_meta.items():
            if value and (not item.get(key) or item[key] in ['Unknown', 'unknown', 'other', None]):
                item[key] = value
    
    return item


# Test function
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test visual metadata extraction')
    parser.add_argument('url', help='Image URL to test')
    parser.add_argument('--confidence', type=float, default=0.25, help='Confidence threshold')
    args = parser.parse_args()
    
    logger.info(f"Testing visual metadata extraction on: {args.url}")
    
    # Download image
    image_bytes = _download_image(args.url)
    if not image_bytes:
        logger.error("Failed to download image")
        sys.exit(1)
    
    # Extract metadata
    metadata = extract_visual_metadata(image_bytes, min_confidence=args.confidence)
    
    logger.info("\n" + "="*70)
    logger.info("VISUAL METADATA EXTRACTION RESULTS")
    logger.info("="*70)
    for key, value in metadata.items():
        logger.info(f"  {key:12} {value or 'N/A'}")
    logger.info("="*70)
    
    # Show detailed predictions for each category
    logger.info("\nDETAILED PREDICTIONS:")
    
    for category_name, candidates in [
        ('Brand', BRAND_CANDIDATES),
        ('Category', CATEGORY_CANDIDATES),
        ('Color', COLOR_CANDIDATES),
        ('Style', STYLE_CANDIDATES)
    ]:
        logger.info(f"\n{category_name}:")
        results = classify_with_clip(image_bytes, candidates, top_k=5)
        for label, conf in results:
            logger.info(f"  {label:20} {conf:.3f}")
