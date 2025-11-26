"""
Working Depop scraper based on actual 2025 page structure.
Depop uses React with lazy-loaded images and separate title/price elements.
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

# Import hybrid metadata extractor (combines text + visual)
try:
    from hybrid_metadata_extractor import enhance_item_metadata_hybrid
    VISUAL_AVAILABLE = True
except ImportError:
    from metadata_extractor import enhance_item_metadata
    VISUAL_AVAILABLE = False
    logger.warning("Visual metadata not available - using text-only extraction")

ua = UserAgent()

# CONFIGURATION: Set to True to use CLIP visual enhancement
# Depop has minimal text data, so visual extraction is HIGHLY recommended
USE_VISUAL_ENHANCEMENT = True  # Depop needs visual - minimal titles from URL slugs

# Toggle visual enhancement (slower but more accurate, especially for color)
USE_VISUAL_ENHANCEMENT = True  # Set to False for faster scraping without CLIP


async def scrape_depop_working(search_term: str, max_items: int = 50) -> List[Dict[str, Any]]:
    """
    Scraper that works with Depop's actual 2025 structure.
    Products are in a grid, title/price are NOT inside the link element.
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
            
            # Scroll to load more
            for _ in range(3):
                await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
                await asyncio.sleep(random.uniform(1, 2))
            
            # Find product cards by the correct class
            # Product data is in DIV with class containing 'productCardRoot'
            containers = await page.query_selector_all('[class*="productCardRoot"]')
            
            logger.info(f"Found {len(containers)} product cards")
            
            for idx, container in enumerate(containers[:max_items]):
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
                    
                    # Depop structure (observed):
                    # Line 0: Category/Type (e.g., "Other", "Tops")
                    # Line 1: Size (e.g., "S", "M", "L")
                    # Line 2: Price (e.g., "$15.00")
                    # Sometimes there's a title before these
                    
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
                    # Since Depop doesn't show title in the card, use the URL slug
                    title = external_id.replace('-', ' ').title()
                    
                    # Get image
                    img = await container.query_selector('img')
                    image_url = None
                    if img:
                        image_url = await img.get_attribute('src')
                    
                    # Build URL
                    full_url = f"https://www.depop.com{href}" if href.startswith('/') else href
                    
                    # Only save if we have minimum data (price and image)
                    if external_id and image_url:
                        item = {
                            'source': 'depop',
                            'external_id': external_id,
                            'title': title,
                            'price': price,
                            'url': full_url,
                            'image_url': image_url,
                            'description': None
                        }
                        
                        # Extract structured metadata (text + optional visual)
                        # Depop ESPECIALLY benefits from visual - titles are just URL slugs
                        if USE_VISUAL_ENHANCEMENT and VISUAL_AVAILABLE:
                            item = enhance_item_metadata_hybrid(
                                item,
                                use_visual=True,
                                visual_confidence=0.20,  # Lower threshold for Depop - we need the help!
                                prefer_visual_for=['color', 'category', 'brand']  # Trust visual for everything except size
                            )
                        else:
                            from metadata_extractor import enhance_item_metadata
                            item = enhance_item_metadata(item)

                        
                        items.append(item)
                        
                        logger.debug(f"✓ [{idx+1}] {title[:40]}... - ${price}")
                
                except Exception as e:
                    logger.debug(f"Error on container {idx}: {e}")
                    continue
            
            logger.info(f"✓ Extracted {len(items)} items")
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
        finally:
            await browser.close()
    
    return items


def save_items(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """Save to unified fashion_items table with structured metadata."""
    saved, failed = 0, 0
    
    for item in items:
        try:
            execute_sync(
                """
                INSERT INTO fashion_items (
                    source, external_id, title, description, price, 
                    url, image_url,
                    brand, category, color, condition, size
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, external_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    price = EXCLUDED.price,
                    url = EXCLUDED.url,
                    image_url = EXCLUDED.image_url,
                    brand = EXCLUDED.brand,
                    category = EXCLUDED.category,
                    color = EXCLUDED.color,
                    condition = EXCLUDED.condition,
                    size = EXCLUDED.size,
                    updated_at = NOW();
                """,
                (item['source'], item['external_id'], item['title'], item.get('description'),
                 item.get('price'), item['url'], item['image_url'],
                 item.get('brand', 'Unknown'), item.get('category', 'other'),
                 item.get('color', 'unknown'), item.get('condition', 'Good'),
                 item.get('size', 'M'))
            )
            saved += 1
        except Exception as e:
            logger.error(f"DB error: {e}")
            failed += 1
    
    return {'saved': saved, 'failed': failed}


async def main():
    """Test run."""
    logger.info("🚀 Depop Scraper - Working Version")
    print()
    
    search_terms = ["vintage tee", "denim jacket"]
    total_saved = 0
    
    for term in search_terms:
        logger.info(f"Scraping: '{term}'")
        items = await scrape_depop_working(term, max_items=20)
        
        if items:
            result = save_items(items)
            total_saved += result['saved']
            logger.info(f"✓ Saved {result['saved']}/{len(items)} items\n")
            
            # Show samples
            for item in items[:3]:
                print(f"  • {item['title']} - ${item['price']}")
        else:
            logger.warning(f"No items for '{term}'\n")
        
        # Delay between searches
        if term != search_terms[-1]:
            await asyncio.sleep(random.uniform(4, 7))
    
    print()
    logger.info(f"✅ Complete! Total saved: {total_saved}")
    
    return total_saved


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result > 0 else 1)
