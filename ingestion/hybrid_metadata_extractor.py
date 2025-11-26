"""
Hybrid Metadata Extraction - Combines text-based AND visual (CLIP) extraction.

Strategy:
1. Extract metadata from text (title/description) - FAST, works offline
2. Extract metadata from image using CLIP - ACCURATE, but slower
3. Combine results intelligently (prefer high-confidence predictions)

This gives us the best of both worlds:
- Text extraction is fast and works when images fail to load
- Visual extraction is more accurate and catches details not in text
"""
import logging
from typing import Dict, Optional
from pathlib import Path
import sys

# Add modules to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from metadata_extractor import (
    extract_brand as extract_brand_text,
    extract_category as extract_category_text,
    extract_color as extract_color_text,
    extract_condition as extract_condition_text,
    extract_size as extract_size_text
)

try:
    from visual_metadata_extractor import extract_visual_metadata, _download_image
    VISUAL_AVAILABLE = True
except ImportError:
    VISUAL_AVAILABLE = False
    logging.warning("Visual metadata extraction not available - install sentence-transformers")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def enhance_item_metadata_hybrid(
    item: dict,
    use_visual: bool = True,
    visual_confidence: float = 0.30,
    prefer_visual_for: list = None
) -> dict:
    """
    Enhanced metadata extraction using BOTH text and visual analysis.
    
    Args:
        item: Item dict with 'title', 'description', and optionally 'image_url'
        use_visual: Whether to use CLIP visual extraction (slower but more accurate)
        visual_confidence: Minimum confidence for visual predictions (0-1)
        prefer_visual_for: List of fields to prefer visual over text ['color', 'category']
                          Color especially benefits from visual analysis!
    
    Returns:
        Enhanced item with metadata
        
    Strategy:
        - Brand: Text first (usually in title), visual as fallback
        - Category: Text first (fast), visual for validation
        - Color: VISUAL PREFERRED (images don't lie!)
        - Condition: Text only (visual can't reliably detect wear)
        - Size: Text only (not visible in images)
    """
    if prefer_visual_for is None:
        prefer_visual_for = ['color']  # Color benefits most from visual
    
    # Step 1: Text-based extraction (always fast)
    text = f"{item.get('title', '')} {item.get('description', '')}"
    
    text_brand = extract_brand_text(text)
    text_category = extract_category_text(text)
    text_color = extract_color_text(text)
    text_condition = extract_condition_text(text)
    text_size = extract_size_text(text)
    
    # Initialize with text results
    item['brand'] = text_brand
    item['category'] = text_category
    item['color'] = text_color
    item['condition'] = text_condition
    item['size'] = text_size
    
    # Step 2: Visual extraction (if enabled and available)
    if use_visual and VISUAL_AVAILABLE and item.get('image_url'):
        try:
            # Download image if needed
            image_bytes = item.get('image_bytes')
            if not image_bytes:
                image_bytes = _download_image(item['image_url'], timeout=10)
            
            if image_bytes:
                # Get visual predictions
                visual_meta = extract_visual_metadata(image_bytes, min_confidence=visual_confidence)
                
                # Merge results intelligently
                for field in ['brand', 'category', 'color']:
                    visual_value = visual_meta.get(field)
                    text_value = item.get(field)
                    
                    if not visual_value:
                        continue  # No visual prediction
                    
                    # Always prefer visual for specified fields (e.g., color)
                    if field in prefer_visual_for:
                        item[field] = visual_value
                        logger.debug(f"Using visual {field}: {visual_value}")
                    
                    # Use visual if text extraction failed
                    elif text_value in ['Unknown', 'unknown', 'other', None]:
                        item[field] = visual_value
                        logger.debug(f"Visual filled missing {field}: {visual_value}")
                    
                    # Keep text result (it's already set)
                    else:
                        logger.debug(f"Keeping text {field}: {text_value} (visual: {visual_value})")
                
                # Store visual style if detected
                if visual_meta.get('style'):
                    item['style'] = visual_meta['style']
        
        except Exception as e:
            logger.warning(f"Visual extraction failed for {item.get('external_id')}: {e}")
            # Fall back to text-only results
    
    return item


# Backward compatibility: make this the default
def enhance_item_metadata(item: dict, use_visual: bool = False) -> dict:
    """
    Default metadata enhancer - text-based by default for speed.
    
    Set use_visual=True for better accuracy (especially color detection).
    """
    return enhance_item_metadata_hybrid(item, use_visual=use_visual)


if __name__ == '__main__':
    # Test with a real item
    test_item = {
        'title': 'Nike Acg Reversible Vest Purple Black Size S',
        'description': 'Excellent condition vintage vest',
        'image_url': 'https://example.com/image.jpg'  # Replace with real URL
    }
    
    logger.info("Testing text-only extraction:")
    result_text = enhance_item_metadata(test_item.copy(), use_visual=False)
    logger.info(f"  Brand: {result_text['brand']}")
    logger.info(f"  Category: {result_text['category']}")
    logger.info(f"  Color: {result_text['color']}")
    logger.info(f"  Condition: {result_text['condition']}")
    logger.info(f"  Size: {result_text['size']}")
    
    if VISUAL_AVAILABLE:
        logger.info("\nTesting hybrid (text + visual) extraction:")
        logger.info("  (requires valid image_url to test)")
