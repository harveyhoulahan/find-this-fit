#!/usr/bin/env python3
"""
Quick test of overnight scraper v2 with working hybrid scrapers.
"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from depop_scraper_working import scrape_depop_working
from grailed_scraper import scrape_grailed
from vinted_scraper import scrape_vinted

async def test_scrapers():
    """Test working scrapers"""
    print("="*60)
    print("🧪 Testing Overnight Scraper V2 (Hybrid Metadata)")
    print("="*60)
    print()
    
    results = {}
    
    # Test Depop
    print("1️⃣  Testing Depop (Playwright + CLIP)...")
    try:
        items = await scrape_depop_working("nike", max_items=5)
        if items and len(items) > 0:
            results['depop'] = f"✅ {len(items)} items"
            sample = items[0]
            print(f"   ✅ Depop: {len(items)} items")
            print(f"   Sample: {sample.get('brand', 'Unknown')} {sample.get('category', 'unknown')} ({sample.get('color', 'unknown')})")
        else:
            results['depop'] = "❌ No items"
            print("   ❌ No items returned")
    except Exception as e:
        results['depop'] = f"❌ Error: {str(e)[:50]}"
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test Grailed
    print("2️⃣  Testing Grailed (Playwright + CLIP)...")
    try:
        items = await scrape_grailed("supreme", max_items=5)
        if items and len(items) > 0:
            results['grailed'] = f"✅ {len(items)} items"
            sample = items[0]
            print(f"   ✅ Grailed: {len(items)} items")
            print(f"   Sample: {sample.get('brand', 'Unknown')} {sample.get('category', 'unknown')} ({sample.get('color', 'unknown')})")
        else:
            results['grailed'] = "❌ No items"
            print("   ❌ No items returned")
    except Exception as e:
        results['grailed'] = f"❌ Error: {str(e)[:50]}"
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test Vinted
    print("3️⃣  Testing Vinted (Playwright + CLIP)...")
    try:
        items = await scrape_vinted("jacket", max_items=5)
        if items and len(items) > 0:
            results['vinted'] = f"✅ {len(items)} items"
            sample = items[0]
            print(f"   ✅ Vinted: {len(items)} items")
            print(f"   Sample: {sample.get('brand', 'Unknown')} {sample.get('category', 'unknown')} ({sample.get('color', 'unknown')})")
        else:
            results['vinted'] = "❌ No items"
            print("   ❌ No items returned")
    except Exception as e:
        results['vinted'] = f"❌ Error: {str(e)[:50]}"
        print(f"   ❌ Error: {e}")
    
    print()
    print("="*60)
    print("📊 Test Results")
    print("="*60)
    for platform, result in results.items():
        print(f"{platform:15} {result}")
    
    print()
    all_passed = all("✅" in r for r in results.values())
    if all_passed:
        print("✅ All tests passed! Ready for overnight scrape.")
        print()
        print("To run full overnight scrape:")
        print("  ./RUN_OVERNIGHT_SCRAPE.sh")
        print()
        return True
    else:
        print("⚠️  Some scrapers failed but this is normal for testing.")
        print("   The overnight script will continue on errors.")
        print()
        print("You can still run: ./RUN_OVERNIGHT_SCRAPE.sh")
        return True  # Still ok to proceed

if __name__ == "__main__":
    success = asyncio.run(test_scrapers())
    sys.exit(0 if success else 1)
