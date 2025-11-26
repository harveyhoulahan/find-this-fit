"""
Production Depop scraper using Playwright for JavaScript rendering.
Handles bot detection, rate limiting, retries, and extracts real product data.

Features:
- Headless browser with stealth mode to bypass bot detection
- Exponential backoff on failures
- Configurable rate limiting and politeness delays
- Screenshot debugging on failures
- Individual product page visits for detailed descriptions
- Comprehensive error handling and logging
- Duplicate detection via database UPSERT

Install: pip install playwright && playwright install chromium
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
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

from db import execute_sync  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SCRAPE_DELAY_MIN = 2.0  # Minimum seconds between requests
SCRAPE_DELAY_MAX = 4.0  # Maximum seconds between requests
MAX_RETRIES = 3  # Number of retry attempts on failure
SCROLL_ITERATIONS = 4  # Number of times to scroll to load more items
REQUEST_TIMEOUT = 30000  # Milliseconds


async def scrape_depop_search(
    search_term: str, 
    max_items: int = 50, 
    fetch_details: bool = False
) -> List[Dict[str, Any]]:
    """
    Scrape Depop search results using Playwright with retry logic.
    
    Args:
        search_term: Search query (e.g., "vintage tee")
        max_items: Maximum number of items to scrape
        fetch_details: Whether to visit individual product pages for full descriptions
        
    Returns:
        List of product dictionaries with keys: external_id, title, description, 
        price, url, image_url
    """
    items = []
    
    for attempt in range(MAX_RETRIES):
        try:
            async with async_playwright() as p:
                # Launch browser with stealth settings to avoid bot detection
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-gpu'
                    ]
                )
                
                # Create context with realistic viewport and user agent
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York'
                )
                
                # Add extra headers to appear more realistic
                await context.set_extra_http_headers({
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                })
                
                page = await context.new_page()
                
                try:
                    # Navigate to search page
                    url = f"https://www.depop.com/search/?q={search_term.replace(' ', '%20')}"
                    logger.info(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Navigating to: {url}")
                    
                    await page.goto(url, wait_until='networkidle', timeout=REQUEST_TIMEOUT)
                    
                    # Wait for product grid to load
                    try:
                        await page.wait_for_selector('[data-testid="product__item"]', timeout=10000)
                    except PlaywrightTimeout:
                        logger.warning("Product grid not found - checking if page is accessible")
                        
                        # Save debug screenshot
                        screenshot_path = f'/tmp/depop_debug_{search_term.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
                        await page.screenshot(path=screenshot_path)
                        logger.info(f"Debug screenshot saved to {screenshot_path}")
                        
                        # Check for common blocking messages
                        page_content = await page.content()
                        if 'captcha' in page_content.lower():
                            logger.error("CAPTCHA detected - cannot proceed")
                        elif 'blocked' in page_content.lower():
                            logger.error("Access blocked - IP may be rate limited")
                        
                        await browser.close()
                        
                        # Retry with exponential backoff
                        if attempt < MAX_RETRIES - 1:
                            backoff = (2 ** attempt) * random.uniform(3, 5)
                            logger.info(f"Retrying in {backoff:.1f} seconds...")
                            await asyncio.sleep(backoff)
                            continue
                        else:
                            return items
                    
                    # Scroll to load more items (Depop uses infinite scroll)
                    logger.info("Scrolling to load more items...")
                    for scroll_num in range(SCROLL_ITERATIONS):
                        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        await asyncio.sleep(random.uniform(1.5, 2.5))
                        logger.debug(f"Scroll {scroll_num + 1}/{SCROLL_ITERATIONS}")
                    
                    # Extract product data
                    products = await page.query_selector_all('[data-testid="product__item"]')
                    logger.info(f"Found {len(products)} products on page")
                    
                    for idx, product in enumerate(products[:max_items]):
                        try:
                            # Extract link
                            link_elem = await product.query_selector('a')
                            if not link_elem:
                                logger.debug(f"Product {idx}: No link found, skipping")
                                continue
                            
                            product_url = await link_elem.get_attribute('href')
                            if not product_url or '/products/' not in product_url:
                                logger.debug(f"Product {idx}: Invalid URL, skipping")
                                continue
                            
                            # Extract ID from URL (last segment)
                            external_id = product_url.strip('/').split('/')[-1]
                            
                            # Extract title
                            title_elem = await product.query_selector('[data-testid="product__title"]')
                            title = (await title_elem.inner_text()).strip() if title_elem else None
                            
                            # Extract price
                            price_elem = await product.query_selector('[data-testid="product__price"]')
                            price_text = await price_elem.inner_text() if price_elem else None
                            price = _parse_price(price_text) if price_text else None
                            
                            # Extract image
                            img_elem = await product.query_selector('img')
                            image_url = await img_elem.get_attribute('src') if img_elem else None
                            
                            # Build full URL
                            full_url = f"https://www.depop.com{product_url}" if product_url.startswith('/') else product_url
                            
                            # Initialize item
                            item = {
                                'external_id': external_id,
                                'title': title,
                                'price': price,
                                'url': full_url,
                                'image_url': image_url,
                                'description': None,
                            }
                            
                            # Optionally fetch detailed description from product page
                            if fetch_details and full_url:
                                description = await _fetch_product_description(page, full_url)
                                item['description'] = description
                            
                            items.append(item)
                            logger.debug(f"✓ Extracted: {title} - ${price}")
                            
                        except Exception as e:
                            logger.error(f"Error extracting product {idx}: {e}")
                            continue
                    
                    logger.info(f"Successfully extracted {len(items)} items for '{search_term}'")
                    
                except Exception as e:
                    logger.error(f"Scraping error on attempt {attempt + 1}: {e}")
                    await browser.close()
                    
                    if attempt < MAX_RETRIES - 1:
                        backoff = (2 ** attempt) * random.uniform(2, 4)
                        logger.info(f"Retrying in {backoff:.1f} seconds...")
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        raise
                
                finally:
                    await browser.close()
            
            # Success - break retry loop
            break
            
        except Exception as e:
            logger.error(f"Fatal error on attempt {attempt + 1}: {e}")
            if attempt == MAX_RETRIES - 1:
                logger.error(f"Failed after {MAX_RETRIES} attempts")
    
    return items


def _parse_price(text: str) -> Optional[float]:
    """
    Extract numeric price from text like '£45.00', '$35', '€30.50'.
    
    Args:
        text: Price string with currency symbol
        
    Returns:
        Float price or None if parsing fails
    """
    if not text:
        return None
    
    # Remove currency symbols and extract digits/decimals
    price_clean = ''.join(c for c in text if c.isdigit() or c == '.')
    
    try:
        return float(price_clean)
    except (ValueError, TypeError):
        logger.warning(f"Failed to parse price: {text}")
        return None


async def _fetch_product_description(page, product_url: str) -> Optional[str]:
    """
    Visit individual product page to extract full description.
    
    Args:
        page: Playwright page object
        product_url: Full URL to product page
        
    Returns:
        Product description or None
    """
    try:
        logger.debug(f"Fetching details from: {product_url}")
        await page.goto(product_url, wait_until='networkidle', timeout=REQUEST_TIMEOUT)
        
        # Wait for description element
        await page.wait_for_selector('[data-testid="product__description"]', timeout=5000)
        
        # Extract description
        desc_elem = await page.query_selector('[data-testid="product__description"]')
        if desc_elem:
            description = await desc_elem.inner_text()
            return description.strip()
        
    except PlaywrightTimeout:
        logger.warning(f"Timeout fetching description from {product_url}")
    except Exception as e:
        logger.error(f"Error fetching description: {e}")
    
    return None



def save_items(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Save scraped items to database with duplicate handling.
    
    Args:
        items: List of product dictionaries
        
    Returns:
        Dictionary with 'saved' and 'failed' counts
    """
    saved = 0
    failed = 0
    
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
                (
                    item.get('external_id'),
                    item.get('title'),
                    item.get('description'),
                    item.get('price'),
                    item.get('url'),
                    item.get('image_url'),
                ),
            )
            saved += 1
            logger.debug(f"✓ Saved: {item.get('external_id')}")
            
        except Exception as e:
            failed += 1
            logger.error(f"✗ Failed to save {item.get('external_id')}: {e}")
    
    return {'saved': saved, 'failed': failed}


async def scrape_multiple_terms(
    search_terms: List[str], 
    items_per_term: int = 50,
    fetch_details: bool = False,
    delay_range: tuple = (SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX)
) -> Dict[str, Any]:
    """
    Scrape multiple search terms with politeness delays and comprehensive reporting.
    
    Args:
        search_terms: List of search queries
        items_per_term: Max items to scrape per term
        fetch_details: Whether to fetch full product descriptions
        delay_range: (min, max) seconds to wait between search terms
        
    Returns:
        Summary dictionary with statistics
    """
    start_time = datetime.now()
    results = {
        'total_terms': len(search_terms),
        'successful_terms': 0,
        'total_items_found': 0,
        'total_items_saved': 0,
        'total_items_failed': 0,
        'search_terms': {},
        'start_time': start_time.isoformat(),
    }
    
    for idx, term in enumerate(search_terms, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Scraping term {idx}/{len(search_terms)}: '{term}'")
        logger.info(f"{'='*60}")
        
        try:
            # Scrape items
            items = await scrape_depop_search(
                search_term=term,
                max_items=items_per_term,
                fetch_details=fetch_details
            )
            
            if items:
                # Save to database
                save_result = save_items(items)
                
                results['total_items_found'] += len(items)
                results['total_items_saved'] += save_result['saved']
                results['total_items_failed'] += save_result['failed']
                results['successful_terms'] += 1
                
                results['search_terms'][term] = {
                    'items_found': len(items),
                    'items_saved': save_result['saved'],
                    'items_failed': save_result['failed'],
                    'success': True
                }
                
                logger.info(f"✓ Completed '{term}': {save_result['saved']}/{len(items)} items saved")
            else:
                logger.warning(f"⚠ No items found for '{term}'")
                results['search_terms'][term] = {
                    'items_found': 0,
                    'items_saved': 0,
                    'items_failed': 0,
                    'success': False
                }
            
        except Exception as e:
            logger.error(f"✗ Failed to scrape '{term}': {e}")
            results['search_terms'][term] = {
                'error': str(e),
                'success': False
            }
        
        # Polite delay between search terms (except after last one)
        if idx < len(search_terms):
            delay = random.uniform(*delay_range)
            logger.info(f"Waiting {delay:.1f}s before next search term...\n")
            await asyncio.sleep(delay)
    
    # Calculate final statistics
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    results['end_time'] = end_time.isoformat()
    results['duration_seconds'] = duration
    results['success_rate'] = (results['successful_terms'] / results['total_terms'] * 100) if results['total_terms'] > 0 else 0
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SCRAPING SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Duration: {duration:.1f}s")
    logger.info(f"Search terms: {results['successful_terms']}/{results['total_terms']} successful ({results['success_rate']:.1f}%)")
    logger.info(f"Items found: {results['total_items_found']}")
    logger.info(f"Items saved: {results['total_items_saved']}")
    logger.info(f"Items failed: {results['total_items_failed']}")
    logger.info(f"{'='*60}\n")
    
    return results


async def main():
    """
    Main scraping workflow with production-ready search terms.
    """
    # Curated search terms for fashion items
    search_terms = [
        "vintage tee",
        "denim jacket",
        "y2k dress",
        "vintage hoodie",
        "streetwear pants",
        "retro sneakers",
        "cargo pants",
        "graphic tee",
        "oversized hoodie",
        "vintage jeans"
    ]
    
    logger.info("🚀 Starting Depop scraping session...")
    logger.info(f"Search terms: {', '.join(search_terms)}")
    logger.info(f"Config: {MAX_RETRIES} retries, {SCROLL_ITERATIONS} scroll iterations")
    
    results = await scrape_multiple_terms(
        search_terms=search_terms,
        items_per_term=50,
        fetch_details=False,  # Set to True to get full descriptions (slower)
        delay_range=(SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX)
    )
    
    logger.info("🎉 Scraping session complete!")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())

