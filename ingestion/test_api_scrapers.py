#!/usr/bin/env python3
"""
Test all marketplace API scrapers to verify structured metadata extraction.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

import os
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from depop_api_scraper import scrape_depop_api
from grailed_api_scraper import scrape_grailed_api
from vinted_api_scraper import scrape_vinted_api

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_scrapers():
    """Test all three scrapers with a simple search term"""
    
    test_term = "nike jacket"
    max_items = 10  # Small test batch
    
    logger.info("="*80)
    logger.info("🧪 TESTING MARKETPLACE API SCRAPERS")
    logger.info("="*80)
    logger.info(f"Search term: '{test_term}'")
    logger.info(f"Max items per platform: {max_items}")
    print()
    
    # Test Depop
    logger.info("1️⃣ Testing Depop API...")
    try:
        depop_items = await scrape_depop_api(test_term, max_items=max_items)
        logger.info(f"✅ Depop: Scraped {len(depop_items)} items")
        
        if depop_items:
            sample = depop_items[0]
            logger.info(f"\n📦 Sample Depop item:")
            logger.info(f"   Title: {sample['title']}")
            logger.info(f"   Brand: {sample['brand']}")
            logger.info(f"   Category: {sample['category']}")
            logger.info(f"   Color: {sample['color']}")
            logger.info(f"   Price: ${sample['price']}")
            logger.info(f"   Condition: {sample['condition']}")
            logger.info(f"   Size: {sample['size']}")
    except Exception as e:
        logger.error(f"❌ Depop failed: {e}")
        depop_items = []
    
    print()
    
    # Test Grailed
    logger.info("2️⃣ Testing Grailed API...")
    try:
        grailed_items = await scrape_grailed_api(test_term, max_items=max_items)
        logger.info(f"✅ Grailed: Scraped {len(grailed_items)} items")
        
        if grailed_items:
            sample = grailed_items[0]
            logger.info(f"\n📦 Sample Grailed item:")
            logger.info(f"   Title: {sample['title']}")
            logger.info(f"   Brand: {sample['brand']}")
            logger.info(f"   Category: {sample['category']}")
            logger.info(f"   Color: {sample['color']}")
            logger.info(f"   Price: ${sample['price']}")
            logger.info(f"   Condition: {sample['condition']}")
            logger.info(f"   Size: {sample['size']}")
    except Exception as e:
        logger.error(f"❌ Grailed failed: {e}")
        grailed_items = []
    
    print()
    
    # Test Vinted
    logger.info("3️⃣ Testing Vinted API...")
    try:
        vinted_items = await scrape_vinted_api(test_term, max_items=max_items)
        logger.info(f"✅ Vinted: Scraped {len(vinted_items)} items")
        
        if vinted_items:
            sample = vinted_items[0]
            logger.info(f"\n📦 Sample Vinted item:")
            logger.info(f"   Title: {sample['title']}")
            logger.info(f"   Brand: {sample['brand']}")
            logger.info(f"   Category: {sample['category']}")
            logger.info(f"   Color: {sample['color']}")
            logger.info(f"   Price: ${sample['price']}")
            logger.info(f"   Condition: {sample['condition']}")
            logger.info(f"   Size: {sample['size']}")
    except Exception as e:
        logger.error(f"❌ Vinted failed: {e}")
        vinted_items = []
    
    print()
    logger.info("="*80)
    logger.info("📊 TEST RESULTS")
    logger.info("="*80)
    logger.info(f"Depop:   {len(depop_items):>3} items")
    logger.info(f"Grailed: {len(grailed_items):>3} items")
    logger.info(f"Vinted:  {len(vinted_items):>3} items")
    logger.info(f"TOTAL:   {len(depop_items + grailed_items + vinted_items):>3} items")
    
    # Check data quality
    all_items = depop_items + grailed_items + vinted_items
    
    if all_items:
        with_brand = sum(1 for item in all_items if item['brand'] and item['brand'] != 'Unknown')
        with_category = sum(1 for item in all_items if item['category'] and item['category'] != 'other')
        with_color = sum(1 for item in all_items if item['color'] and item['color'] != 'unknown')
        
        total = len(all_items)
        logger.info("")
        logger.info("📈 Data Quality:")
        logger.info(f"   Items with brand:    {with_brand}/{total} ({100*with_brand/total:.1f}%)")
        logger.info(f"   Items with category: {with_category}/{total} ({100*with_category/total:.1f}%)")
        logger.info(f"   Items with color:    {with_color}/{total} ({100*with_color/total:.1f}%)")
        
        if with_brand/total >= 0.8 and with_category/total >= 0.8 and with_color/total >= 0.7:
            logger.info("\n✅ Data quality looks good! Ready for production scraping.")
        else:
            logger.warning("\n⚠️  Data quality below target. May need to improve mappings.")
    
    logger.info("="*80)
    
    return all_items


if __name__ == "__main__":
    result = asyncio.run(test_scrapers())
    sys.exit(0 if result else 1)
