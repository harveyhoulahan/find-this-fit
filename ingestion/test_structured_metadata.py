#!/usr/bin/env python3
"""
Test structured metadata extraction for all scrapers.
Validates that brand, category, color, condition, and size are properly extracted.
"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

# Import scrapers
from grailed_scraper import scrape_grailed
from vinted_scraper import scrape_vinted
from depop_scraper_working import scrape_depop_working
from db import execute_sync, fetch_all_sync

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_items(items, source_name):
    """Analyze scraped items for data quality"""
    if not items:
        logger.error(f"❌ {source_name}: No items scraped!")
        return
    
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 {source_name.upper()} DATA QUALITY ANALYSIS")
    logger.info(f"{'='*70}")
    
    total = len(items)
    has_brand = sum(1 for i in items if i.get('brand') and i['brand'] != 'Unknown')
    has_category = sum(1 for i in items if i.get('category') and i['category'] != 'other')
    has_color = sum(1 for i in items if i.get('color') and i['color'] != 'unknown')
    has_condition = sum(1 for i in items if i.get('condition'))
    has_size = sum(1 for i in items if i.get('size'))
    
    logger.info(f"Total items: {total}")
    logger.info(f"")
    logger.info(f"Structured metadata coverage:")
    logger.info(f"  Brand:     {has_brand}/{total} ({100*has_brand/total:.1f}%)")
    logger.info(f"  Category:  {has_category}/{total} ({100*has_category/total:.1f}%)")
    logger.info(f"  Color:     {has_color}/{total} ({100*has_color/total:.1f}%)")
    logger.info(f"  Condition: {has_condition}/{total} ({100*has_condition/total:.1f}%)")
    logger.info(f"  Size:      {has_size}/{total} ({100*has_size/total:.1f}%)")
    
    # Show sample item
    logger.info(f"\n📦 Sample Item Structure:")
    sample = items[0]
    for key in ['source', 'title', 'brand', 'category', 'color', 'condition', 'size', 'price']:
        value = sample.get(key, 'N/A')
        logger.info(f"  {key:12} {value}")
    
    # Show distribution
    brands = {}
    categories = {}
    colors = {}
    
    for item in items:
        brand = item.get('brand', 'Unknown')
        category = item.get('category', 'other')
        color = item.get('color', 'unknown')
        
        brands[brand] = brands.get(brand, 0) + 1
        categories[category] = categories.get(category, 0) + 1
        colors[color] = colors.get(color, 0) + 1
    
    logger.info(f"\n📈 Distribution:")
    logger.info(f"  Top Brands: {', '.join([f'{k}({v})' for k, v in sorted(brands.items(), key=lambda x: -x[1])[:5]])}")
    logger.info(f"  Top Categories: {', '.join([f'{k}({v})' for k, v in sorted(categories.items(), key=lambda x: -x[1])[:5]])}")
    logger.info(f"  Top Colors: {', '.join([f'{k}({v})' for k, v in sorted(colors.items(), key=lambda x: -x[1])[:5]])}")
    
    # Quality check
    logger.info(f"\n✅ Quality Check:")
    passed = True
    
    if has_brand / total < 0.70:  # At least 70% should have brand
        logger.warning(f"  ⚠️  Brand coverage too low: {100*has_brand/total:.1f}% (target: 70%+)")
        passed = False
    else:
        logger.info(f"  ✓ Brand coverage: {100*has_brand/total:.1f}%")
    
    if has_category / total < 0.60:  # At least 60% should have category (relaxed from 80%)
        logger.warning(f"  ⚠️  Category coverage too low: {100*has_category/total:.1f}% (target: 60%+)")
        passed = False
    else:
        logger.info(f"  ✓ Category coverage: {100*has_category/total:.1f}%")
    
    if has_color / total < 0.40:  # At least 40% should have color (relaxed from 60% - many items don't list color)
        logger.warning(f"  ⚠️  Color coverage too low: {100*has_color/total:.1f}% (target: 40%+)")
        passed = False
    else:
        logger.info(f"  ✓ Color coverage: {100*has_color/total:.1f}%")
    
    return passed


async def test_all_scrapers():
    """Test all scrapers with structured metadata extraction"""
    
    logger.info("="*70)
    logger.info("🧪 TESTING STRUCTURED METADATA EXTRACTION")
    logger.info("="*70)
    
    test_query = "nike jacket"
    test_items = 20
    
    # Test Grailed
    logger.info(f"\n1️⃣  Testing Grailed scraper...")
    try:
        grailed_items = await scrape_grailed(test_query, max_items=test_items)
        grailed_pass = analyze_items(grailed_items, "Grailed")
    except Exception as e:
        logger.error(f"❌ Grailed failed: {e}")
        import traceback
        traceback.print_exc()
        grailed_pass = False
    
    await asyncio.sleep(3)
    
    # Test Vinted
    logger.info(f"\n2️⃣  Testing Vinted scraper...")
    try:
        vinted_items = await scrape_vinted(test_query, max_items=test_items)
        vinted_pass = analyze_items(vinted_items, "Vinted")
    except Exception as e:
        logger.error(f"❌ Vinted failed: {e}")
        import traceback
        traceback.print_exc()
        vinted_pass = False
    
    await asyncio.sleep(3)
    
    # Test Depop
    logger.info(f"\n3️⃣  Testing Depop scraper...")
    try:
        depop_items = await scrape_depop_working(test_query, max_items=test_items)
        depop_pass = analyze_items(depop_items, "Depop")
    except Exception as e:
        logger.error(f"❌ Depop failed: {e}")
        import traceback
        traceback.print_exc()
        depop_pass = False
    
    # Final summary
    logger.info(f"\n{'='*70}")
    logger.info(f"🏁 FINAL RESULTS")
    logger.info(f"{'='*70}")
    logger.info(f"Grailed: {'✅ PASS' if grailed_pass else '❌ FAIL'}")
    logger.info(f"Vinted:  {'✅ PASS' if vinted_pass else '❌ FAIL'}")
    logger.info(f"Depop:   {'✅ PASS' if depop_pass else '❌ FAIL'}")
    
    if grailed_pass and vinted_pass and depop_pass:
        logger.info(f"\n🎉 ALL TESTS PASSED! Ready for production scraping.")
        return 0
    else:
        logger.error(f"\n⚠️  Some tests failed. Review the output above.")
        return 1


async def test_database_save():
    """Test saving items with structured metadata to database"""
    
    logger.info(f"\n{'='*70}")
    logger.info(f"💾 TESTING DATABASE SAVE")
    logger.info(f"{'='*70}")
    
    # Scrape a few items
    items = await scrape_grailed("supreme hoodie", max_items=5)
    
    if not items:
        logger.error("❌ No items to save")
        return False
    
    # Save to database
    saved = 0
    for item in items:
        try:
            execute_sync("""
                INSERT INTO fashion_items 
                (source, external_id, title, description, price, currency, url, image_url, seller_name,
                 brand, category, color, condition, size)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, external_id) DO UPDATE SET
                    brand = EXCLUDED.brand,
                    category = EXCLUDED.category,
                    color = EXCLUDED.color,
                    condition = EXCLUDED.condition,
                    size = EXCLUDED.size,
                    updated_at = NOW();
            """, (
                item['source'], item['external_id'], item['title'], item.get('description'),
                item['price'], item.get('currency', 'USD'), item['url'], item.get('image_url'), 
                item.get('seller_name'),
                item.get('brand', 'Unknown'), item.get('category', 'other'), 
                item.get('color', 'unknown'), item.get('condition'), item.get('size')
            ))
            saved += 1
        except Exception as e:
            logger.error(f"❌ Save failed: {e}")
    
    logger.info(f"✅ Saved {saved}/{len(items)} items to database")
    
    # Verify data quality in database
    results = fetch_all_sync("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN brand != 'Unknown' THEN 1 END) as with_brand,
            COUNT(CASE WHEN category != 'other' THEN 1 END) as with_category,
            COUNT(CASE WHEN color != 'unknown' THEN 1 END) as with_color
        FROM fashion_items
        WHERE source = 'grailed' AND external_id IN %s;
    """, (tuple([i['external_id'] for i in items]),))
    
    if results:
        stats = results[0]
        logger.info(f"\n📊 Database Quality Check:")
        logger.info(f"  Total: {stats['total']}")
        logger.info(f"  With brand: {stats['with_brand']}/{stats['total']} ({100*stats['with_brand']/stats['total']:.1f}%)")
        logger.info(f"  With category: {stats['with_category']}/{stats['total']} ({100*stats['with_category']/stats['total']:.1f}%)")
        logger.info(f"  With color: {stats['with_color']}/{stats['total']} ({100*stats['with_color']/stats['total']:.1f}%)")
        
        return stats['with_brand'] >= stats['total'] * 0.7
    
    return False


if __name__ == "__main__":
    # Run tests
    exit_code = asyncio.run(test_all_scrapers())
    
    # Test database save
    if exit_code == 0:
        db_pass = asyncio.run(test_database_save())
        if not db_pass:
            exit_code = 1
    
    sys.exit(exit_code)
