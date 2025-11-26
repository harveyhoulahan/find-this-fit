#!/usr/bin/env python3
"""
🌙 OVERNIGHT MASS SCRAPER V2 🌙
Large-scale scraping using WORKING hybrid (text + CLIP visual) scrapers.

Uses the actual working scrapers:
- depop_scraper_working.py (Playwright + hybrid metadata)
- grailed_scraper.py (Playwright + hybrid metadata)
- vinted_scraper.py (Playwright + hybrid metadata)

All use CLIP visual analysis for accurate brand/category/color detection.

Expected: 10,000-20,000 high-quality items overnight (8-12 hours)
"""
import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Setup paths
project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from db import execute_sync

# Import the WORKING scrapers and their save functions
from depop_scraper_working import scrape_depop_working, save_items as save_depop_items
from grailed_scraper import scrape_grailed, save_items as save_grailed_items
from vinted_scraper import scrape_vinted, save_items as save_vinted_items

# Configure logging
log_file = Path(__file__).parent / f"overnight_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 🎯 COMPREHENSIVE SEARCH TERMS - 287+ terms covering all fashion categories
# Note: With CLIP visual analysis, we can scrape broader terms and let AI classify
SEARCH_TERMS = [
    # === LUXURY BRANDS ===
    "gucci", "prada", "louis vuitton", "chanel", "dior",
    "balenciaga", "saint laurent", "bottega veneta", "celine",
    "burberry", "fendi", "valentino", "givenchy", "versace",
    "dolce gabbana", "armani", "moncler", "tom ford", "loewe",
    "hermes", "cartier", "ferragamo", "bulgari",
    
    # === STREETWEAR ===
    "supreme", "palace", "bape", "stussy", "off-white",
    "kith", "anti social social club", "bape hoodie",
    "supreme box logo", "palace tri ferg", "travis scott",
    "vlone", "gallery dept", "chrome hearts", "human made",
    "brain dead", "corteiz", "kapital", "neighborhood",
    
    # === SPORTSWEAR ===
    "nike", "adidas", "jordan", "yeezy", "new balance",
    "puma", "reebok", "under armour", "champion", "fila",
    "asics", "salomon", "nike air max", "jordan 1", "jordan 4",
    "nike dunk", "adidas yeezy", "air force 1", "new balance 550",
    "adidas samba", "nike tech fleece", "vapormax",
    
    # === DESIGNER/CONTEMPORARY ===
    "acne studios", "ami paris", "apc", "comme des garcons",
    "rick owens", "maison margiela", "yohji yamamoto", "issey miyake",
    "stone island", "cp company", "dries van noten", "jil sander",
    "lemaire", "our legacy", "марни", "jacquemus", "helmut lang",
    "raf simons", "y3", "craig green", "sacai", "junya watanabe",
    
    # === OUTDOOR/TECHNICAL ===
    "patagonia", "north face", "arcteryx", "arc'teryx", "carhartt",
    "columbia", "mammut", "fjallraven", "helly hansen", "berghaus",
    "napapijri", "barbour", "woolrich", "canada goose", "mountain hardwear",
    "north face nuptse", "patagonia fleece", "arcteryx jacket",
    "carhartt wip", "dickies", "gramicci",
    
    # === SKATE/SURF ===
    "vans", "converse", "billabong", "quiksilver", "volcom",
    "hurley", "rvca", "thrasher", "santa cruz", "element",
    "globe", "dc shoes", "emerica", "etnies", "huf",
    
    # === DENIM BRANDS ===
    "levis", "wrangler", "lee", "diesel", "g-star",
    "true religion", "nudie jeans", "acne jeans", "apc denim",
    "naked famous", "3sixteen", "iron heart", "rrl",
    
    # === VINTAGE/RETRO BRANDS ===
    "tommy hilfiger", "polo ralph lauren", "lacoste", "nautica",
    "gap", "old navy", "eddie bauer", "ll bean", "lands end",
    "pendleton", "woolrich", "carhartt vintage",
    
    # === JAPANESE BRANDS ===
    "visvim", "kapital", "neighborhood", "wtaps", "undercover",
    "sacai", "nonnative", "white mountaineering", "porter",
    "beams", "uniqlo", "needles", "south2 west8",
    
    # === TOPS - SPECIFIC STYLES ===
    "hoodie", "sweatshirt", "crewneck", "zip hoodie", "pullover",
    "t-shirt", "tee", "long sleeve", "polo shirt", "henley",
    "sweater", "cardigan", "turtleneck", "v-neck", "crew neck",
    "tank top", "muscle tee", "crop top", "tube top",
    "flannel", "chambray", "oxford shirt", "button down",
    "graphic tee", "band tee", "vintage tee", "oversized tee",
    "dress shirt", "work shirt", "hawaiian shirt", "camp collar",
    
    # === OUTERWEAR - SPECIFIC STYLES ===
    "jacket", "coat", "blazer", "parka", "windbreaker",
    "bomber jacket", "varsity jacket", "harrington jacket",
    "coach jacket", "trucker jacket", "denim jacket",
    "leather jacket", "suede jacket", "shearling jacket",
    "puffer jacket", "down jacket", "quilted jacket",
    "fleece jacket", "fleece pullover", "zip fleece",
    "peacoat", "overcoat", "trench coat", "mac coat",
    "anorak", "rain jacket", "shell jacket", "softshell",
    
    # === BOTTOMS - SPECIFIC STYLES ===
    "jeans", "denim", "black jeans", "blue jeans", "raw denim",
    "pants", "trousers", "chinos", "khakis", "dress pants",
    "cargo pants", "cargo shorts", "work pants", "painter pants",
    "track pants", "joggers", "sweatpants", "lounge pants",
    "corduroy pants", "wide leg pants", "straight leg", "slim fit",
    "shorts", "chino shorts", "athletic shorts", "swim shorts",
    "board shorts", "gym shorts", "basketball shorts",
    "skirt", "midi skirt", "mini skirt", "pleated skirt",
    "leggings", "tights", "bike shorts",
    
    # === DRESSES & SETS ===
    "dress", "mini dress", "midi dress", "maxi dress",
    "slip dress", "wrap dress", "shirt dress", "sundress",
    "jumpsuit", "romper", "overalls", "coveralls",
    "suit", "two piece", "matching set", "co-ord",
    
    # === FOOTWEAR - SPECIFIC STYLES ===
    "sneakers", "runners", "trainers", "high tops", "low tops",
    "basketball shoes", "running shoes", "tennis shoes",
    "boots", "combat boots", "chelsea boots", "work boots",
    "hiking boots", "desert boots", "chukka boots",
    "doc martens", "timberland", "red wing", "blundstone",
    "dress shoes", "loafers", "oxfords", "brogues", "derbies",
    "sandals", "slides", "flip flops", "birkenstock",
    "heels", "pumps", "platforms", "wedges",
    "slippers", "mules", "espadrilles",
    
    # === ACCESSORIES - COMPREHENSIVE ===
    "bag", "backpack", "tote bag", "messenger bag", "crossbody",
    "shoulder bag", "handbag", "clutch", "duffle bag", "gym bag",
    "fanny pack", "belt bag", "sling bag", "weekend bag",
    "wallet", "cardholder", "coin purse", "money clip",
    "belt", "leather belt", "canvas belt", "chain belt",
    "hat", "beanie", "cap", "snapback", "dad hat", "fitted hat",
    "bucket hat", "trucker hat", "five panel", "baseball cap",
    "fedora", "panama hat", "sun hat", "winter hat",
    "scarf", "bandana", "neck warmer", "infinity scarf",
    "sunglasses", "glasses", "aviators", "wayfarers",
    "watch", "watch strap", "smart watch",
    "jewelry", "necklace", "chain", "pendant", "bracelet",
    "ring", "earrings", "choker",
    "gloves", "mittens", "socks", "tie", "bow tie",
    
    # === ACTIVEWEAR ===
    "athletic wear", "gym wear", "yoga pants", "sports bra",
    "compression shorts", "running tights", "tank top",
    "performance jacket", "windrunner", "training pants",
    
    # === UNDERWEAR/BASICS ===
    "underwear", "boxers", "briefs", "boxer briefs",
    "bra", "sports bra", "bralette", "tank top", "cami",
    "thermal", "base layer", "long underwear",
    
    # === STYLE KEYWORDS (CLIP analyzes) ===
    "vintage", "retro", "y2k", "90s", "80s", "70s",
    "grunge", "punk", "goth", "emo", "scene",
    "preppy", "ivy", "americana", "workwear",
    "minimalist", "maximalist", "avant garde",
    "oversized", "cropped", "fitted", "loose", "baggy",
    "distressed", "ripped", "washed", "faded",
    "embroidered", "printed", "patterned", "striped",
    "monochrome", "neutral", "earth tone",
    
    # === COLOR-SPECIFIC ===
    "black", "white", "grey", "gray", "navy", "blue",
    "red", "pink", "green", "olive", "forest green",
    "yellow", "mustard", "orange", "burnt orange",
    "purple", "lavender", "brown", "tan", "beige", "cream",
    "burgundy", "maroon", "khaki", "sage", "mint",
    
    # === PATTERN-SPECIFIC ===
    "striped", "plaid", "checkered", "gingham", "houndstooth",
    "floral", "paisley", "tie dye", "camo", "camouflage",
    "leopard print", "zebra print", "animal print",
    
    # === MATERIAL-SPECIFIC ===
    "leather", "suede", "denim", "corduroy", "velvet",
    "wool", "cashmere", "cotton", "linen", "silk",
    "fleece", "sherpa", "nylon", "polyester", "gore-tex",
]

# Items to scrape per search term per platform
# With 287+ search terms, we'll get massive coverage
# 40 items * 287 terms * 3 platforms = ~34,500 total items (30,000+ goal)
ITEMS_PER_SEARCH = 40  # Balanced for overnight completion with comprehensive coverage


async def backup_database():
    """Create a backup of current fashion_items data."""
    backup_dir = Path(__file__).parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f"fashion_items_backup_{timestamp}.sql"
    
    logger.info(f"📦 Creating database backup: {backup_file}")
    
    try:
        os.system(
            f"docker exec findthisfit-db pg_dump -U postgres -d find_this_fit "
            f"-t fashion_items --data-only --column-inserts > {backup_file}"
        )
        logger.info(f"✅ Backup created: {backup_file}")
        return True
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        return False


def clear_database():
    """Clear all existing fashion_items data."""
    logger.info("🗑️  Clearing existing fashion_items data...")
    
    try:
        result = execute_sync("SELECT COUNT(*) FROM fashion_items")
        old_count = result[0][0] if result else 0
        
        execute_sync("DELETE FROM fashion_items")
        execute_sync("ALTER SEQUENCE fashion_items_id_seq RESTART WITH 1")
        
        logger.info(f"✅ Deleted {old_count:,} items. Database cleared.")
        return old_count
    except Exception as e:
        logger.error(f"❌ Database clear failed: {e}")
        return 0


async def scrape_platform(platform: str, scraper_func, search_terms: List[str], items_per_search: int) -> Dict[str, Any]:
    """Scrape a single platform with all search terms."""
    logger.info(f"\n{'='*80}")
    logger.info(f"🚀 Starting {platform.upper()} scrape (with CLIP visual analysis)")
    logger.info(f"{'='*80}")
    
    total_saved = 0
    total_failed = 0
    
    for i, term in enumerate(search_terms, 1):
        logger.info(f"\n[{platform.upper()}] Search {i}/{len(search_terms)}: '{term}'")
        
        try:
            # Call the scraper with CLIP visual analysis
            items = await scraper_func(term, max_items=items_per_search)
            
            # Save items to database
            if items:
                result = None
                if platform == "depop":
                    result = save_depop_items(items)
                elif platform == "grailed":
                    result = save_grailed_items(items)
                elif platform == "vinted":
                    result = save_vinted_items(items)
                
                if result:
                    saved = result['saved']
                    total_saved += saved
                    total_failed += result['failed']
                    
                    logger.info(f"  ✓ Saved {saved}/{len(items)} items to DB (Total: {total_saved:,})")
                    
                    # Show sample metadata
                    if len(items) > 0:
                        sample = items[0]
                        logger.info(f"  Sample: {sample.get('brand', 'Unknown')} {sample.get('category', 'unknown')} ({sample.get('color', 'unknown')})")
            else:
                logger.info(f"  ⚠️ No items returned for '{term}'")
            
            # Brief pause between searches to avoid detection
            await asyncio.sleep(random.uniform(3, 5))
            
        except Exception as e:
            logger.error(f"  ✗ Error scraping '{term}': {e}")
            total_failed += 1
            continue
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ {platform.upper()} Complete: {total_saved:,} items scraped")
    logger.info(f"{'='*80}\n")
    
    return {
        "platform": platform,
        "saved": total_saved,
        "failed": total_failed
    }


async def main():
    """Execute overnight mass scraping operation."""
    import random
    
    start_time = datetime.now()
    
    logger.info("="*80)
    logger.info("🌙 OVERNIGHT MASS SCRAPER V2 - HYBRID (Text + CLIP Visual) 🌙")
    logger.info("="*80)
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log file: {log_file}")
    logger.info("")
    
    # Step 1: Backup
    logger.info("STEP 1: Database Backup")
    logger.info("-" * 80)
    backup_success = await backup_database()
    if not backup_success:
        logger.error("❌ Backup failed. Aborting scrape.")
        return 0
    
    # Step 2: Clear existing data
    logger.info("\nSTEP 2: Clear Existing Data")
    logger.info("-" * 80)
    old_count = clear_database()
    
    # Step 3: Scraping plan
    logger.info("\nSTEP 3: Scraping Plan")
    logger.info("-" * 80)
    
    total_searches = len(SEARCH_TERMS)
    expected_per_platform = total_searches * ITEMS_PER_SEARCH
    expected_total = expected_per_platform * 3
    
    logger.info(f"Search terms: {total_searches}")
    logger.info(f"Items per search: {ITEMS_PER_SEARCH}")
    logger.info(f"Expected per platform: ~{expected_per_platform:,}")
    logger.info(f"Expected total: ~{expected_total:,} items (targeting 30,000+)")
    logger.info(f"Method: Playwright + CLIP visual analysis")
    logger.info(f"Estimated time: 10-14 hours (slower but higher quality)")
    
    # Step 4: Execute scraping
    logger.info("\nSTEP 4: Execute Scraping")
    logger.info("-" * 80)
    
    results = []
    
    # Scrape each platform
    platforms = [
        ("depop", scrape_depop_working),
        ("grailed", scrape_grailed),
        ("vinted", scrape_vinted)
    ]
    
    for platform_name, scraper_func in platforms:
        result = await scrape_platform(
            platform_name, 
            scraper_func, 
            SEARCH_TERMS, 
            ITEMS_PER_SEARCH
        )
        results.append(result)
        
        # Brief break between platforms
        await asyncio.sleep(10)
    
    # Step 5: Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("\n" + "="*80)
    logger.info("🎉 OVERNIGHT SCRAPE COMPLETE 🎉")
    logger.info("="*80)
    logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Duration: {duration}")
    logger.info("")
    
    total_saved = sum(r['saved'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    
    logger.info("RESULTS BY PLATFORM:")
    logger.info("-" * 80)
    for result in results:
        logger.info(f"{result['platform'].upper():15} {result['saved']:>8,} saved, {result['failed']:>6} failed")
    
    logger.info("-" * 80)
    logger.info(f"{'TOTAL':15} {total_saved:>8,} saved, {total_failed:>6} failed")
    logger.info("")
    
    # Database statistics
    logger.info("DATABASE STATISTICS:")
    logger.info("-" * 80)
    
    try:
        stats = execute_sync("""
            SELECT 
                source,
                COUNT(*) as total,
                COUNT(DISTINCT brand) as brands,
                COUNT(DISTINCT category) as categories,
                COUNT(DISTINCT color) as colors
            FROM fashion_items
            GROUP BY source
            ORDER BY total DESC
        """)
        
        for row in stats:
            logger.info(f"{row[0]:15} {row[1]:>8,} items, {row[2]:>4} brands, {row[3]:>3} categories, {row[4]:>3} colors")
        
        overall = execute_sync("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT brand) as brands,
                COUNT(DISTINCT category) as categories,
                COUNT(DISTINCT color) as colors,
                COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as embedded
            FROM fashion_items
        """)
        
        if overall:
            row = overall[0]
            logger.info("-" * 80)
            logger.info(f"{'TOTAL':15} {row[0]:>8,} items, {row[1]:>4} brands, {row[2]:>3} categories, {row[3]:>3} colors")
            logger.info(f"{'EMBEDDED':15} {row[4]:>8,} items ({100*row[4]//row[0] if row[0] > 0 else 0}%)")
            
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
    
    logger.info("")
    logger.info(f"📝 Full log saved to: {log_file}")
    logger.info("="*80)
    
    logger.info("\n📋 NEXT STEPS:")
    logger.info("1. Review the log file for any errors")
    logger.info("2. Generate embeddings: python3 embed_items.py all")
    logger.info("3. Test search API with new data")
    
    return total_saved


if __name__ == "__main__":
    import random
    
    try:
        total = asyncio.run(main())
        sys.exit(0 if total and total > 0 else 1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Scrape interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
