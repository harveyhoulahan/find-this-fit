#!/usr/bin/env python3
"""Quick test of Depop with visual enhancement."""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from depop_scraper_working import scrape_depop_working

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_depop():
    """Test Depop scraper with visual enhancement."""
    logger.info("="*70)
    logger.info("🧪 TESTING DEPOP WITH VISUAL ENHANCEMENT")
    logger.info("="*70)
    
    items = await scrape_depop_working("nike jacket", max_items=10)
    
    if not items:
        logger.error("Failed to scrape items")
        return
    
    logger.info(f"\n✓ Scraped {len(items)} items")
    
    # Analyze
    total = len(items)
    has_brand = sum(1 for i in items if i.get('brand') and i['brand'] != 'Unknown')
    has_category = sum(1 for i in items if i.get('category') and i['category'] != 'other')
    has_color = sum(1 for i in items if i.get('color') and i['color'] != 'unknown')
    
    logger.info("\n" + "="*70)
    logger.info("📊 RESULTS")
    logger.info("="*70)
    logger.info(f"Brand:    {has_brand}/{total} ({100*has_brand/total:.1f}%)")
    logger.info(f"Category: {has_category}/{total} ({100*has_category/total:.1f}%)")
    logger.info(f"Color:    {has_color}/{total} ({100*has_color/total:.1f}%)")
    
    logger.info("\n📦 Sample items:")
    for item in items[:5]:
        logger.info(f"  {item['title'][:40]}")
        logger.info(f"    Brand: {item.get('brand', 'N/A'):15} Category: {item.get('category', 'N/A'):12} Color: {item.get('color', 'N/A')}")
    
    # Check if we pass thresholds
    logger.info("\n" + "="*70)
    if has_category / total >= 0.60 and has_color / total >= 0.40:
        logger.info("✅ PASS - Visual enhancement is working!")
    else:
        logger.warning("⚠️  Still need improvement")
    logger.info("="*70)


if __name__ == "__main__":
    asyncio.run(test_depop())
