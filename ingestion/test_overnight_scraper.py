#!/usr/bin/env python3
"""
Quick test of the overnight scraper setup.
Tests all 3 API scrapers with minimal data to verify they work.
"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from depop_api_scraper import scrape_depop_api, save_items as save_depop
from grailed_api_scraper import scrape_grailed_api, save_items as save_grailed
from vinted_api_scraper import scrape_vinted_api, save_items as save_vinted

async def test_scrapers():
    """Test all 3 scrapers with small batches"""
    print("="*60)
    print("🧪 Testing Overnight Scraper Components")
    print("="*60)
    print()
    
    results = {}
    
    # Test Depop
    print("1️⃣  Testing Depop API Scraper...")
    try:
        items = await scrape_depop_api("nike", max_items=10)
        if items:
            result = save_depop(items)
            results['depop'] = f"✅ {result['saved']} items saved"
            print(f"   ✅ Depop: {result['saved']} items")
            if items:
                sample = items[0]
                print(f"   Sample: {sample['brand']} {sample['category']} ({sample['color']})")
        else:
            results['depop'] = "❌ No items returned"
            print("   ❌ No items returned")
    except Exception as e:
        results['depop'] = f"❌ Error: {e}"
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test Grailed
    print("2️⃣  Testing Grailed API Scraper...")
    try:
        items = await scrape_grailed_api("supreme", max_items=10)
        if items:
            result = save_grailed(items)
            results['grailed'] = f"✅ {result['saved']} items saved"
            print(f"   ✅ Grailed: {result['saved']} items")
            if items:
                sample = items[0]
                print(f"   Sample: {sample['brand']} {sample['category']} ({sample['color']})")
        else:
            results['grailed'] = "❌ No items returned"
            print("   ❌ No items returned")
    except Exception as e:
        results['grailed'] = f"❌ Error: {e}"
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test Vinted
    print("3️⃣  Testing Vinted API Scraper...")
    try:
        items = await scrape_vinted_api("jacket", max_items=10)
        if items:
            result = save_vinted(items)
            results['vinted'] = f"✅ {result['saved']} items saved"
            print(f"   ✅ Vinted: {result['saved']} items")
            if items:
                sample = items[0]
                print(f"   Sample: {sample['brand']} {sample['category']} ({sample['color']})")
        else:
            results['vinted'] = "❌ No items returned"
            print("   ❌ No items returned")
    except Exception as e:
        results['vinted'] = f"❌ Error: {e}"
        print(f"   ❌ Error: {e}")
    
    print()
    print("="*60)
    print("📊 Test Results Summary")
    print("="*60)
    for platform, result in results.items():
        print(f"{platform:15} {result}")
    
    print()
    all_passed = all("✅" in r for r in results.values())
    if all_passed:
        print("✅ All tests passed! Ready for overnight scrape.")
        print()
        print("To run the full overnight scrape:")
        print("  ./RUN_OVERNIGHT_SCRAPE.sh")
        print()
        return True
    else:
        print("❌ Some tests failed. Fix errors before running overnight scrape.")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_scrapers())
    sys.exit(0 if success else 1)
