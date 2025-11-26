"""
Vinted scraper - European secondhand fashion marketplace.
Vinted is popular in EU/UK with good variety of vintage and contemporary items.
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
USE_VISUAL_ENHANCEMENT = False  # Change to True for better color detection

# Toggle visual enhancement (slower but more accurate, especially for color)
USE_VISUAL_ENHANCEMENT = True  # Set to False for faster scraping without CLIP


async def scrape_vinted(search_term: str, max_items: int = 50, region: str = 'us') -> List[Dict[str, Any]]:
    """
    Scrape Vinted marketplace.
    
    Vinted URL structure: https://www.vinted.com/catalog?search_text=vintage+hoodie
    Regional variants: vinted.com (US), vinted.co.uk (UK), vinted.fr (FR), etc.
    
    Args:
        search_term: What to search for
        max_items: Maximum items to extract
        region: 'us', 'uk', 'fr', 'de', 'es', 'it', etc.
    
    Returns:
        List of scraped items
    """
    items = []
    
    # Regional domains
    domains = {
        'us': 'vinted.com',
        'uk': 'vinted.co.uk',
        'fr': 'vinted.fr',
        'de': 'vinted.de',
        'es': 'vinted.es',
        'it': 'vinted.it',
        'pl': 'vinted.pl',
    }
    
    domain = domains.get(region, 'vinted.com')
    
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
            # Vinted uses catalog endpoint
            query_encoded = search_term.replace(' ', '+')
            url = f"https://www.{domain}/catalog?search_text={query_encoded}"
            logger.info(f"Loading: {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(3, 5))
            
            # Handle cookie consent if present
            try:
                accept_btn = await page.query_selector('button:has-text("Accept"), button:has-text("I agree")')
                if accept_btn:
                    await accept_btn.click()
                    await asyncio.sleep(1)
            except:
                pass
            
            # Scroll to load more items
            for _ in range(5):
                await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
                await asyncio.sleep(random.uniform(1, 2))
            
            # Vinted uses various selectors for items - updated for 2025
            selectors = [
                'div[data-testid="item-box"]',
                'a[class*="ItemBox"]',
                'div[class*="feed-grid"] a',
                'article[class*="item"]',
                'a[href*="/items/"]'  # Fallback: any link to an item
            ]
            
            containers = []
            for selector in selectors:
                containers = await page.query_selector_all(selector)
                if containers:
                    logger.info(f"✓ Found {len(containers)} items with selector: {selector}")
                    break
            
            if not containers:
                logger.warning("Could not find product containers")
                # Last resort: try finding item links
                all_links = await page.query_selector_all('a[href*="/items/"]')
                if all_links:
                    logger.info(f"Found {len(all_links)} item links as fallback")
                    containers = all_links
                else:
                    return items
            
            logger.info(f"Extracting data from {min(len(containers), max_items)} items...")
            
            for idx, container in enumerate(containers[:max_items]):
                try:
                    # If container is already a link, use it directly but get parent for complete data
                    tag_name = await container.evaluate('el => el.tagName')
                    if tag_name == 'A':
                        link = container
                        # Get parent element which should have both title and price
                        try:
                            parent = await container.evaluate_handle('el => el.closest("div[class*=feed-grid__item], article, li") || el.parentElement')
                            search_container = parent.as_element() or container
                        except:
                            search_container = container
                    else:
                        link = await container.query_selector('a')
                        search_container = container
                    
                    if not link:
                        continue
                    
                    href = await link.get_attribute('href')
                    if not href or '/items/' not in href:
                        continue
                    
                    # Extract ID and title from URL (/items/12345-title or /items/12345)
                    url_suffix = href.split('/items/')[-1].split('?')[0]
                    
                    # Parse ID and potential title from URL
                    # URL format: /items/3918259716-vintage-nike-hoodie or just /items/3918259716
                    if '-' in url_suffix:
                        parts = url_suffix.split('-', 1)  # Split on first dash only
                        external_id = parts[0]
                        url_title = parts[1].replace('-', ' ').title() if len(parts) > 1 else None
                    else:
                        external_id = url_suffix
                        url_title = None
                    
                    # Get title - improved extraction with better selectors
                    title = None
                    brand_name = None
                    
                    # First, try to extract brand from link (usually first line)
                    try:
                        link_text = await link.inner_text()
                        if link_text:
                            first_line = link_text.split('\n')[0].strip()
                            # If it's short and doesn't have price symbols, it's likely the brand
                            if 2 < len(first_line) < 30 and '$' not in first_line and '€' not in first_line and '£' not in first_line:
                                brand_name = first_line
                    except:
                        pass
                    
                    # Use URL title as the base (most reliable for actual product description)
                    if url_title and len(url_title) > 3:
                        # If we have a brand and it's not already in the title, prepend it
                        if brand_name and brand_name.lower() not in url_title.lower():
                            title = f"{brand_name} {url_title}"
                        else:
                            title = url_title
                    
                    # Fallback: try specific selectors in the search container
                    if not title:
                        title_selectors = [
                            '[class*="ItemBox-title"]',
                            '[class*="item-title"]',
                            '[data-testid*="title"]',
                            '[class*="ItemBox"] h3',
                            '[class*="ItemBox"] h4',
                            'h3:not([class*="price"]):not([class*="brand"])',
                            'h4:not([class*="price"]):not([class*="brand"])',
                            'p[class*="title"]:not([class*="price"]):not([class*="brand"])'
                        ]
                        
                        for sel in title_selectors:
                            try:
                                title_elem = await search_container.query_selector(sel)
                                if title_elem:
                                    title_text = await title_elem.inner_text()
                                    # Validate it's not a price or ID
                                    if title_text and len(title_text.strip()) > 2:
                                        clean_text = title_text.strip()
                                        # Skip if it's just numbers (likely an ID or price)
                                        if not clean_text.replace('.', '').replace(',', '').isdigit():
                                            # Skip if it contains currency symbols (likely price)
                                            if not any(sym in clean_text for sym in ['€', '$', '£', 'USD', 'EUR', 'GBP']):
                                                title = clean_text
                                                break
                            except:
                                continue
                    
                    # Fallback: try specific selectors
                    if not title:
                        title_selectors = [
                            '[class*="ItemBox-title"]',
                            '[class*="item-title"]',
                            '[data-testid*="title"]',
                            '[class*="ItemBox"] h3',
                            '[class*="ItemBox"] h4',
                            'h3:not([class*="price"]):not([class*="brand"])',
                            'h4:not([class*="price"]):not([class*="brand"])',
                            'p[class*="title"]:not([class*="price"]):not([class*="brand"])'
                        ]
                        
                        for sel in title_selectors:
                            try:
                                title_elem = await search_container.query_selector(sel)
                                if title_elem:
                                    title_text = await title_elem.inner_text()
                                    if title_text and len(title_text.strip()) > 2:
                                        clean_text = title_text.strip()
                                        if not clean_text.replace('.', '').replace(',', '').isdigit():
                                            if not any(sym in clean_text for sym in ['€', '$', '£', 'USD', 'EUR', 'GBP']):
                                                title = clean_text
                                                break
                            except:
                                continue
                    
                    # Final fallback: use brand name or generic title
                    if not title:
                        if brand_name:
                            title = brand_name
                        else:
                            title = f"Vinted Item {external_id}"
                    
                    # Clean up title - remove extra whitespace and newlines
                    title = ' '.join(title.split())
                    
                    # Limit title length
                    if len(title) > 100:
                        title = title[:100].strip()
                    
                    # Extract price - improved extraction with better validation
                    price = None
                    currency = 'USD'
                    
                    # Vinted US shows prices as plain numbers without $ symbol
                    # Try specific selectors first, then broader text-based search
                    price_selectors = [
                        '[class*="ItemBox-price"]',
                        '[class*="item-price"]',
                        '[data-testid*="price"]',
                        '[class*="price"]:not([class*="old"]):not([class*="original"])',
                        '[class*="Price"]:not([class*="old"]):not([class*="original"])',
                        'p:has-text("€"), p:has-text("$"), p:has-text("£")',
                        'span:has-text("€"), span:has-text("$"), span:has-text("£")',
                        'div:has-text("€"), div:has-text("$"), div:has-text("£")',
                        # Also try to find standalone numbers (Vinted US format)
                        'p', 'span', 'div'
                    ]
                    
                    for sel in price_selectors:
                        try:
                            price_elems = await search_container.query_selector_all(sel)
                            for price_elem in price_elems:
                                price_text = await price_elem.inner_text()
                                if not price_text or len(price_text) > 20:  # Skip if too long
                                    continue
                                
                                price_text = price_text.strip()
                                
                                # Check if it looks like a price
                                # Could be: "$25", "25.00", "€25,50", "25"
                                
                                # Detect currency
                                if '€' in price_text:
                                    currency = 'EUR'
                                elif '£' in price_text:
                                    currency = 'GBP'
                                elif '$' in price_text:
                                    currency = 'USD'
                                
                                # Extract number - handle both EU (123,45) and US (123.45) formats
                                # Remove currency symbols and whitespace
                                clean_text = price_text.replace('€', '').replace('$', '').replace('£', '').strip()
                                
                                # If it's ONLY digits (with optional decimal), it might be a price
                                if clean_text.replace('.', '', 1).replace(',', '', 1).isdigit():
                                    # Handle EU format (comma as decimal separator)
                                    if ',' in clean_text and '.' not in clean_text:
                                        # e.g., "12,50" -> "12.50"
                                        clean_text = clean_text.replace(',', '.')
                                    elif ',' in clean_text and '.' in clean_text:
                                        # Has both - determine which is decimal
                                        comma_pos = clean_text.rfind(',')
                                        dot_pos = clean_text.rfind('.')
                                        if comma_pos > dot_pos:
                                            # Comma is decimal (EU format: 1.234,56)
                                            clean_text = clean_text.replace('.', '').replace(',', '.')
                                        else:
                                            # Dot is decimal (US format: 1,234.56)
                                            clean_text = clean_text.replace(',', '')
                                    
                                    # Extract digits and decimal point
                                    price_str = ''.join(c for c in clean_text if c.isdigit() or c == '.')
                                    
                                    try:
                                        if price_str and price_str != '.':
                                            extracted_price = float(price_str)
                                            # Sanity check - reasonable price range
                                            if 0.1 <= extracted_price <= 50000:
                                                price = extracted_price
                                                break
                                    except ValueError:
                                        continue
                            
                            if price is not None:
                                break
                                
                        except Exception as e:
                            logger.debug(f"Error extracting price with selector {sel}: {e}")
                            continue
                    
                    # Get image
                    image_url = None
                    img = await search_container.query_selector('img')
                    if img:
                        # Try src, data-src, data-lazy-src
                        for attr in ['src', 'data-src', 'data-lazy-src']:
                            image_url = await img.get_attribute(attr)
                            if image_url and image_url.startswith('http'):
                                break
                    
                    # Build full URL
                    if href.startswith('/'):
                        full_url = f"https://www.{domain}{href}"
                    else:
                        full_url = href
                    
                    # Extract brand if available
                    brand = None
                    brand_elem = await search_container.query_selector('[class*="brand"], [class*="Brand"]')
                    if brand_elem:
                        brand = await brand_elem.inner_text()
                        brand = brand.strip()
                    
                    # Extract size if available
                    size = None
                    size_elem = await search_container.query_selector('[class*="size"], [class*="Size"]')
                    if size_elem:
                        size = await size_elem.inner_text()
                        size = size.strip()
                    
                    # Only save if we have minimum data
                    if external_id and image_url:
                        item = {
                            'source': 'vinted',
                            'external_id': external_id,
                            'title': title,
                            'price': price,
                            'currency': currency,
                            'url': full_url,
                            'image_url': image_url,
                            'brand': brand,
                            'size': size,
                            'description': None
                        }
                        
                        # Extract structured metadata (text + optional visual)
                        # Vinted especially benefits from visual - minimal titles
                        if USE_VISUAL_ENHANCEMENT and VISUAL_AVAILABLE:
                            item = enhance_item_metadata_hybrid(
                                item,
                                use_visual=True,
                                prefer_visual_for=['color', 'category']  # Visual helps fill gaps
                            )
                        else:
                            from metadata_extractor import enhance_item_metadata
                            item = enhance_item_metadata(item)

                        
                        items.append(item)
                        
                        if (idx + 1) % 10 == 0:
                            logger.info(f"  Extracted {idx + 1} items...")
                
                except Exception as e:
                    logger.debug(f"Error on item {idx}: {e}")
                    continue
            
            logger.info(f"✓ Successfully extracted {len(items)} Vinted items")
            
        except Exception as e:
            logger.error(f"Vinted scraping failed: {e}")
        finally:
            await browser.close()
    
    return items


def save_items(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """Save items to unified fashion_items table with structured metadata."""
    saved, failed = 0, 0
    
    for item in items:
        try:
            execute_sync(
                """
                INSERT INTO fashion_items (
                    source, external_id, title, description, price, currency,
                    url, image_url, 
                    brand, category, color, condition, size
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, external_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    price = EXCLUDED.price,
                    currency = EXCLUDED.currency,
                    url = EXCLUDED.url,
                    image_url = EXCLUDED.image_url,
                    brand = EXCLUDED.brand,
                    category = EXCLUDED.category,
                    color = EXCLUDED.color,
                    condition = EXCLUDED.condition,
                    size = EXCLUDED.size,
                    updated_at = NOW();
                """,
                (item['source'], item['external_id'], item['title'], 
                 item.get('description'), item.get('price'), item.get('currency', 'USD'),
                 item['url'], item['image_url'], 
                 item.get('brand', 'Unknown'), item.get('category', 'other'),
                 item.get('color', 'unknown'), item.get('condition', 'Good'),
                 item.get('size', 'M'))
            )
            saved += 1
        except Exception as e:
            logger.error(f"DB error for {item['external_id']}: {e}")
            failed += 1
    
    return {'saved': saved, 'failed': failed}


async def main():
    """Test Vinted scraper."""
    logger.info("="*70)
    logger.info("🛍️  VINTED SCRAPER TEST")
    logger.info("="*70)
    print()
    
    search_term = "vintage hoodie"
    region = "us"  # Change to 'uk', 'fr', etc. for other regions
    
    logger.info(f"Searching Vinted ({region.upper()}) for: '{search_term}'")
    
    items = await scrape_vinted(search_term, max_items=30, region=region)
    
    if items:
        result = save_items(items)
        
        logger.info("="*70)
        logger.info(f"✅ Vinted scrape complete!")
        logger.info(f"   Scraped: {len(items)}")
        logger.info(f"   Saved: {result['saved']}")
        logger.info(f"   Failed: {result['failed']}")
        logger.info("="*70)
        print()
        
        # Show samples
        logger.info("Sample items:")
        for item in items[:5]:
            currency_symbol = {'USD': '$', 'EUR': '€', 'GBP': '£'}.get(item.get('currency', 'USD'), '$')
            print(f"  • {item['title'][:50]} - {currency_symbol}{item['price']}")
            if item.get('brand'):
                print(f"    Brand: {item['brand']}")
            if item.get('size'):
                print(f"    Size: {item['size']}")
        
        return len(items)
    else:
        logger.warning("No items scraped from Vinted")
        return 0


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result > 0 else 1)
