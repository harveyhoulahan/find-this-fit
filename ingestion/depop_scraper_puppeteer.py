"""
Production Depop scraper using Playwright (headless browser).
Bypasses bot detection by rendering JavaScript like a real browser.

Install: pip install playwright && playwright install chromium
"""
import asyncio
import logging
import random
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from config import REQUEST_TIMEOUT  # noqa: E402
from db import execute_sync  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scrape_depop_with_playwright(search_term: str, max_items: int = 50) -> List[Dict[str, Any]]:
    """
    Scrape Depop using Playwright headless browser.
    This bypasses bot detection by acting like a real browser.
    """
    from playwright.async_api import async_playwright
    
    items = []
    
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        
        # Create context with realistic user agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )
        
        page = await context.new_page()
        
        try:
            # Navigate to search page
            url = f"https://www.depop.com/search/?q={search_term.replace(' ', '+')}"
            logger.info(f"Navigating to: {url}")
            
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait for products to load
            await page.wait_for_selector('a[data-testid="product__item"]', timeout=10000)
            
            # Scroll to load more items (Depop uses infinite scroll)
            for _ in range(3):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # Extract product data
            products = await page.query_selector_all('a[data-testid="product__item"]')
            
            logger.info(f"Found {len(products)} products")
            
            for product in products[:max_items]:
                try:
                    # Extract URL
                    href = await product.get_attribute('href')
                    if not href or '/products/' not in href:
                        continue
                    
                    # Extract external ID from URL
                    external_id = href.strip('/').split('/')[-1]
                    
                    # Extract title
                    title_elem = await product.query_selector('[data-testid="product__title"]')
                    title = await title_elem.inner_text() if title_elem else None
                    
                    # Extract price
                    price_elem = await product.query_selector('[data-testid="product__price"]')
                    price_text = await price_elem.inner_text() if price_elem else None
                    price = _parse_price(price_text) if price_text else None
                    
                    # Extract image URL
                    img_elem = await product.query_selector('img')
                    image_url = await img_elem.get_attribute('src') if img_elem else None
                    
                    # Extract description (optional - requires visiting product page)
                    description = None
                    
                    items.append({
                        'external_id': external_id,
                        'title': title,
                        'price': price,
                        'url': f"https://www.depop.com{href}" if href.startswith('/') else href,
                        'image_url': image_url,
                        'description': description,
                    })
                    
                    logger.info(f"Scraped: {title} - ${price}")
                    
                except Exception as e:
                    logger.error(f"Error extracting product: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
        
        finally:
            await browser.close()
    
    return items


def _parse_price(text: str) -> float:
    """Extract numeric price from text like '$45.00' or '£35'."""
    if not text:
        return None
    clean = "".join(ch for ch in text if ch.isdigit() or ch == "." or ch == ",")
    try:
        return float(clean.replace(",", ""))
    except ValueError:
        return None


def save_listing(item: Dict[str, Any]):
    """Upsert listing into database."""
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
        (
            item.get("external_id"),
            item.get("title"),
            item.get("description"),
            item.get("price"),
            item.get("url"),
            item.get("image_url"),
        ),
    )


async def scrape_multiple_terms(search_terms: List[str], items_per_term: int = 50):
    """Scrape multiple search terms."""
    total_saved = 0
    
    for term in search_terms:
        logger.info(f"Scraping '{term}'...")
        items = await scrape_depop_with_playwright(term, max_items=items_per_term)
        
        for item in items:
            try:
                save_listing(item)
                total_saved += 1
            except Exception as e:
                logger.error(f"Failed to save {item.get('external_id')}: {e}")
        
        # Polite delay between searches
        await asyncio.sleep(random.uniform(3.0, 5.0))
    
    logger.info(f"Scraping complete. Saved {total_saved} items.")


if __name__ == "__main__":
    # Run scraper
    search_terms = [
        "vintage tee",
        "denim jacket",
        "y2k dress",
        "vintage hoodie",
        "streetwear",
    ]
    
    asyncio.run(scrape_multiple_terms(search_terms, items_per_term=50))
