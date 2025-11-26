"""
Grailed scraper - menswear-focused fashion marketplace.
Grailed has a cleaner HTML structure than Depop and is easier to scrape.
"""
import asyncio
import logging
import random
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from playwright.async_api import async_playwright
from fake_useragent import UserAgent
from db import execute_sync

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ua = UserAgent()


async def scrape_grailed(search_term: str, max_items: int = 50) -> List[Dict[str, Any]]:
    """
    Scrape Grailed marketplace.
    
    Grailed URL structure: https://www.grailed.com/shop?query=vintage+hoodie
    
    Args:
        search_term: What to search for
        max_items: Maximum items to extract
    
    Returns:
        List of scraped items
    """
    items = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=ua.random
        )
        
        page = await context.new_page()
        
        try:
            # Grailed uses /shop endpoint with query param
            query_encoded = search_term.replace(' ', '+')
            url = f"https://www.grailed.com/shop?query={query_encoded}"
            logger.info(f"Loading: {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(3, 5))
            
            # Scroll to load more items
            for _ in range(5):
                await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
                await asyncio.sleep(random.uniform(1, 2))
            
            # Grailed uses article tags for products or feed-item class
            # Try multiple selectors - updated for 2025 Grailed structure
            selectors = [
                'article[data-testid="FeedItem"]',
                'div[class*="FeedItem"]',
                'a[class*="listing"]',
                'div[class*="feed-item"]',
                'div[data-cy="listing"]',
                '[class*="ListingItem"]',
                'a[href*="/listings/"]'  # Fallback: any link to a listing
            ]
            
            containers = []
            for selector in selectors:
                containers = await page.query_selector_all(selector)
                if containers:
                    logger.info(f"✓ Found {len(containers)} items with selector: {selector}")
                    break
            
            if not containers:
                # Last resort: get page HTML and log some of it
                html = await page.content()
                logger.warning("Could not find product containers")
                logger.debug(f"Page has {len(html)} chars of HTML")
                # Try to find any product links
                all_links = await page.query_selector_all('a[href*="/listings/"]')
                if all_links:
                    logger.info(f"Found {len(all_links)} listing links as fallback")
                    containers = all_links
                else:
                    return items
            
            logger.info(f"Extracting data from {min(len(containers), max_items)} items...")
            
            for idx, container in enumerate(containers[:max_items]):
                try:
                    # If container is already a link, use it directly
                    if await container.evaluate('el => el.tagName') == 'A':
                        link = container
                        # Get parent for additional data
                        parent = await container.evaluate_handle('el => el.parentElement')
                        container = parent.as_element() or container
                    else:
                        # Find product link within container
                        link = await container.query_selector('a[href*="/listings/"]')
                        if not link:
                            # Try alternative
                            link = await container.query_selector('a')
                    
                    if not link:
                        continue
                    
                    href = await link.get_attribute('href')
                    if not href or '/listings/' not in href:
                        continue
                    
                    # Extract ID from URL (/listings/12345-title)
                    external_id = href.split('/listings/')[-1].split('?')[0]
                    
                    # Get title - prioritize actual product title over designer/brand
                    title = None
                    
                    # Try multiple selectors in order of preference
                    title_selectors = [
                        '[class*="ListingTitle"]',  # Grailed's listing title class
                        '[class*="listing-title"]',
                        'p[class*="title"]:not([class*="designer"]):not([class*="brand"])',  # Title but not designer
                        'h3:not([class*="designer"]):not([class*="brand"])',
                        'h4:not([class*="designer"]):not([class*="brand"])',
                        '[data-testid*="title"]'
                    ]
                    
                    for sel in title_selectors:
                        title_elem = await container.query_selector(sel)
                        if title_elem:
                            title_text = await title_elem.inner_text()
                            if title_text and len(title_text.strip()) > 2:
                                title = title_text.strip()
                                break
                    
                    # Fallback: try to parse from URL slug (last part of external_id)
                    if not title or len(title) < 3:
                        # Extract title from URL slug (e.g., "12345-vintage-nike-hoodie" -> "vintage nike hoodie")
                        url_parts = external_id.split('-')
                        if len(url_parts) > 1:
                            # Skip the ID part (first element if it's all digits)
                            if url_parts[0].isdigit():
                                title = ' '.join(url_parts[1:]).title()
                            else:
                                title = external_id.replace('-', ' ').title()
                        else:
                            title = external_id.replace('-', ' ').title()
                    
                    # Clean up title - remove extra whitespace and newlines
                    title = ' '.join(title.split())
                    
                    # Limit title length
                    if len(title) > 100:
                        title = title[:100].strip()
                    
                    # Extract price - look more broadly
                    price = None
                    price_selectors = [
                        '[class*="price"]', 
                        '[class*="Price"]', 
                        'p:has-text("$")',
                        'span:has-text("$")',
                        'div:has-text("$")'
                    ]
                    
                    for sel in price_selectors:
                        price_elem = await container.query_selector(sel)
                        if price_elem:
                            price_text = await price_elem.inner_text()
                            # Extract number from text like "$45" or "$45.00" or "$1,234.56"
                            price_text = price_text.replace(',', '')  # Remove thousand separators
                            price_str = ''.join(c for c in price_text if c.isdigit() or c == '.')
                            try:
                                if price_str:
                                    price = float(price_str)
                                    # Sanity check - prices shouldn't be crazy high
                                    if 1 <= price <= 50000:
                                        break
                                    else:
                                        price = None
                            except:
                                pass
                    
                    # Get image
                    image_url = None
                    img = await container.query_selector('img')
                    if img:
                        image_url = await img.get_attribute('src')
                        # Grailed uses lazy loading, check data-src too
                        if not image_url:
                            image_url = await img.get_attribute('data-src')
                    
                    # Build full URL
                    if href.startswith('/'):
                        full_url = f"https://www.grailed.com{href}"
                    else:
                        full_url = href
                    
                    # Extract seller name if available
                    seller_name = None
                    seller_elem = await container.query_selector('[class*="seller"], [class*="username"]')
                    if seller_elem:
                        seller_name = await seller_elem.inner_text()
                    
                    # Only save if we have minimum data
                    if external_id and image_url:
                        items.append({
                            'source': 'grailed',
                            'external_id': external_id,
                            'title': title,
                            'price': price,
                            'url': full_url,
                            'image_url': image_url,
                            'seller_name': seller_name,
                            'description': None
                        })
                        
                        if (idx + 1) % 10 == 0:
                            logger.info(f"  Extracted {idx + 1} items...")
                
                except Exception as e:
                    logger.debug(f"Error on item {idx}: {e}")
                    continue
            
            logger.info(f"✓ Successfully extracted {len(items)} Grailed items")
            
        except Exception as e:
            logger.error(f"Grailed scraping failed: {e}")
        finally:
            await browser.close()
    
    return items


def save_items(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """Save items to unified fashion_items table."""
    saved, failed = 0, 0
    
    for item in items:
        try:
            execute_sync(
                """
                INSERT INTO fashion_items (
                    source, external_id, title, description, price, 
                    url, image_url, seller_name
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, external_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    price = EXCLUDED.price,
                    url = EXCLUDED.url,
                    image_url = EXCLUDED.image_url,
                    seller_name = EXCLUDED.seller_name,
                    updated_at = NOW();
                """,
                (item['source'], item['external_id'], item['title'], 
                 item['description'], item['price'], item['url'], 
                 item['image_url'], item['seller_name'])
            )
            saved += 1
        except Exception as e:
            logger.error(f"DB error for {item['external_id']}: {e}")
            failed += 1
    
    return {'saved': saved, 'failed': failed}


async def main():
    """Test Grailed scraper."""
    logger.info("="*70)
    logger.info("🛍️  GRAILED SCRAPER TEST")
    logger.info("="*70)
    print()
    
    search_term = "vintage hoodie"
    logger.info(f"Searching Grailed for: '{search_term}'")
    
    items = await scrape_grailed(search_term, max_items=30)
    
    if items:
        result = save_items(items)
        
        logger.info("="*70)
        logger.info(f"✅ Grailed scrape complete!")
        logger.info(f"   Scraped: {len(items)}")
        logger.info(f"   Saved: {result['saved']}")
        logger.info(f"   Failed: {result['failed']}")
        logger.info("="*70)
        print()
        
        # Show samples
        logger.info("Sample items:")
        for item in items[:5]:
            print(f"  • {item['title'][:50]} - ${item['price']}")
            if item['seller_name']:
                print(f"    Seller: {item['seller_name']}")
        
        return len(items)
    else:
        logger.warning("No items scraped from Grailed")
        return 0


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result > 0 else 1)
