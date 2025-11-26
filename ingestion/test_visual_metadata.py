#!/usr/bin/env python3
"""
Test visual metadata extraction to see the improvement over text-only.

This will:
1. Run text-only metadata extraction
2. Run hybrid (text + visual) metadata extraction  
3. Compare results to show the improvement

Especially useful for color detection!
"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from grailed_scraper import scrape_grailed
from vinted_scraper import scrape_vinted
from hybrid_metadata_extractor import enhance_item_metadata_hybrid

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_metadata_quality(items, extraction_method: str):
    """Analyze metadata quality for a set of items."""
    if not items:
        return
    
    total = len(items)
    has_brand = sum(1 for i in items if i.get('brand') and i['brand'] != 'Unknown')
    has_category = sum(1 for i in items if i.get('category') and i['category'] != 'other')
    has_color = sum(1 for i in items if i.get('color') and i['color'] != 'unknown')
    
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 {extraction_method.upper()} - METADATA QUALITY")
    logger.info(f"{'='*70}")
    logger.info(f"Total items: {total}")
    logger.info(f"")
    logger.info(f"Coverage:")
    logger.info(f"  Brand:    {has_brand}/{total} ({100*has_brand/total:.1f}%)")
    logger.info(f"  Category: {has_category}/{total} ({100*has_category/total:.1f}%)")
    logger.info(f"  Color:    {has_color}/{total} ({100*has_color/total:.1f}%)")
    
    # Show sample items
    logger.info(f"\n📦 Sample items:")
    for item in items[:3]:
        logger.info(f"  • {item['title'][:50]}")
        logger.info(f"    Brand: {item.get('brand', 'N/A'):15} Category: {item.get('category', 'N/A'):12} Color: {item.get('color', 'N/A')}")
    
    return {
        'brand_coverage': has_brand / total,
        'category_coverage': has_category / total,
        'color_coverage': has_color / total
    }


async def test_visual_enhancement():
    """
    Compare text-only vs hybrid metadata extraction.
    """
    logger.info("="*70)
    logger.info("🧪 TESTING VISUAL METADATA ENHANCEMENT")
    logger.info("="*70)
    
    # Scrape some test items
    logger.info("\n🔍 Scraping test items from Grailed...")
    items = await scrape_grailed("nike jacket", max_items=10)
    
    if not items:
        logger.error("Failed to scrape items")
        return
    
    logger.info(f"✓ Scraped {len(items)} items")
    
    # Test 1: Text-only extraction
    logger.info("\n1️⃣  Testing TEXT-ONLY extraction...")
    text_only_items = []
    for item in items:
        enhanced = enhance_item_metadata_hybrid(item.copy(), use_visual=False)
        text_only_items.append(enhanced)
    
    text_stats = analyze_metadata_quality(text_only_items, "Text-Only")
    
    # Test 2: Hybrid (text + visual) extraction
    logger.info("\n2️⃣  Testing HYBRID (text + visual) extraction...")
    logger.info("   (This will be slower as it downloads images and runs CLIP)")
    
    hybrid_items = []
    for idx, item in enumerate(items, 1):
        logger.info(f"   Processing {idx}/{len(items)}...")
        enhanced = enhance_item_metadata_hybrid(
            item.copy(),
            use_visual=True,
            visual_confidence=0.25,
            prefer_visual_for=['color']  # Trust visual for color detection
        )
        hybrid_items.append(enhanced)
    
    hybrid_stats = analyze_metadata_quality(hybrid_items, "Hybrid (Text + Visual)")
    
    # Compare results
    logger.info(f"\n{'='*70}")
    logger.info(f"📈 IMPROVEMENT FROM VISUAL ENHANCEMENT")
    logger.info(f"{'='*70}")
    
    brand_improvement = (hybrid_stats['brand_coverage'] - text_stats['brand_coverage']) * 100
    category_improvement = (hybrid_stats['category_coverage'] - text_stats['category_coverage']) * 100
    color_improvement = (hybrid_stats['color_coverage'] - text_stats['color_coverage']) * 100
    
    logger.info(f"Brand:    {brand_improvement:+.1f}% improvement")
    logger.info(f"Category: {category_improvement:+.1f}% improvement")
    logger.info(f"Color:    {color_improvement:+.1f}% improvement ⭐️")
    logger.info(f"")
    
    # Show specific examples where visual helped
    logger.info("💡 Examples where visual extraction helped:")
    improvements_found = 0
    for text_item, hybrid_item in zip(text_only_items, hybrid_items):
        changes = []
        
        if text_item['color'] == 'unknown' and hybrid_item['color'] != 'unknown':
            changes.append(f"color: {text_item['color']} → {hybrid_item['color']}")
        
        if text_item['category'] == 'other' and hybrid_item['category'] != 'other':
            changes.append(f"category: {text_item['category']} → {hybrid_item['category']}")
        
        if text_item['brand'] == 'Unknown' and hybrid_item['brand'] != 'Unknown':
            changes.append(f"brand: {text_item['brand']} → {hybrid_item['brand']}")
        
        if changes:
            improvements_found += 1
            logger.info(f"\n   {text_item['title'][:60]}")
            for change in changes:
                logger.info(f"      • {change}")
    
    if improvements_found == 0:
        logger.info("   (No improvements in this batch - try with different items)")
    
    logger.info(f"\n{'='*70}")
    logger.info("✅ Test complete!")
    logger.info("   💡 Use visual extraction for better color detection!")
    logger.info(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(test_visual_enhancement())
