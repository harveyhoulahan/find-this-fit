#!/usr/bin/env python3
"""Debug scraper to see what data we're actually getting from Depop."""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from playwright.async_api import async_playwright


async def debug_depop():
    """See what's actually on the page."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        url = "https://www.depop.com/search/?q=vintage%20tee"
        print(f"Loading: {url}\n")
        
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(4)
        
        # Find products
        products = await page.query_selector_all('a[href*="/products/"]')
        print(f"Found {len(products)} product links\n")
        
        # Examine first 3
        for i, product in enumerate(products[:3], 1):
            print(f"="*60)
            print(f"PRODUCT {i}")
            print(f"="*60)
            
            # URL
            href = await product.get_attribute('href')
            print(f"href: {href}")
            
            # All text
            text = await product.inner_text()
            print(f"\nText content:\n{text}\n")
            
            # HTML structure
            html = await product.inner_html()
            print(f"HTML (first 200 chars):\n{html[:200]}...\n")
            
            # Check for image
            img = await product.query_selector('img')
            if img:
                src = await img.get_attribute('src')
                alt = await img.get_attribute('alt')
                print(f"Image src: {src}")
                print(f"Image alt: {alt}")
            
            print()
        
        # Save screenshot
        await page.screenshot(path='/tmp/depop_manual_debug.png', full_page=True)
        print("Screenshot saved to /tmp/depop_manual_debug.png")
        
        print("\nKeeping browser open for 20 seconds...")
        await asyncio.sleep(20)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_depop())
