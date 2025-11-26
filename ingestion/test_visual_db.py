#!/usr/bin/env python3
"""
Test visual metadata extraction using items from the database.
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from db import fetch_all_sync
from visual_metadata_extractor import extract_visual_metadata, _download_image, classify_with_clip
from visual_metadata_extractor import BRAND_CANDIDATES, CATEGORY_CANDIDATES, COLOR_CANDIDATES
from metadata_extractor import extract_brand, extract_category, extract_color

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def test_db_items(limit: int = 3):
    """Test visual extraction on items from database."""
    
    logger.info("="*70)
    logger.info("🧪 TESTING VISUAL METADATA ON DATABASE ITEMS")
    logger.info("="*70)
    
    # Get some items without complete metadata
    items = fetch_all_sync("""
        SELECT id, source, external_id, title, image_url, brand, category, color
        FROM fashion_items
        WHERE image_url IS NOT NULL
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))
    
    if not items:
        logger.error("No items found in database")
        return
    
    logger.info(f"\nTesting {len(items)} items from database\n")
    
    for idx, item in enumerate(items, 1):
        logger.info("="*70)
        logger.info(f"Item {idx}/{len(items)}")
        logger.info("="*70)
        logger.info(f"Source:   {item['source']}")
        logger.info(f"Title:    {item['title'][:60]}")
        logger.info(f"Image:    {item['image_url'][:60]}...")
        
        # Current metadata from text extraction
        logger.info(f"\n📝 Current (text-based) metadata:")
        logger.info(f"  Brand:    {item['brand']}")
        logger.info(f"  Category: {item['category']}")
        logger.info(f"  Color:    {item['color']}")
        
        # Download image
        logger.info(f"\n📥 Downloading image...")
        image_bytes = _download_image(item['image_url'], timeout=15)
        
        if not image_bytes:
            logger.error("  ❌ Failed to download")
            continue
        
        logger.info(f"  ✓ Downloaded {len(image_bytes)/1024:.1f} KB")
        
        # Extract visual metadata
        logger.info(f"\n🔍 Running CLIP visual analysis...")
        try:
            visual_meta = extract_visual_metadata(image_bytes, min_confidence=0.25)
            
            logger.info(f"\n🎨 Visual predictions:")
            logger.info(f"  Brand:    {visual_meta.get('brand') or 'Not detected'}")
            logger.info(f"  Category: {visual_meta.get('category') or 'Not detected'}")
            logger.info(f"  Color:    {visual_meta.get('color') or 'Not detected'}")
            logger.info(f"  Style:    {visual_meta.get('style') or 'Not detected'}")
            
            # Show top predictions
            logger.info(f"\n📊 Top predictions:")
            
            logger.info("  Brand (top 3):")
            brand_preds = classify_with_clip(image_bytes, BRAND_CANDIDATES[:20], template="a {} product", top_k=3)
            for label, conf in brand_preds:
                logger.info(f"    {label:20} {conf:.3f}")
            
            logger.info("  Category (top 3):")
            cat_preds = classify_with_clip(image_bytes, CATEGORY_CANDIDATES, template="a photo of a {}", top_k=3)
            for label, conf in cat_preds:
                logger.info(f"    {label:20} {conf:.3f}")
            
            logger.info("  Color (top 3):")
            color_preds = classify_with_clip(image_bytes, COLOR_CANDIDATES, template="a {} item", top_k=3)
            for label, conf in color_preds:
                logger.info(f"    {label:20} {conf:.3f}")
            
            # Highlight improvements
            improvements = []
            if item['color'] == 'unknown' and visual_meta.get('color'):
                improvements.append(f"Color: unknown → {visual_meta['color']} ✨")
            if item['brand'] == 'Unknown' and visual_meta.get('brand'):
                improvements.append(f"Brand: Unknown → {visual_meta['brand']} ✨")
            if item['category'] == 'other' and visual_meta.get('category'):
                improvements.append(f"Category: other → {visual_meta['category']} ✨")
            
            if improvements:
                logger.info(f"\n💡 Improvements:")
                for imp in improvements:
                    logger.info(f"  • {imp}")
            else:
                logger.info(f"\n✓ Text metadata was already good!")
        
        except Exception as e:
            logger.error(f"❌ Visual extraction failed: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info("")
    
    logger.info("="*70)
    logger.info("✅ Test complete!")
    logger.info("="*70)


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    test_db_items(limit)
