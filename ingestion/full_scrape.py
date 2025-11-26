"""
Full Depop scrape across multiple clothing categories.
Builds a diverse dataset for training accurate fashion search models.
"""
import asyncio
import logging
import random
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from depop_scraper_working import scrape_depop_working, save_items

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Comprehensive search terms for diverse fashion dataset
SEARCH_CATEGORIES = [
    # Tops
    "vintage tee",
    "graphic tshirt",
    "band tee",
    "crop top",
    "vintage hoodie",
    "sweater",
    "flannel shirt",
    
    # Bottoms
    "denim jacket",
    "cargo pants",
    "baggy jeans",
    "wide leg jeans",
    "vintage levis",
    "corduroy pants",
    
    # Outerwear
    "leather jacket",
    "puffer jacket",
    "windbreaker",
    "bomber jacket",
    
    # Shoes & Accessories
    "vintage sneakers",
    "new balance",
    "bucket hat",
    "beanie",
    
    # Specific styles
    "y2k",
    "streetwear",
    "grunge",
    "90s vintage",
    "oversized"
]


async def full_scrape(items_per_category: int = 30, max_scrolls: int = 3):
    """
    Comprehensive scrape across all categories.
    
    Args:
        items_per_category: Max items to scrape per search term (30=quick, 100=medium, 500=large)
        max_scrolls: Number of scroll attempts (3=quick, 10=medium, 50=deep)
                    Each scroll loads ~24 more items
    """
    logger.info("="*70)
    logger.info("🚀 FULL DEPOP SCRAPE - COMPREHENSIVE DATASET BUILD")
    logger.info("="*70)
    logger.info(f"Categories: {len(SEARCH_CATEGORIES)}")
    logger.info(f"Items per category: {items_per_category}")
    logger.info(f"Max scrolls: {max_scrolls}")
    logger.info(f"Expected total: ~{len(SEARCH_CATEGORIES) * items_per_category} items")
    logger.info("="*70)
    print()
    
    total_scraped = 0
    total_saved = 0
    category_results = []
    
    for idx, search_term in enumerate(SEARCH_CATEGORIES, 1):
        logger.info(f"[{idx}/{len(SEARCH_CATEGORIES)}] Scraping: '{search_term}'")
        
        try:
            items = await scrape_depop_working(search_term, max_items=items_per_category)
            
            if items:
                result = save_items(items)
                total_scraped += len(items)
                total_saved += result['saved']
                
                category_results.append({
                    'category': search_term,
                    'scraped': len(items),
                    'saved': result['saved'],
                    'failed': result['failed']
                })
                
                logger.info(f"  ✓ Scraped: {len(items)} | Saved: {result['saved']} | Failed: {result['failed']}")
                
                # Show 2 sample items
                for item in items[:2]:
                    logger.info(f"    • {item['title'][:50]}... - ${item['price']}")
            else:
                logger.warning(f"  ⚠️  No items found for '{search_term}'")
                category_results.append({
                    'category': search_term,
                    'scraped': 0,
                    'saved': 0,
                    'failed': 0
                })
            
            # Respectful delay between categories (3-8 seconds)
            if idx < len(SEARCH_CATEGORIES):
                delay = random.uniform(3, 8)
                logger.info(f"  💤 Waiting {delay:.1f}s before next category...")
                await asyncio.sleep(delay)
            
            print()
            
        except Exception as e:
            logger.error(f"  ❌ Error scraping '{search_term}': {e}")
            category_results.append({
                'category': search_term,
                'scraped': 0,
                'saved': 0,
                'failed': 0
            })
            print()
            continue
    
    # Final summary
    logger.info("="*70)
    logger.info("📊 SCRAPE COMPLETE - SUMMARY")
    logger.info("="*70)
    logger.info(f"Total items scraped: {total_scraped}")
    logger.info(f"Total items saved to DB: {total_saved}")
    logger.info(f"Success rate: {(total_saved/total_scraped*100) if total_scraped > 0 else 0:.1f}%")
    logger.info("="*70)
    print()
    
    # Category breakdown
    logger.info("Category Breakdown:")
    logger.info("-"*70)
    for result in category_results:
        if result['saved'] > 0:
            logger.info(f"  {result['category']:25} → {result['saved']:3} items")
    
    logger.info("="*70)
    logger.info(f"✅ Dataset ready with {total_saved} unique items!")
    logger.info("Next step: Run embedding generation (embed_items.py)")
    logger.info("="*70)
    
    return total_saved


async def main():
    """Run full scrape."""
    try:
        # CONFIGURE SCRAPE SIZE HERE:
        # - items_per_category: 30 (quick test), 100 (medium), 500 (large), 0 (unlimited)
        # - max_scrolls: 3 (quick), 10 (medium), 50 (deep scrape)
        
        import sys
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()
            if mode == "quick":
                items_per_cat, scrolls = 30, 3
            elif mode == "medium":
                items_per_cat, scrolls = 100, 10
            elif mode == "large":
                items_per_cat, scrolls = 500, 50
            else:
                items_per_cat, scrolls = 30, 3
        else:
            # Default: quick test
            items_per_cat, scrolls = 30, 3
        
        logger.info(f"Scrape mode: {items_per_cat} items/category, {scrolls} scrolls")
        total = await full_scrape(items_per_category=items_per_cat, max_scrolls=scrolls)
        sys.exit(0 if total > 0 else 1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Scrape interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
