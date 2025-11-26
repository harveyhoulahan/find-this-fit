#!/usr/bin/env python3
"""
Quick test runner for Depop scraper with proper path setup.
Usage: python3 test_scraper.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Set up paths correctly
project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
ingestion_path = project_root / "ingestion"
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(ingestion_path))

# Set environment variable for database
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from depop_scraper_advanced import scrape_depop_advanced, save_items


async def test_scraper():
    """Quick test of the scraper."""
    print("="*60)
    print("DEPOP SCRAPER TEST")
    print("="*60)
    print()
    
    search_term = "vintage tee"
    max_items = 10
    
    print(f"Search term: '{search_term}'")
    print(f"Max items: {max_items}")
    print(f"Stealth mode: ON")
    print()
    print("Starting scrape...")
    print("-"*60)
    
    items = await scrape_depop_advanced(
        search_term=search_term,
        max_items=max_items,
        use_stealth=True
    )
    
    print()
    print("="*60)
    print("RESULTS")
    print("="*60)
    
    if items:
        print(f"✓ Found {len(items)} items")
        print()
        
        # Save to database
        print("Saving to database...")
        result = save_items(items)
        print(f"✓ Saved: {result['saved']}")
        print(f"✗ Failed: {result['failed']}")
        print()
        
        # Show samples
        print("Sample items:")
        print("-"*60)
        for i, item in enumerate(items[:5], 1):
            print(f"{i}. {item['title']}")
            print(f"   Price: ${item['price']}")
            print(f"   URL: {item['url'][:60]}...")
            print()
        
        return len(items)
    else:
        print("⚠️  No items found")
        print()
        print("Debug information:")
        print("  Check /tmp/depop_advanced_debug_*.png for screenshots")
        print("  Check /tmp/depop_html_*.html for page source")
        print()
        print("Possible issues:")
        print("  - Depop is blocking automated access (CAPTCHA)")
        print("  - Page structure has changed")
        print("  - Network/firewall blocking")
        print()
        return 0


if __name__ == "__main__":
    try:
        result = asyncio.run(test_scraper())
        
        print("="*60)
        if result > 0:
            print(f"✅ TEST PASSED: Scraped {result} items")
        else:
            print("❌ TEST FAILED: No items scraped")
        print("="*60)
        
        sys.exit(0 if result > 0 else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
