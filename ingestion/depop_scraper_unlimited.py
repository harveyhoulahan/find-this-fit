"""
UNLIMITED Depop scraper - scrapes as many items as possible.
Uses infinite scroll to load 100s or 1000s of products per category.
"""
import asyncio
import logging
import random
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

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


async def scrape_depop_unlimited(
    search_term: str, 
    max_items: int = 500,
    max_scrolls: int = 50
) -> List[Dict[str, Any]]:
    """
    Scraper that loads as many items as possible via infinite scroll.
    
    Args:
        search_term: What to search for
        max_items: Maximum items to extract (500 default, use 0 for unlimited)
        max_scrolls: How many times to scroll (each scroll loads ~24 items)
                     50 scrolls ≈ 1200 items, 100 scrolls ≈ 2400 items
    
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
            url = f"https://www.depop.com/search/?q={search_term.replace(' ', '%20')}"
            logger.info(f"Loading: {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(3, 5))
            
            # Aggressive scrolling to load TONS of items
            logger.info(f"Scrolling {max_scrolls} times to load items...")
            previous_count = 0
            no_new_items_count = 0
            
            for scroll_num in range(max_scrolls):
                # Scroll down aggressively
                await page.evaluate('window.scrollBy(0, window.innerHeight * 3)')
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Check how many items loaded so far
                current_count = await page.locator('[class*="productCardRoot"]').count()
                
                # Log progress every 10 scrolls
                if scroll_num % 10 == 0:
                    logger.info(f"  Scroll {scroll_num}/{max_scrolls}: {current_count} items loaded")
                
                # Stop if no new items after 5 scrolls (reached end)
                if current_count == previous_count:
                    no_new_items_count += 1
                    if no_new_items_count >= 5:
                        logger.info(f"  ✓ Reached end at scroll {scroll_num} ({current_count} items)")
                        break
                else:
                    no_new_items_count = 0
                
                previous_count = current_count
                
                # Stop if we've loaded enough
                if max_items > 0 and current_count >= max_items:
                    logger.info(f"  ✓ Reached target of {max_items} items at scroll {scroll_num}")
                    break
            
            # Now extract ALL loaded items
            containers = await page.query_selector_all('[class*="productCardRoot"]')
            total_found = len(containers)
            logger.info(f"✓ Found {total_found} total product cards on page")
            
            # Limit extraction if max_items specified
            items_to_extract = containers if max_items == 0 else containers[:max_items]
            logger.info(f"Extracting data from {len(items_to_extract)} items...")
            
            for idx, container in enumerate(items_to_extract):
                try:
                    # Find link within container
                    link = await container.query_selector('a[href*="/products/"]')
                    if not link:
                        continue
                    
                    href = await link.get_attribute('href')
                    if not href:
                        continue
                    
                    external_id = href.strip('/').split('/')[-1]
                    
                    # Get ALL text from the product card container
                    all_text = await container.inner_text()
                    lines = [l.strip() for l in all_text.split('\n') if l.strip()]
                    
                    if not lines:
                        continue
                    
                    # Extract price (has $ £ or €)
                    price = None
                    for line in lines:
                        if any(sym in line for sym in ['£', '$', '€']):
                            price_str = ''.join(c for c in line if c.isdigit() or c == '.')
                            try:
                                price = float(price_str) if price_str else None
                                break
                            except:
                                pass
                    
                    # Extract title - use the product ID formatted nicely
                    title = external_id.replace('-', ' ').title()
                    
                    # Get image
                    img = await container.query_selector('img')
                    image_url = None
                    if img:
                        image_url = await img.get_attribute('src')
                    
                    # Build URL
                    full_url = f"https://www.depop.com{href}" if href.startswith('/') else href
                    
                    # Only save if we have minimum data
                    if external_id and image_url:
                        items.append({
                            'external_id': external_id,
                            'title': title,
                            'price': price,
                            'url': full_url,
                            'image_url': image_url,
                            'description': None
                        })
                        
                        # Log every 50 items
                        if (idx + 1) % 50 == 0:
                            logger.info(f"  Extracted {idx + 1}/{len(items_to_extract)} items...")
                
                except Exception as e:
                    logger.debug(f"Error on container {idx}: {e}")
                    continue
            
            logger.info(f"✓ Successfully extracted {len(items)} items")
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
        finally:
            await browser.close()
    
    return items


def save_items(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """Save to database."""
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
            logger.error(f"DB error: {e}")
            failed += 1
    
    return {'saved': saved, 'failed': failed}


async def main():
    """Test run with unlimited scraping."""
    logger.info("="*70)
    logger.info("🚀 Depop UNLIMITED Scraper")
    logger.info("="*70)
    print()
    
    search_term = input("Search term (e.g., 'vintage hoodie'): ").strip() or "vintage hoodie"
    
    max_items_input = input("Max items to scrape (0 for unlimited, default 500): ").strip()
    max_items = int(max_items_input) if max_items_input.isdigit() else 500
    
    max_scrolls_input = input("Max scrolls (default 50, ~1200 items): ").strip()
    max_scrolls = int(max_scrolls_input) if max_scrolls_input.isdigit() else 50
    
    logger.info(f"Settings: max_items={max_items}, max_scrolls={max_scrolls}")
    print()
    
    items = await scrape_depop_unlimited(
        search_term=search_term,
        max_items=max_items,
        max_scrolls=max_scrolls
    )
    
    if items:
        logger.info("Saving to database...")
        result = save_items(items)
        
        logger.info("="*70)
        logger.info(f"✅ COMPLETE!")
        logger.info(f"   Scraped: {len(items)}")
        logger.info(f"   Saved: {result['saved']}")
        logger.info(f"   Failed: {result['failed']}")
        logger.info("="*70)
        
        # Show samples
        print("\nSample items:")
        for item in items[:5]:
            print(f"  • {item['title'][:60]} - ${item['price']}")
        
        return len(items)
    else:
        logger.warning("No items scraped")
        return 0


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result > 0 else 1)
