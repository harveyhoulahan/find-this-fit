#!/usr/bin/env python3
"""
Quick test of visual metadata extraction with a single URL.
No scraping needed - just paste an image URL.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from visual_metadata_extractor import (
    extract_visual_metadata,
    classify_with_clip,
    _download_image,
    BRAND_CANDIDATES,
    CATEGORY_CANDIDATES,
    COLOR_CANDIDATES
)

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def test_visual_extraction(image_url: str):
    """Test visual metadata extraction on a single image."""
    
    logger.info("="*70)
    logger.info("🧪 TESTING VISUAL METADATA EXTRACTION")
    logger.info("="*70)
    logger.info(f"\nImage URL: {image_url}")
    
    # Download image
    logger.info("\n📥 Downloading image...")
    image_bytes = _download_image(image_url, timeout=15)
    
    if not image_bytes:
        logger.error("❌ Failed to download image")
        return False
    
    logger.info(f"✓ Downloaded {len(image_bytes)} bytes")
    
    # Extract metadata
    logger.info("\n🔍 Extracting visual metadata...")
    metadata = extract_visual_metadata(image_bytes, min_confidence=0.25)
    
    logger.info("\n" + "="*70)
    logger.info("📊 RESULTS")
    logger.info("="*70)
    logger.info(f"  Brand:    {metadata.get('brand') or 'Not detected'}")
    logger.info(f"  Category: {metadata.get('category') or 'Not detected'}")
    logger.info(f"  Color:    {metadata.get('color') or 'Not detected'}")
    logger.info(f"  Style:    {metadata.get('style') or 'Not detected'}")
    
    # Show detailed predictions
    logger.info("\n" + "="*70)
    logger.info("🎯 DETAILED PREDICTIONS (Top 5)")
    logger.info("="*70)
    
    logger.info("\nBrand predictions:")
    brand_results = classify_with_clip(image_bytes, BRAND_CANDIDATES, template="a {} product", top_k=5)
    for label, conf in brand_results:
        logger.info(f"  {label:25} {conf:.3f} {'⭐️' if conf >= 0.25 else ''}")
    
    logger.info("\nCategory predictions:")
    category_results = classify_with_clip(image_bytes, CATEGORY_CANDIDATES, template="a photo of a {}", top_k=5)
    for label, conf in category_results:
        logger.info(f"  {label:25} {conf:.3f} {'⭐️' if conf >= 0.25 else ''}")
    
    logger.info("\nColor predictions:")
    color_results = classify_with_clip(image_bytes, COLOR_CANDIDATES, template="a {} item", top_k=5)
    for label, conf in color_results:
        logger.info(f"  {label:25} {conf:.3f} {'⭐️' if conf >= 0.20 else ''}")
    
    logger.info("\n" + "="*70)
    logger.info("✅ Test complete!")
    logger.info("="*70)
    
    return True


if __name__ == "__main__":
    # Test with a default image or user-provided URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default test image: Nike jacket from Grailed
        url = "https://process.fs.grailed.com/AJdAgnqCST4iPtnUxiGtTz/auto_image/cache=expiry:max/rotate=deg:exif/resize=height:1760,fit:scale/output=quality:70/compress/https://cdn.fs.grailed.com/api/file/xMYU27nTR6GOCPNpvWqg"
        logger.info("No URL provided, using default test image")
        logger.info("Usage: python3 test_visual_quick.py <image_url>")
        logger.info("")
    
    try:
        success = test_visual_extraction(url)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
