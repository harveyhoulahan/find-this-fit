"""
Practical Depop scraper - works around modern anti-bot measures.

Note: Depop has strong bot detection. For production use, consider:
1. Using Depop's official API (if available)
2. Manual data collection with proper permissions
3. Alternative data sources like Grailed, Poshmark, etc.

This script demonstrates the scraping approach but may require adjustments.
"""
import asyncio
import logging
import random
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed")
    sys.exit(1)

from db import execute_sync  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def scrape_depop_realistic(search_term: str, max_items: int = 20) -> List[Dict[str, Any]]:
    """
    Attempt to scrape Depop with realistic browser behavior.
    Falls back gracefully if blocked.
    """
    items = []
    
    async with async_playwright() as p:
        # Launch with realistic settings
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US'
        )
        
        page = await context.new_page()
        
        try:
            url = f"https://www.depop.com/search/?q={search_term.replace(' ', '%20')}"
            logger.info(f"Navigating to: {url}")
            
            # Use 'domcontentloaded' instead of 'networkidle' - faster and more reliable
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            
            # Wait a bit for dynamic content
            await asyncio.sleep(random.uniform(2, 4))
            
            # Try multiple possible selectors
            selectors = [
                'a[href*="/products/"]',  # Most generic - any link to a product
                '[data-testid="product__item"]',
                '[class*="ProductCard"]',
                'article a[href*="/products/"]',
            ]
            
            products = []
            for selector in selectors:
                try:
                    found = await page.query_selector_all(selector)
                    if len(found) > 5:  # Need reasonable number
                        products = found
                        logger.info(f"✓ Found {len(products)} products with selector: {selector}")
                        break
                except:
                    continue
            
            if not products:
                logger.warning("No products found with any selector")
                screenshot_path = f'/tmp/depop_failed_{search_term.replace(" ", "_")}.png'
                await page.screenshot(path=screenshot_path)
                logger.info(f"Debug screenshot: {screenshot_path}")
                await browser.close()
                return items
            
            # Extract data from products
            for idx, product in enumerate(products[:max_items]):
                try:
                    # Get link
                    if await product.get_attribute('href'):
                        href = await product.get_attribute('href')
                        link_elem = product
                    else:
                        link_elem = await product.query_selector('a[href*="/products/"]')
                        if not link_elem:
                            continue
                        href = await link_elem.get_attribute('href')
                    
                    if not href:
                        continue
                    
                    # Extract ID
                    external_id = href.strip('/').split('/')[-1]
                    
                    # Get all text content (contains title and price)
                    text_content = await product.inner_text()
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    
                    # Heuristic: title is usually the first substantial line
                    title = lines[0] if lines else None
                    
                    # Find price (contains currency symbol)
                    price = None
                    for line in lines:
                        if any(symbol in line for symbol in ['£', '$', '€']):
                            price_clean = ''.join(c for c in line if c.isdigit() or c == '.')
                            try:
                                price = float(price_clean)
                                break
                            except:
                                pass
                    
                    # Get image
                    img = await product.query_selector('img')
                    image_url = await img.get_attribute('src') if img else None
                    
                    # Build full URL
                    full_url = f"https://www.depop.com{href}" if href.startswith('/') else href
                    
                    if external_id and title:  # Minimum required data
                        items.append({
                            'external_id': external_id,
                            'title': title,
                            'price': price,
                            'url': full_url,
                            'image_url': image_url,
                            'description': None
                        })
                        logger.debug(f"✓ {title} - ${price}")
                
                except Exception as e:
                    logger.debug(f"Error extracting product {idx}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(items)} items")
            
        except PlaywrightTimeout:
            logger.error("Page load timeout - Depop may be blocking requests")
        except Exception as e:
            logger.error(f"Scraping error: {e}")
        finally:
            await browser.close()
    
    return items


def save_items(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """Save items to database."""
    saved, failed = 0, 0
    
    for item in items:
        try:
            execute_sync(
                """
                INSERT INTO depop_items (external_id, title, description, price, url, image_url)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (external_id) DO UPDATE SET
                    title = EXCLUDED.title,
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
            logger.error(f"Failed to save {item['external_id']}: {e}")
            failed += 1
    
    return {'saved': saved, 'failed': failed}


async def main():
    """Test run with single search term."""
    logger.info("🚀 Testing Depop scraper...")
    logger.info("Note: Depop has anti-bot measures. Results may vary.\n")
    
    search_term = "vintage tee"
    items = await scrape_depop_realistic(search_term, max_items=10)
    
    if items:
        logger.info(f"\n✓ Found {len(items)} items")
        result = save_items(items)
        logger.info(f"✓ Saved {result['saved']} items to database")
        
        print("\nSample items:")
        for item in items[:3]:
            print(f"  • {item['title']} - ${item['price']}")
            print(f"    {item['url']}\n")
    else:
        logger.warning("⚠️  No items scraped")
        logger.info("\nPossible issues:")
        logger.info("  1. Depop is blocking automated access")
        logger.info("  2. Page structure has changed")
        logger.info("  3. Network/firewall blocking")
        logger.info("\nConsider:")
        logger.info("  • Using official APIs")
        logger.info("  • Adding CAPTCHA solving service")
        logger.info("  • Using residential proxies")
        logger.info("  • Scraping alternative platforms (Grailed, Poshmark)")
    
    return len(items)


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result > 0 else 1)
