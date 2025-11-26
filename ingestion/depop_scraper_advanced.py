"""
Advanced Depop scraper with anti-bot detection bypass.

Implements sophisticated evasion techniques:
- Browser fingerprint masking
- Realistic human behavior simulation
- Header rotation and cookie management
- Request timing randomization
- WebGL/Canvas fingerprint randomization

Note: Use responsibly and in compliance with Depop's Terms of Service.
"""
import asyncio
import logging
import random
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    from fake_useragent import UserAgent
except ImportError as e:
    print(f"ERROR: Missing dependencies. Run: pip install -r requirements.txt")
    print(f"Details: {e}")
    sys.exit(1)

from db import execute_sync  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SCRAPE_DELAY_MIN = 3.0
SCRAPE_DELAY_MAX = 7.0
MAX_RETRIES = 3
SCROLL_ITERATIONS = 5
REQUEST_TIMEOUT = 45000

# Initialize realistic user agent generator
ua = UserAgent(platforms=['pc', 'mobile'], os=['windows', 'macos', 'linux'])


def get_random_viewport():
    """Generate realistic viewport dimensions."""
    common_viewports = [
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1536, 'height': 864},
        {'width': 1440, 'height': 900},
        {'width': 1280, 'height': 720},
    ]
    return random.choice(common_viewports)


def get_random_timezone():
    """Get random timezone from common ones."""
    timezones = [
        'America/New_York',
        'America/Chicago',
        'America/Los_Angeles',
        'Europe/London',
        'Europe/Paris',
        'America/Toronto',
    ]
    return random.choice(timezones)


def get_random_locale():
    """Get random locale."""
    locales = ['en-US', 'en-GB', 'en-CA']
    return random.choice(locales)


async def apply_stealth_techniques(page):
    """
    Apply browser fingerprint masking techniques to evade detection.
    These patches hide automation indicators that anti-bot systems look for.
    """
    # Override navigator.webdriver flag
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    # Override automation indicators
    await page.add_init_script("""
        window.navigator.chrome = {
            runtime: {},
        };
    """)
    
    # Add realistic plugin array
    await page.add_init_script("""
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
    """)
    
    # Override permissions
    await page.add_init_script("""
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    """)
    
    # Randomize canvas fingerprint slightly
    await page.add_init_script("""
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter.apply(this, [parameter]);
        };
    """)


async def simulate_human_behavior(page):
    """
    Simulate realistic human mouse movements and interactions.
    """
    # Random mouse movements
    for _ in range(random.randint(2, 4)):
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.1, 0.3))
    
    # Random small scrolls (like reading)
    for _ in range(random.randint(1, 3)):
        scroll_amount = random.randint(50, 200)
        await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
        await asyncio.sleep(random.uniform(0.5, 1.5))


async def scrape_depop_advanced(
    search_term: str,
    max_items: int = 50,
    use_stealth: bool = True
) -> List[Dict[str, Any]]:
    """
    Advanced scraper with anti-bot evasion techniques.
    
    Args:
        search_term: Search query
        max_items: Maximum items to scrape
        use_stealth: Enable stealth mode (recommended)
        
    Returns:
        List of product dictionaries
    """
    items = []
    
    for attempt in range(MAX_RETRIES):
        try:
            async with async_playwright() as p:
                # Generate random browser configuration
                viewport = get_random_viewport()
                user_agent = ua.random
                timezone = get_random_timezone()
                locale = get_random_locale()
                
                logger.info(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Browser config:")
                logger.info(f"  Viewport: {viewport['width']}x{viewport['height']}")
                logger.info(f"  User-Agent: {user_agent[:60]}...")
                logger.info(f"  Locale: {locale}, TZ: {timezone}")
                
                # Launch browser with anti-detection args
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-gpu',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-background-networking',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-hang-monitor',
                        '--disable-prompt-on-repost',
                        '--metrics-recording-only',
                        '--safebrowsing-disable-auto-update',
                        '--password-store=basic',
                    ]
                )
                
                # Create context with randomized fingerprint
                context = await browser.new_context(
                    viewport=viewport,
                    user_agent=user_agent,
                    locale=locale,
                    timezone_id=timezone,
                    permissions=['geolocation'],
                    geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC
                    color_scheme='light',
                    device_scale_factor=random.uniform(1.0, 2.0),
                    is_mobile=random.choice([False, False, False, True]),  # 25% mobile
                    has_touch=random.choice([False, True]),
                )
                
                # Set additional realistic headers
                await context.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': f'{locale},en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'max-age=0',
                })
                
                page = await context.new_page()
                
                # Apply stealth techniques
                if use_stealth:
                    await apply_stealth_techniques(page)
                
                try:
                    # Navigate with realistic behavior
                    url = f"https://www.depop.com/search/?q={search_term.replace(' ', '%20')}"
                    logger.info(f"Navigating to: {url}")
                    
                    # Use domcontentloaded instead of networkidle (faster, more realistic)
                    await page.goto(url, wait_until='domcontentloaded', timeout=REQUEST_TIMEOUT)
                    
                    # Simulate human reading the page
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    if use_stealth:
                        await simulate_human_behavior(page)
                    
                    # Try multiple selectors
                    selectors = [
                        'a[href*="/products/"]',
                        '[data-testid="product__item"]',
                        '[data-testid*="product"]',
                        'article a',
                        '[class*="ProductCard"] a',
                        'li a[href*="/products/"]',
                    ]
                    
                    products = []
                    working_selector = None
                    
                    for selector in selectors:
                        try:
                            found = await page.query_selector_all(selector)
                            if len(found) >= 5:
                                products = found
                                working_selector = selector
                                logger.info(f"✓ Found {len(products)} products with: {selector}")
                                break
                        except:
                            continue
                    
                    if not products:
                        logger.warning("No products found - trying scroll and wait")
                        
                        # Scroll to trigger lazy loading
                        for i in range(SCROLL_ITERATIONS):
                            await page.evaluate('window.scrollBy(0, window.innerHeight)')
                            await asyncio.sleep(random.uniform(1, 2))
                        
                        # Try again
                        for selector in selectors:
                            try:
                                found = await page.query_selector_all(selector)
                                if len(found) >= 5:
                                    products = found
                                    working_selector = selector
                                    logger.info(f"✓ After scroll: {len(products)} products with: {selector}")
                                    break
                            except:
                                continue
                    
                    if not products:
                        # Save debug info
                        screenshot_path = f'/tmp/depop_advanced_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
                        await page.screenshot(path=screenshot_path, full_page=True)
                        
                        html_path = f'/tmp/depop_html_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
                        content = await page.content()
                        Path(html_path).write_text(content)
                        
                        logger.warning(f"Debug files saved:")
                        logger.warning(f"  Screenshot: {screenshot_path}")
                        logger.warning(f"  HTML: {html_path}")
                        
                        # Check for blocking
                        if 'captcha' in content.lower():
                            logger.error("CAPTCHA detected - need CAPTCHA solving service")
                        elif 'cloudflare' in content.lower():
                            logger.error("Cloudflare protection detected")
                        elif 'access denied' in content.lower():
                            logger.error("Access denied - IP may be blocked")
                        
                        await browser.close()
                        
                        if attempt < MAX_RETRIES - 1:
                            backoff = (2 ** attempt) * random.uniform(5, 10)
                            logger.info(f"Retrying in {backoff:.1f}s...")
                            await asyncio.sleep(backoff)
                            continue
                        else:
                            return items
                    
                    # Extract product data
                    logger.info(f"Extracting data from {min(len(products), max_items)} products...")
                    
                    for idx, product in enumerate(products[:max_items]):
                        try:
                            # Get href
                            href = await product.get_attribute('href')
                            if not href:
                                link = await product.query_selector('a[href*="/products/"]')
                                if link:
                                    href = await link.get_attribute('href')
                            
                            if not href or '/products/' not in href:
                                continue
                            
                            # Extract ID
                            external_id = href.strip('/').split('/')[-1]
                            
                            # Get text content
                            text = await product.inner_text()
                            lines = [l.strip() for l in text.split('\n') if l.strip()]
                            
                            # Extract title (usually first line)
                            title = lines[0] if lines else None
                            
                            # Extract price
                            price = None
                            for line in lines:
                                if any(sym in line for sym in ['£', '$', '€', 'USD', 'GBP']):
                                    price_str = ''.join(c for c in line if c.isdigit() or c == '.')
                                    try:
                                        price = float(price_str) if price_str else None
                                        break
                                    except:
                                        pass
                            
                            # Get image
                            img = await product.query_selector('img')
                            image_url = await img.get_attribute('src') if img else None
                            
                            # Construct full URL
                            full_url = f"https://www.depop.com{href}" if href.startswith('/') else href
                            
                            if external_id and title:
                                items.append({
                                    'external_id': external_id,
                                    'title': title,
                                    'price': price,
                                    'url': full_url,
                                    'image_url': image_url,
                                    'description': None
                                })
                                
                                if (idx + 1) % 10 == 0:
                                    logger.info(f"  Processed {idx + 1}/{min(len(products), max_items)}...")
                        
                        except Exception as e:
                            logger.debug(f"Error on product {idx}: {e}")
                            continue
                    
                    logger.info(f"✓ Successfully extracted {len(items)} items")
                    
                except PlaywrightTimeout:
                    logger.error("Page timeout")
                    await browser.close()
                    
                    if attempt < MAX_RETRIES - 1:
                        backoff = (2 ** attempt) * random.uniform(3, 6)
                        logger.info(f"Retrying in {backoff:.1f}s...")
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        return items
                
                finally:
                    await browser.close()
                
                # Success - break retry loop
                break
        
        except Exception as e:
            logger.error(f"Fatal error on attempt {attempt + 1}: {e}")
            if attempt == MAX_RETRIES - 1:
                logger.error(f"All {MAX_RETRIES} attempts failed")
    
    return items


def save_items(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """Save items to database with upsert logic."""
    saved, failed = 0, 0
    
    for item in items:
        try:
            execute_sync(
                """
                INSERT INTO depop_items (external_id, title, description, price, url, image_url)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (external_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    price = EXCLUDED.price,
                    url = EXCLUDED.url,
                    image_url = EXCLUDED.image_url,
                    updated_at = NOW();
                """,
                (item['external_id'], item['title'], item['description'],
                 item['price'], item['url'], item['image_url'])
            )
            saved += 1
        except Exception as e:
            logger.error(f"DB error for {item['external_id']}: {e}")
            failed += 1
    
    return {'saved': saved, 'failed': failed}


async def scrape_multiple_terms(search_terms: List[str], items_per_term: int = 50):
    """Scrape multiple search terms with delays between them."""
    total_found = 0
    total_saved = 0
    
    for idx, term in enumerate(search_terms, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Term {idx}/{len(search_terms)}: '{term}'")
        logger.info(f"{'='*60}")
        
        items = await scrape_depop_advanced(term, max_items=items_per_term, use_stealth=True)
        
        if items:
            total_found += len(items)
            result = save_items(items)
            total_saved += result['saved']
            logger.info(f"✓ Saved {result['saved']}/{len(items)} items")
        else:
            logger.warning(f"⚠️  No items found for '{term}'")
        
        # Polite delay between searches
        if idx < len(search_terms):
            delay = random.uniform(SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX)
            logger.info(f"Waiting {delay:.1f}s before next term...\n")
            await asyncio.sleep(delay)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"FINAL SUMMARY: Found {total_found}, Saved {total_saved}")
    logger.info(f"{'='*60}\n")
    
    return total_saved


async def main():
    """Main entry point."""
    logger.info("🚀 Advanced Depop Scraper with Anti-Bot Evasion")
    logger.info("="*60)
    
    search_terms = [
        "vintage tee",
        "denim jacket",
        "y2k dress",
    ]
    
    total = await scrape_multiple_terms(search_terms, items_per_term=20)
    
    if total > 0:
        logger.info(f"✅ Success! Scraped {total} items total")
    else:
        logger.warning("⚠️  No items scraped - check debug files")
        logger.info("\nTroubleshooting:")
        logger.info("  1. Check /tmp/depop_*.png and *.html for debug info")
        logger.info("  2. Depop may require CAPTCHA solving")
        logger.info("  3. Consider using residential proxies")
        logger.info("  4. Try alternative platforms (Grailed, Poshmark, Vinted)")
    
    return total


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result > 0 else 1)
