#!/usr/bin/env python3
"""
DEPOP-ONLY LUXURY BRAND SCRAPER
Targets high-end fashion brands on Depop only.
"""
import asyncio
import logging
import random
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from depop_scraper_working import scrape_depop_working, save_items as save_depop_items

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# MASSIVE LUXURY & DESIGNER SEARCH TERMS
LUXURY_SEARCHES = [
    # === PRADA ===
    "prada bag", "prada jacket", "prada coat", "prada shoes",
    "prada shirt", "prada sweater", "prada sunglasses", "prada wallet",
    "prada nylon", "prada re-edition", "prada sport",
    
    # === GUCCI ===
    "gucci bag", "gucci belt", "gucci loafers", "gucci sneakers",
    "gucci jacket", "gucci sweater", "gucci shirt", "gucci scarf",
    "gucci sunglasses", "gucci ace", "gucci dionysus", "gucci marmont",
    
    # === MIU MIU ===
    "miu miu bag", "miu miu shoes", "miu miu dress", "miu miu skirt",
    "miu miu ballet flats", "miu miu sunglasses", "miu miu cardigan",
    
    # === ACNE STUDIOS ===
    "acne studios jeans", "acne studios jacket", "acne studios coat",
    "acne studios sweater", "acne studios scarf", "acne studios beanie",
    "acne studios shoes", "acne studios shirt",
    
    # === YOHJI YAMAMOTO ===
    "yohji yamamoto", "y-3", "yohji yamamoto pour homme",
    "yohji yamamoto pants", "yohji yamamoto jacket", "yohji yamamoto coat",
    
    # === COMME DES GARCONS ===
    "comme des garcons", "cdg", "comme des garcons play",
    "cdg homme plus", "comme des garcons shirt", "cdg wallet",
    
    # === RICK OWENS ===
    "rick owens", "rick owens ramones", "rick owens geobasket",
    "rick owens drkshdw", "rick owens jacket", "rick owens pants",
    
    # === CARHARTT ===
    "carhartt wip", "carhartt jacket", "carhartt pants", "carhartt overalls",
    "carhartt detroit jacket", "carhartt vest", "carhartt bag",
    
    # === STONE ISLAND ===
    "stone island", "stone island jacket", "stone island sweater",
    "stone island cargo", "stone island badge",
    
    # === ARC'TERYX ===
    "arcteryx", "arcteryx jacket", "arcteryx shell", "arcteryx veilance",
    "arcteryx fleece", "arcteryx gore tex", "arcteryx beta",
    
    # === PATAGONIA ===
    "patagonia fleece", "patagonia synchilla", "patagonia jacket",
    "patagonia vest", "patagonia bag", "patagonia retro",
    
    # === MAISON MARGIELA ===
    "maison margiela", "margiela tabis", "margiela tabi boots",
    "margiela jacket", "margiela replica sneakers", "margiela sweater",
    
    # === BURBERRY ===
    "burberry trench", "burberry coat", "burberry scarf",
    "burberry jacket", "burberry bag", "burberry shirt",
    
    # === BALENCIAGA ===
    "balenciaga", "balenciaga triple s", "balenciaga bag",
    "balenciaga jacket", "balenciaga hoodie", "balenciaga speed trainer",
    
    # === SAINT LAURENT ===
    "saint laurent", "ysl", "saint laurent jacket",
    "saint laurent boots", "saint laurent bag", "saint laurent jeans",
    
    # === DIOR ===
    "dior", "dior bag", "dior jacket", "dior sweater",
    "dior homme", "dior saddle bag", "dior sunglasses",
    
    # === GIVENCHY ===
    "givenchy", "givenchy jacket", "givenchy sweater",
    "givenchy bag", "givenchy shirt", "givenchy nightingale",
    
    # === LOUIS VUITTON ===
    "louis vuitton bag", "lv bag", "louis vuitton jacket",
    "louis vuitton wallet", "louis vuitton shoes", "lv monogram",
    
    # === BOTTEGA VENETA ===
    "bottega veneta", "bottega veneta bag", "bottega veneta cassette",
    "bottega veneta jacket", "bottega veneta shoes",
    
    # === THE ROW ===
    "the row", "the row bag", "the row jacket", "the row coat",
    
    # === HELMUT LANG ===
    "helmut lang", "helmut lang jeans", "helmut lang jacket",
    "helmut lang pants", "helmut lang vintage",
    
    # === RAF SIMONS ===
    "raf simons", "raf simons jacket", "raf simons sweater",
    "raf simons ozweego", "raf simons shirt",
    
    # === UNDERCOVER ===
    "undercover", "undercover jacket", "undercover pants",
    "undercover sweater", "jun takahashi",
    
    # === ISSEY MIYAKE ===
    "issey miyake", "pleats please", "issey miyake jacket",
    "issey miyake pants", "homme plisse",
    
    # === JIL SANDER ===
    "jil sander", "jil sander jacket", "jil sander coat",
    "jil sander bag", "jil sander pants",
    
    # === CELINE ===
    "celine", "celine bag", "celine jacket", "celine coat",
    "celine sunglasses", "celine shirt",
    
    # === LOEWE ===
    "loewe", "loewe bag", "loewe jacket", "loewe puzzle bag",
    "loewe sweater", "loewe coat",
    
    # === AMI PARIS ===
    "ami paris", "ami jacket", "ami sweater", "ami shirt",
    
    # === A.P.C. ===
    "apc", "apc jeans", "apc jacket", "apc bag",
    "apc sweater", "apc shirt",
    
    # === MARNI ===
    "marni", "marni jacket", "marni bag", "marni shoes",
    "marni sweater", "marni pants",
    
    # === LEMAIRE ===
    "lemaire", "lemaire jacket", "lemaire pants", "lemaire coat",
    "lemaire bag", "lemaire shirt",
    
    # === OUR LEGACY ===
    "our legacy", "our legacy jacket", "our legacy shirt",
    "our legacy pants", "our legacy sweater",
    
    # === ENGINEERED GARMENTS ===
    "engineered garments", "eg jacket", "engineered garments vest",
    "engineered garments pants", "eg bedford",
    
    # === KAPITAL ===
    "kapital", "kapital jacket", "kapital jeans", "kapital pants",
    "kapital shirt", "kapital sweater",
    
    # === VISVIM ===
    "visvim", "visvim fbt", "visvim jacket", "visvim pants",
    "visvim shirt", "visvim shoes",
    
    # === NIKE (vintage & special) ===
    "vintage nike", "nike acg", "nike vintage jacket",
    "nike swoosh", "nike windbreaker", "nike tech fleece",
    
    # === ADIDAS (vintage & special) ===
    "vintage adidas", "adidas vintage jacket", "adidas track jacket",
    "adidas firebird", "adidas originals", "adidas gazelle",
    
    # === SUPREME ===
    "supreme box logo", "supreme jacket", "supreme hoodie",
    "supreme bag", "supreme shirt", "supreme pants",
    
    # === STUSSY ===
    "stussy", "stussy jacket", "stussy hoodie", "stussy shirt",
    "stussy vintage", "stussy fleece",
    
    # === VINTAGE DENIM ===
    "vintage levis", "levis 501", "levis jacket", "levis trucker",
    "vintage wrangler", "vintage lee jeans", "selvedge denim",
    
    # === VINTAGE SPORTSWEAR ===
    "vintage champion", "champion reverse weave", "vintage polo",
    "polo sport", "tommy hilfiger vintage", "nautica vintage",
    
    # === WORKWEAR ===
    "dickies 874", "dickies jacket", "dickies carpenter",
    "ben davis", "red kap", "vintage workwear",
    
    # === MILITARY/SURPLUS ===
    "military surplus", "m65 jacket", "military jacket",
    "army jacket", "cargo pants", "tactical vest",
    
    # === FLEECE & OUTDOOR ===
    "vintage fleece", "north face fleece", "columbia fleece",
    "patagonia fleece", "ll bean", "eddie bauer",
    
    # === KNITWEAR ===
    "cashmere sweater", "wool sweater", "cardigan",
    "cable knit", "fair isle", "vintage sweater",
    
    # === ACCESSORIES ===
    "designer belt", "designer scarf", "designer sunglasses",
    "leather bag", "tote bag", "crossbody bag",
    
    # === FOOTWEAR ===
    "designer shoes", "leather boots", "chelsea boots",
    "loafers", "derby shoes", "sneakers",
]


async def depop_luxury_scrape(
    items_per_search: int = 50,
    max_searches: int = None
):
    """DEPOP-ONLY luxury brand scrape."""
    
    search_count = len(LUXURY_SEARCHES) if max_searches is None else min(max_searches, len(LUXURY_SEARCHES))
    
    logger.info("="*80)
    logger.info("💎 DEPOP-ONLY LUXURY BRAND SCRAPER")
    logger.info("="*80)
    logger.info(f"Platform: Depop ONLY")
    logger.info(f"Search terms: {search_count} luxury brands & categories")
    logger.info(f"Items per search: {items_per_search}")
    logger.info(f"Expected total: ~{search_count * items_per_search:,} items")
    logger.info("="*80)
    print()
    
    total_saved = 0
    successful_searches = 0
    failed_searches = 0
    
    for idx, search_term in enumerate(LUXURY_SEARCHES[:search_count], 1):
        logger.info(f"[{idx}/{search_count}] 🔍 {search_term}")
        
        try:
            depop_items = await scrape_depop_working(search_term, max_items=items_per_search)
            
            if isinstance(depop_items, Exception):
                logger.warning(f"  ❌ Depop failed: {depop_items}")
                failed_searches += 1
                continue
            
            result = save_depop_items(depop_items) if depop_items else {'saved': 0, 'failed': 0}
            
            total_saved += result['saved']
            
            if result['saved'] > 0:
                successful_searches += 1
                logger.info(f"  ✓ Saved {result['saved']} items")
            else:
                failed_searches += 1
                logger.info(f"  ⚠️  No items saved")
            
            # Progress update every 20 searches
            if idx % 20 == 0:
                logger.info("")
                logger.info(f"  📊 Progress: {total_saved:,} items | Success: {successful_searches}/{idx}")
                logger.info("")
            
            # Delay between searches (randomized to avoid rate limits)
            if idx < search_count:
                delay = random.uniform(2, 5)
                await asyncio.sleep(delay)
            
        except KeyboardInterrupt:
            logger.warning("\n⚠️  Interrupted by user!")
            raise
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            failed_searches += 1
            continue
    
    # Final summary
    print()
    logger.info("="*80)
    logger.info("🏆 DEPOP SCRAPE COMPLETE")
    logger.info("="*80)
    logger.info(f"Total items saved: {total_saved:,}")
    logger.info(f"Successful searches: {successful_searches}/{search_count}")
    logger.info(f"Failed searches: {failed_searches}")
    logger.info("="*80)
    logger.info("✨ Next step: python3 embed_items.py depop")
    logger.info("="*80)
    
    return total_saved


async def main():
    """Run Depop-only luxury brand scrape."""
    import sys
    
    # Parse arguments
    items_per_search = 50  # default - 50 items per search
    max_searches = None  # default - all searches
    
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit():
            max_searches = int(sys.argv[1])
        elif sys.argv[1] == 'all':
            max_searches = None
    
    if len(sys.argv) > 2 and sys.argv[2].isdigit():
        items_per_search = int(sys.argv[2])
    
    logger.info(f"⚙️  Config: {max_searches or 'ALL'} searches, {items_per_search} items/search")
    print()
    
    try:
        total = await depop_luxury_scrape(
            items_per_search=items_per_search,
            max_searches=max_searches
        )
        sys.exit(0 if total > 0 else 1)
    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Interrupted! All progress has been saved to database.")
        logger.info("💡 Run the embed script when ready: python3 embed_items.py depop")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
