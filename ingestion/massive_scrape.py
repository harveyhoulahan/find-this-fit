#!/usr/bin/env python3
"""
MASSIVE DEPOP SCRAPE - Production scale scraping
Scrapes 1000s of items across all categories for building a large fashion dataset.
"""
import asyncio
import logging
import random
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from depop_scraper_working import scrape_depop_working, save_items

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# MASSIVE list of search terms for comprehensive coverage
COMPREHENSIVE_SEARCHES = [
    # Tops - Basics
    "vintage tee", "graphic tshirt", "band tee", "crop top", "tank top",
    "vintage hoodie", "sweatshirt", "sweater", "cardigan", "flannel shirt",
    "button down", "polo shirt", "rugby shirt", "longsleeve tee",
    
    # Tops - Styles
    "y2k top", "90s shirt", "oversized tee", "baby tee", "mesh top",
    "striped shirt", "tie dye", "bleach dye", "distressed tee",
    
    # Bottoms - Jeans
    "baggy jeans", "wide leg jeans", "vintage levis", "501 jeans",
    "bootcut jeans", "flare jeans", "mom jeans", "boyfriend jeans",
    "straight leg jeans", "skinny jeans", "ripped jeans",
    
    # Bottoms - Pants
    "cargo pants", "corduroy pants", "dickies", "work pants",
    "parachute pants", "track pants", "sweatpants", "khakis",
    
    # Bottoms - Shorts/Skirts
    "jean shorts", "cargo shorts", "mini skirt", "midi skirt",
    "maxi skirt", "tennis skirt", "denim skirt",
    
    # Outerwear - Jackets
    "denim jacket", "leather jacket", "bomber jacket", "varsity jacket",
    "puffer jacket", "north face", "patagonia", "windbreaker",
    "harrington jacket", "trucker jacket", "sherpa jacket",
    
    # Outerwear - Coats
    "trench coat", "peacoat", "overcoat", "parka", "fleece jacket",
    
    # Footwear
    "vintage sneakers", "nike", "adidas", "new balance", "converse",
    "vans", "air jordan", "dunk", "air max", "samba", "campus",
    "boots", "doc martens", "timberland", "platform shoes",
    
    # Accessories
    "bucket hat", "beanie", "cap", "snapback", "dad hat",
    "bandana", "scarf", "belt", "sunglasses", "bag", "backpack",
    
    # Styles/Eras
    "y2k", "90s vintage", "80s vintage", "70s vintage",
    "grunge", "punk", "streetwear", "skate", "preppy",
    "minimalist", "maximalist", "cottagecore", "dark academia",
    
    # Brands (high demand)
    "carhartt", "dickies", "levi's", "wrangler", "lee jeans",
    "ralph lauren", "tommy hilfiger", "nautica", "champion",
    "stussy", "supreme", "bape", "palace",
]


async def massive_scrape(
    items_per_search: int = 100,
    total_items_target: int = 5000
):
    """
    Massive scrape to build production-scale dataset.
    
    Args:
        items_per_search: Items to scrape per search term
        total_items_target: Stop after reaching this many total items
    """
    logger.info("="*80)
    logger.info("🚀 MASSIVE DEPOP SCRAPE - PRODUCTION SCALE")
    logger.info("="*80)
    logger.info(f"Search terms: {len(COMPREHENSIVE_SEARCHES)}")
    logger.info(f"Items per search: {items_per_search}")
    logger.info(f"Target total: {total_items_target:,} items")
    logger.info(f"Max possible: {len(COMPREHENSIVE_SEARCHES) * items_per_search:,} items")
    logger.info("="*80)
    logger.info("⚠️  This will take ~2-4 hours. Press Ctrl+C to stop anytime.")
    logger.info("="*80)
    print()
    
    total_saved = 0
    categories_completed = 0
    
    for idx, search_term in enumerate(COMPREHENSIVE_SEARCHES, 1):
        # Check if we've hit target
        if total_items_target > 0 and total_saved >= total_items_target:
            logger.info(f"✅ Reached target of {total_items_target:,} items!")
            break
        
        logger.info(f"[{idx}/{len(COMPREHENSIVE_SEARCHES)}] '{search_term}' (Total: {total_saved:,})")
        
        try:
            items = await scrape_depop_working(search_term, max_items=items_per_search)
            
            if items:
                result = save_items(items)
                total_saved += result['saved']
                categories_completed += 1
                
                logger.info(f"  ✓ +{result['saved']} items (Total: {total_saved:,})")
                
                # Sample
                if items:
                    logger.info(f"    • {items[0]['title'][:50]}... - ${items[0]['price']}")
            else:
                logger.warning(f"  ⚠️  No items")
            
            # Respectful delay
            if idx < len(COMPREHENSIVE_SEARCHES):
                delay = random.uniform(4, 10)
                await asyncio.sleep(delay)
            
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            continue
    
    # Final summary
    logger.info("="*80)
    logger.info("📊 MASSIVE SCRAPE COMPLETE")
    logger.info("="*80)
    logger.info(f"Categories scraped: {categories_completed}/{len(COMPREHENSIVE_SEARCHES)}")
    logger.info(f"Total items saved: {total_saved:,}")
    logger.info(f"Avg items/category: {total_saved/categories_completed if categories_completed > 0 else 0:.1f}")
    logger.info("="*80)
    logger.info("✅ Next step: python3 embed_items.py all")
    logger.info("="*80)
    
    return total_saved


async def main():
    """Run massive scrape."""
    import sys
    
    # Parse arguments
    items_per_search = 100  # default
    target = 5000  # default
    
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit():
            target = int(sys.argv[1])
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            items_per_search = int(sys.argv[2])
    
    try:
        total = await massive_scrape(
            items_per_search=items_per_search,
            total_items_target=target
        )
        sys.exit(0 if total > 0 else 1)
    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Interrupted! Progress has been saved to database.")
        logger.info("You can run embedding generation on what's been scraped so far.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
