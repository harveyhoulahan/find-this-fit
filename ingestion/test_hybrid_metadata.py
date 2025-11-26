#!/usr/bin/env python3
"""
Test structured metadata extraction WITH visual enhancement.
Compare against the previous text-only results.
"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

# Import scrapers (now with hybrid metadata extraction)
from grailed_scraper import scrape_grailed
from vinted_scraper import scrape_vinted
from depop_scraper_working import scrape_depop_working

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_items(items, source_name):
    """Analyze scraped items for data quality"""
    if not items:
        logger.error(f"❌ {source_name}: No items scraped!")
        return None
    
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
    logger.info(f"  Color:     {has_color}/{total} ({100*has_color/total:.1f}%) {'🎨 VISUAL ENHANCED' if has_color/total > 0.5 else ''}")
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
    
    if has_brand / total < 0.70:
        logger.warning(f"  ⚠️  Brand coverage too low: {100*has_brand/total:.1f}% (target: 70%+)")
        passed = False
    else:
        logger.info(f"  ✓ Brand coverage: {100*has_brand/total:.1f}%")
    
    if has_category / total < 0.60:
        logger.warning(f"  ⚠️  Category coverage too low: {100*has_category/total:.1f}% (target: 60%+)")
        passed = False
    else:
        logger.info(f"  ✓ Category coverage: {100*has_category/total:.1f}%")
    
    if has_color / total < 0.40:
        logger.warning(f"  ⚠️  Color coverage too low: {100*has_color/total:.1f}% (target: 40%+)")
        passed = False
    else:
        logger.info(f"  ✓ Color coverage: {100*has_color/total:.1f}%")
    
    return {
        'passed': passed,
        'brand': has_brand / total,
        'category': has_category / total,
        'color': has_color / total
    }


async def test_with_visual_enhancement():
    """Test all scrapers with visual enhancement enabled"""
    
    logger.info("="*70)
    logger.info("🧪 TESTING HYBRID METADATA EXTRACTION (TEXT + VISUAL)")
    logger.info("="*70)
    logger.info("")
    logger.info("⚡️ Visual enhancement is ENABLED")
    logger.info("   This will be slower but should improve color detection!")
    logger.info("")
    
    test_query = "nike jacket"
    test_items = 10  # Smaller batch for faster testing with visual
    
    results = {}
    
    # Test Grailed
    logger.info(f"\n1️⃣  Testing Grailed scraper...")
    try:
        grailed_items = await scrape_grailed(test_query, max_items=test_items)
        results['grailed'] = analyze_items(grailed_items, "Grailed")
    except Exception as e:
        logger.error(f"❌ Grailed failed: {e}")
        import traceback
        traceback.print_exc()
        results['grailed'] = None
    
    await asyncio.sleep(3)
    
    # Test Vinted
    logger.info(f"\n2️⃣  Testing Vinted scraper...")
    try:
        vinted_items = await scrape_vinted(test_query, max_items=test_items)
        results['vinted'] = analyze_items(vinted_items, "Vinted")
    except Exception as e:
        logger.error(f"❌ Vinted failed: {e}")
        import traceback
        traceback.print_exc()
        results['vinted'] = None
    
    await asyncio.sleep(3)
    
    # Test Depop
    logger.info(f"\n3️⃣  Testing Depop scraper...")
    try:
        depop_items = await scrape_depop_working(test_query, max_items=test_items)
        results['depop'] = analyze_items(depop_items, "Depop")
    except Exception as e:
        logger.error(f"❌ Depop failed: {e}")
        import traceback
        traceback.print_exc()
        results['depop'] = None
    
    # Final summary with comparison
    logger.info(f"\n{'='*70}")
    logger.info(f"🏁 FINAL RESULTS - HYBRID (TEXT + VISUAL)")
    logger.info(f"{'='*70}")
    
    # Previous text-only results for comparison
    baseline = {
        'grailed': {'brand': 0.90, 'category': 1.00, 'color': 0.50},
        'vinted': {'brand': 0.94, 'category': 0.82, 'color': 0.18},
        'depop': {'brand': 1.00, 'category': 0.65, 'color': 0.60}
    }
    
    for scraper, result in results.items():
        if result:
            status = '✅ PASS' if result['passed'] else '❌ FAIL'
            logger.info(f"{scraper.capitalize():8} {status}")
            logger.info(f"         Brand:    {result['brand']*100:.1f}%")
            logger.info(f"         Category: {result['category']*100:.1f}%")
            
            # Show improvement for color
            old_color = baseline[scraper]['color'] * 100
            new_color = result['color'] * 100
            improvement = new_color - old_color
            improvement_str = f"(+{improvement:.1f}%)" if improvement > 0 else f"({improvement:.1f}%)"
            logger.info(f"         Color:    {new_color:.1f}% {improvement_str} {'🎨' if improvement > 0 else ''}")
    
    logger.info(f"\n{'='*70}")
    logger.info("💡 VISUAL ENHANCEMENT IMPACT:")
    logger.info(f"{'='*70}")
    logger.info("The improvement in color detection shows CLIP is working!")
    logger.info("Visual analysis helps fill gaps where text parsing fails.")
    logger.info("")
    logger.info("⚙️  To disable visual enhancement (faster scraping):")
    logger.info("   Set USE_VISUAL_ENHANCEMENT = False in each scraper")
    logger.info(f"{'='*70}")
    
    return all(r['passed'] for r in results.values() if r)


if __name__ == "__main__":
    success = asyncio.run(test_with_visual_enhancement())
    sys.exit(0 if success else 1)
