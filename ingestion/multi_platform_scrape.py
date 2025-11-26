#!/usr/bin/env python3
"""
Multi-platform fashion scraper - scrapes Depop, Grailed, AND Vinted simultaneously.
Builds massive diverse dataset from multiple marketplaces.
"""
import asyncio
import logging
import random
import sys
import os
from pathlib import Path
from typing import Dict, Any

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from depop_scraper_working import scrape_depop_working, save_items as save_depop_items
from grailed_scraper import scrape_grailed, save_items as save_grailed_items
from vinted_scraper import scrape_vinted, save_items as save_vinted_items

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Comprehensive search terms across all platforms
SEARCH_TERMS = [
    # Shorts & Summer
    "jorts", "denim shorts", "cargo shorts", "swim shorts",
    "vintage swim trunks", "patagonia baggies", "board shorts",
    
    # Cargo & Utility
    "cargo pants", "cargo shorts", "tactical pants", 
    "utility pants", "work pants",
    
    # Brands - Carhartt
    "carhartt jacket", "carhartt pants", "carhartt overalls",
    "carhartt vest", "carhartt beanie",
    
    # Brands - Arc'teryx
    "arcteryx jacket", "arcteryx shell", "arcteryx fleece",
    "arcteryx vest", "arcteryx gore tex",
    
    # Technical/Outdoor
    "patagonia fleece", "patagonia synchilla", "north face fleece",
    "columbia jacket", "outdoor gear", "hiking pants",
    
    # Bottoms
    "baggy jeans", "wide leg jeans", "vintage levis",
    "dickies pants", "corduroy pants",
    
    # Tops
    "vintage tee", "band tee", "oversized hoodie",
    "fleece jacket", "windbreaker", "flannel shirt"
]


async def scrape_all_platforms(
    search_term: str,
    items_per_platform: int = 30
) -> Dict[str, Any]:
    """
    Scrape a single search term across ALL platforms simultaneously.
    
    Args:
        search_term: What to search for
        items_per_platform: Max items per platform
    
    Returns:
        Dictionary with results from each platform
    """
    logger.info(f"🔍 Searching all platforms for: '{search_term}'")
    
    # Run all scrapers in parallel
    results = await asyncio.gather(
        scrape_depop_working(search_term, max_items=items_per_platform),
        scrape_grailed(search_term, max_items=items_per_platform),
        scrape_vinted(search_term, max_items=items_per_platform),
        return_exceptions=True
    )
    
    depop_items, grailed_items, vinted_items = results
    
    # Handle exceptions
    if isinstance(depop_items, Exception):
        logger.error(f"Depop failed: {depop_items}")
        depop_items = []
    if isinstance(grailed_items, Exception):
        logger.error(f"Grailed failed: {grailed_items}")
        grailed_items = []
    if isinstance(vinted_items, Exception):
        logger.error(f"Vinted failed: {vinted_items}")
        vinted_items = []
    
    # Save all items
    depop_result = save_depop_items(depop_items) if depop_items else {'saved': 0, 'failed': 0}
    grailed_result = save_grailed_items(grailed_items) if grailed_items else {'saved': 0, 'failed': 0}
    vinted_result = save_vinted_items(vinted_items) if vinted_items else {'saved': 0, 'failed': 0}
    
    total_saved = depop_result['saved'] + grailed_result['saved'] + vinted_result['saved']
    
    logger.info(f"  ✓ Depop: {depop_result['saved']} | Grailed: {grailed_result['saved']} | Vinted: {vinted_result['saved']} → Total: {total_saved}")
    
    return {
        'search_term': search_term,
        'depop': depop_result,
        'grailed': grailed_result,
        'vinted': vinted_result,
        'total_saved': total_saved
    }


async def multi_platform_scrape(
    items_per_platform: int = 30,
    max_searches: int = 10
):
    """
    Comprehensive multi-platform scrape.
    
    Args:
        items_per_platform: Items to scrape per platform per search
        max_searches: Number of search terms to process
    """
    logger.info("="*80)
    logger.info("🌍 MULTI-PLATFORM FASHION SCRAPER")
    logger.info("="*80)
    logger.info(f"Platforms: Depop + Grailed + Vinted")
    logger.info(f"Search terms: {min(len(SEARCH_TERMS), max_searches)}")
    logger.info(f"Items per platform per search: {items_per_platform}")
    logger.info(f"Expected total: ~{min(len(SEARCH_TERMS), max_searches) * items_per_platform * 3} items")
    logger.info("="*80)
    print()
    
    total_saved = 0
    platform_totals = {'depop': 0, 'grailed': 0, 'vinted': 0}
    
    for idx, search_term in enumerate(SEARCH_TERMS[:max_searches], 1):
        logger.info(f"[{idx}/{max_searches}] '{search_term}'")
        
        try:
            result = await scrape_all_platforms(search_term, items_per_platform)
            
            total_saved += result['total_saved']
            platform_totals['depop'] += result['depop']['saved']
            platform_totals['grailed'] += result['grailed']['saved']
            platform_totals['vinted'] += result['vinted']['saved']
            
            # Delay between searches
            if idx < max_searches:
                delay = random.uniform(5, 10)
                logger.info(f"  💤 Waiting {delay:.1f}s...")
                await asyncio.sleep(delay)
            
            print()
            
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            print()
            continue
    
    # Final summary
    logger.info("="*80)
    logger.info("📊 MULTI-PLATFORM SCRAPE COMPLETE")
    logger.info("="*80)
    logger.info(f"Total items saved: {total_saved}")
    logger.info(f"")
    logger.info(f"Breakdown by platform:")
    logger.info(f"  Depop:   {platform_totals['depop']:4} items")
    logger.info(f"  Grailed: {platform_totals['grailed']:4} items")
    logger.info(f"  Vinted:  {platform_totals['vinted']:4} items")
    logger.info("="*80)
    logger.info("✅ Next step: python3 embed_items.py all")
    logger.info("="*80)
    
    return total_saved


async def main():
    """Run multi-platform scrape."""
    import sys
    
    # Parse arguments
    items_per_platform = 30  # default
    max_searches = 10  # default
    
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit():
            max_searches = int(sys.argv[1])
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            items_per_platform = int(sys.argv[2])
    
    logger.info(f"Configuration: {max_searches} searches, {items_per_platform} items/platform")
    print()
    
    try:
        total = await multi_platform_scrape(
            items_per_platform=items_per_platform,
            max_searches=max_searches
        )
        sys.exit(0 if total > 0 else 1)
    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Interrupted! Progress has been saved.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
