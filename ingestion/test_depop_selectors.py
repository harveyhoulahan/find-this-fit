"""
Quick diagnostic script to test Depop page structure and find correct selectors.
This helps debug scraping issues when selectors change.
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: playwright not installed")
    sys.exit(1)


async def diagnose_depop(search_term: str = "vintage tee"):
    """
    Load Depop search page and analyze its structure to find correct selectors.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible browser for debugging
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        
        url = f"https://www.depop.com/search/?q={search_term.replace(' ', '%20')}"
        print(f"Loading: {url}\n")
        
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)  # Wait for JS to render
        
        print("="*60)
        print("DIAGNOSTIC REPORT")
        print("="*60)
        
        # Test various selectors
        selectors_to_test = [
            ('data-testid="product__item"', '[data-testid="product__item"]'),
            ('data-testid="productCard"', '[data-testid="productCard"]'),
            ('class contains "product"', '[class*="product"]'),
            ('class contains "ProductCard"', '[class*="ProductCard"]'),
            ('a[href*="/products/"]', 'a[href*="/products/"]'),
            ('article', 'article'),
            ('li[data-testid]', 'li[data-testid]'),
            ('.styles__ProductCard', '.styles__ProductCard'),
        ]
        
        print("\n1. TESTING SELECTORS:")
        print("-" * 60)
        
        working_selector = None
        for name, selector in selectors_to_test:
            try:
                elements = await page.query_selector_all(selector)
                count = len(elements)
                status = "✓" if count > 0 else "✗"
                print(f"{status} {name:40s} → {count} elements")
                
                if count > 5 and not working_selector:
                    working_selector = selector
                    
            except Exception as e:
                print(f"✗ {name:40s} → Error: {e}")
        
        # Check page content
        print("\n2. PAGE CONTENT ANALYSIS:")
        print("-" * 60)
        content = await page.content()
        
        checks = [
            ("Product links found", '/products/' in content),
            ("React app detected", 'react' in content.lower() or '__NEXT_DATA__' in content),
            ("CAPTCHA detected", 'captcha' in content.lower()),
            ("CloudFlare detected", 'cloudflare' in content.lower()),
            ("Access blocked", 'blocked' in content.lower() or 'access denied' in content.lower()),
        ]
        
        for check_name, result in checks:
            status = "✓" if result else "✗"
            print(f"{status} {check_name}")
        
        # Try to find product elements with working selector
        if working_selector:
            print(f"\n3. EXTRACTING WITH SELECTOR: {working_selector}")
            print("-" * 60)
            
            products = await page.query_selector_all(working_selector)
            
            for i, product in enumerate(products[:3], 1):
                print(f"\nProduct {i}:")
                
                # Try to extract basic info
                link = await product.query_selector('a')
                if link:
                    href = await link.get_attribute('href')
                    print(f"  URL: {href}")
                
                # Try to find image
                img = await product.query_selector('img')
                if img:
                    src = await img.get_attribute('src')
                    alt = await img.get_attribute('alt')
                    print(f"  Image: {src[:60]}..." if src else "  No image src")
                    print(f"  Alt: {alt}" if alt else "  No alt text")
                
                # Get all text
                text = await product.inner_text()
                print(f"  Text: {text[:100]}...")
        
        # Save screenshot
        screenshot_path = f'/tmp/depop_diagnosis_{search_term.replace(" ", "_")}.png'
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n4. SCREENSHOT SAVED:")
        print(f"   {screenshot_path}")
        
        print("\n" + "="*60)
        print("Recommended next steps:")
        if working_selector:
            print(f"✓ Use selector: {working_selector}")
        else:
            print("✗ No working selector found - check screenshot for page state")
            print("  Possible causes:")
            print("  - Depop changed their page structure")
            print("  - Bot detection is blocking access")
            print("  - Page requires authentication")
        print("="*60)
        
        # Keep browser open for manual inspection
        print("\nBrowser will stay open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(diagnose_depop("vintage tee"))
