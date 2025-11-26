#!/usr/bin/env python3
"""
🌙 OVERNIGHT MASS SCRAPER 🌙
Large-scale scraping operation that replaces all existing data.

This script:
1. Backs up current database to a timestamped file
2. Clears all existing fashion_items data
3. Performs comprehensive scraping across Depop, Grailed, and Vinted
4. Uses structured metadata (brand, category, color, condition, size)
5. Covers diverse search terms across all major fashion categories
6. Runs overnight - expect 8-12 hours for ~50,000+ items

Usage:
    python3 overnight_mass_scrape.py
    
Environment:
    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/find_this_fit
"""
import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import json

# Setup paths
project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from db import execute_sync
from depop_api_scraper import scrape_depop_api, save_items as save_depop_items
from grailed_api_scraper import scrape_grailed_api, save_items as save_grailed_items
from vinted_api_scraper import scrape_vinted_api, save_items as save_vinted_items

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

# 🎯 COMPREHENSIVE SEARCH TERMS - Covers all major categories
SEARCH_TERMS = {
    # Luxury Brands
    "luxury": [
        "gucci", "prada", "louis vuitton", "chanel", "dior",
        "balenciaga", "saint laurent", "givenchy", "bottega veneta",
        "celine", "burberry", "fendi", "valentino", "versace",
        "gucci bag", "prada shoes", "balenciaga sneakers",
        "saint laurent jacket", "dior dress"
    ],
    
    # Streetwear
    "streetwear": [
        "supreme", "palace", "bape", "stussy", "off-white",
        "fear of god", "kith", "anti social social club",
        "supreme box logo", "bape hoodie", "off-white tee",
        "palace jacket", "stussy sweatshirt"
    ],
    
    # Sportswear
    "sportswear": [
        "nike", "adidas", "jordan", "yeezy", "new balance",
        "puma", "reebok", "under armour", "champion",
        "nike air max", "adidas yeezy", "jordan 1", "nike dunk",
        "adidas ultra boost", "new balance 550", "nike tech fleece"
    ],
    
    # Designer/Contemporary
    "designer": [
        "acne studios", "ami paris", "apc", "comme des garcons",
        "rick owens", "maison margiela", "yohji yamamoto",
        "issey miyake", "stone island", "cp company",
        "rick owens ramones", "cdg converse", "stone island jacket"
    ],
    
    # Outdoor/Technical
    "outdoor": [
        "patagonia", "north face", "arc'teryx", "carhartt",
        "columbia", "mammut", "fjallraven",
        "north face nuptse", "patagonia fleece", "arcteryx jacket",
        "carhartt jacket", "fjallraven kanken"
    ],
    
    # Denim
    "denim": [
        "levi's", "wrangler", "lee", "diesel", "g-star",
        "true religion", "nudie jeans", "acne jeans",
        "levi's 501", "vintage levi's", "black jeans", "blue jeans",
        "distressed jeans", "skinny jeans", "straight jeans"
    ],
    
    # Tops
    "tops": [
        "vintage tee", "band tee", "graphic tee", "vintage shirt",
        "flannel", "denim shirt", "oxford shirt", "polo shirt",
        "sweater", "cardigan", "knit sweater", "wool sweater",
        "hoodie", "crewneck", "zip hoodie"
    ],
    
    # Outerwear
    "outerwear": [
        "leather jacket", "bomber jacket", "denim jacket",
        "varsity jacket", "coach jacket", "windbreaker",
        "parka", "trench coat", "peacoat", "overcoat",
        "puffer jacket", "down jacket", "fleece jacket"
    ],
    
    # Bottoms
    "bottoms": [
        "cargo pants", "track pants", "sweatpants", "chinos",
        "corduroy pants", "work pants", "shorts", "denim shorts",
        "athletic shorts", "swim shorts"
    ],
    
    # Footwear
    "footwear": [
        "sneakers", "boots", "dress shoes", "loafers", "sandals",
        "doc martens", "converse", "vans", "timberland",
        "chelsea boots", "combat boots", "running shoes",
        "high tops", "low tops", "slip ons"
    ],
    
    # Accessories
    "accessories": [
        "backpack", "tote bag", "crossbody bag", "messenger bag",
        "wallet", "belt", "hat", "beanie", "cap", "bucket hat",
        "scarf", "sunglasses", "watch", "jewelry", "necklace", "ring"
    ],
    
    # Color-specific searches (helps with diversity)
    "colors": [
        "black jacket", "white sneakers", "navy sweater",
        "grey hoodie", "red dress", "blue jeans", "green coat",
        "brown boots", "beige pants", "pink bag"
    ],
    
    # Condition/Style searches
    "styles": [
        "vintage", "retro", "y2k", "90s", "80s",
        "minimalist", "oversized", "cropped", "distressed",
        "new with tags", "like new", "designer sample"
    ]
}

# Items per search term per platform
ITEMS_PER_SEARCH = {
    "luxury": 500,      # High priority - detailed luxury items
    "streetwear": 400,  # Popular category
    "sportswear": 400,  # Popular category
    "designer": 300,    # Quality over quantity
    "outdoor": 200,
    "denim": 300,
    "tops": 200,
    "outerwear": 300,
    "bottoms": 200,
    "footwear": 300,
    "accessories": 200,
    "colors": 100,      # Supplementary
    "styles": 100       # Supplementary
}


async def backup_database():
    """Create a backup of current fashion_items data."""
    backup_dir = Path(__file__).parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f"fashion_items_backup_{timestamp}.sql"
    
    logger.info(f"📦 Creating database backup: {backup_file}")
    
    try:
        # Export current data using pg_dump
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
        # Get count before deletion
        result = execute_sync("SELECT COUNT(*) FROM fashion_items")
        old_count = result[0][0] if result else 0
        
        # Delete all items
        execute_sync("DELETE FROM fashion_items")
        
        # Reset sequence
        execute_sync("ALTER SEQUENCE fashion_items_id_seq RESTART WITH 1")
        
        logger.info(f"✅ Deleted {old_count:,} items. Database cleared.")
        return old_count
    except Exception as e:
        logger.error(f"❌ Database clear failed: {e}")
        return 0


async def scrape_platform(platform: str, search_terms: List[str], items_per_search: int) -> Dict[str, Any]:
    """Scrape a single platform with all search terms."""
    logger.info(f"\n{'='*80}")
    logger.info(f"🚀 Starting {platform.upper()} scrape")
    logger.info(f"{'='*80}")
    
    total_items = []
    total_saved = 0
    total_failed = 0
    
    for i, term in enumerate(search_terms, 1):
        logger.info(f"\n[{platform.upper()}] Search {i}/{len(search_terms)}: '{term}'")
        
        items = []
        try:
            # Call appropriate scraper
            if platform == "depop":
                items = await scrape_depop_api(term, max_items=items_per_search)
                if items:
                    result = save_depop_items(items)
                    total_saved += result['saved']
                    total_failed += result['failed']
                    
            elif platform == "grailed":
                items = await scrape_grailed_api(term, max_items=items_per_search)
                if items:
                    result = save_grailed_items(items)
                    total_saved += result['saved']
                    total_failed += result['failed']
                    
            elif platform == "vinted":
                items = await scrape_vinted_api(term, max_items=items_per_search)
                if items:
                    result = save_vinted_items(items)
                    total_saved += result['saved']
                    total_failed += result['failed']
            
            logger.info(f"  ✓ Saved {len(items)} items (Total: {total_saved:,})")
            
            # Brief pause between searches
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"  ✗ Error scraping '{term}': {e}")
            continue
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ {platform.upper()} Complete: {total_saved:,} saved, {total_failed} failed")
    logger.info(f"{'='*80}\n")
    
    return {
        "platform": platform,
        "saved": total_saved,
        "failed": total_failed
    }


async def main():
    """Execute overnight mass scraping operation."""
    start_time = datetime.now()
    
    logger.info("="*80)
    logger.info("🌙 OVERNIGHT MASS SCRAPER STARTING 🌙")
    logger.info("="*80)
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log file: {log_file}")
    logger.info("")
    
    # Step 1: Backup current database
    logger.info("STEP 1: Database Backup")
    logger.info("-" * 80)
    backup_success = await backup_database()
    if not backup_success:
        logger.error("❌ Backup failed. Aborting scrape.")
        return
    
    # Step 2: Clear existing data
    logger.info("\nSTEP 2: Clear Existing Data")
    logger.info("-" * 80)
    old_count = clear_database()
    
    # Step 3: Calculate scraping plan
    logger.info("\nSTEP 3: Scraping Plan")
    logger.info("-" * 80)
    
    all_terms = []
    for category, terms in SEARCH_TERMS.items():
        items_per = ITEMS_PER_SEARCH.get(category, 100)
        all_terms.extend([(term, items_per) for term in terms])
    
    total_searches = len(all_terms)
    expected_items_per_platform = sum(items for _, items in all_terms)
    expected_total = expected_items_per_platform * 3  # 3 platforms
    
    logger.info(f"Search terms: {total_searches}")
    logger.info(f"Expected items per platform: ~{expected_items_per_platform:,}")
    logger.info(f"Expected total items: ~{expected_total:,}")
    logger.info(f"Estimated time: 8-12 hours")
    
    # Step 4: Execute scraping
    logger.info("\nSTEP 4: Execute Scraping")
    logger.info("-" * 80)
    
    results = []
    
    # Scrape each platform sequentially
    for platform in ["depop", "grailed", "vinted"]:
        search_list = [term for term, _ in all_terms]
        # Use average items per search
        avg_items = sum(items for _, items in all_terms) // len(all_terms)
        
        result = await scrape_platform(platform, search_list, avg_items)
        results.append(result)
        
        # Brief break between platforms
        await asyncio.sleep(5)
    
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
        
        # Overall stats
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
    
    # Next steps
    logger.info("\n📋 NEXT STEPS:")
    logger.info("1. Review the log file for any errors")
    logger.info("2. Run embeddings: python3 embed_items.py all")
    logger.info("3. Test search API with new data")
    logger.info("4. Check database stats: docker exec -i findthisfit-db psql -U postgres -d find_this_fit")
    
    return total_saved


if __name__ == "__main__":
    try:
        total = asyncio.run(main())
        sys.exit(0 if total and total > 0 else 1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Scrape interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
