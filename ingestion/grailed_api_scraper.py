#!/usr/bin/env python3
"""
Grailed API Scraper - Extracts STRUCTURED metadata for ML training.
Uses Grailed's API instead of HTML scraping.
"""
import asyncio
import logging
import random
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import aiohttp

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from db import execute_sync
from marketplace_maps import GRAILED_BRANDS, GRAILED_CATEGORY_MAP, normalize_color, normalize_category

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def scrape_grailed_api(search_term: str, max_items: int = 1000) -> List[Dict[str, Any]]:
    """
    Scrape Grailed using their API with structured metadata.
    
    Returns items with: brand, category, color, condition, size
    """
    items = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        pages_to_scrape = (max_items // 40) + 1
        
        for page in range(1, pages_to_scrape + 1):
            url = "https://www.grailed.com/api/listings/search"
            params = {
                'query': search_term,
                'page': page,
                'per_page': 40
            }
            
            try:
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status != 200:
                        logger.warning(f"HTTP {resp.status} for page {page}")
                        break
                    
                    data = await resp.json()
                    listings = data.get('data', [])
                    
                    if not listings:
                        break
                    
                    for listing in listings:
                        try:
                            # Extract brand from designer object
                            designer = listing.get('designer', {})
                            brand = designer.get('name', 'Unknown') if designer else 'Unknown'
                            
                            # Extract category from category path
                            category_data = listing.get('category', {})
                            category_path = tuple(category_data.get('path', [])) if category_data else ()
                            category = GRAILED_CATEGORY_MAP.get(category_path, normalize_category(category_data.get('path_string', 'other')))
                            
                            # Parse color
                            color_raw = listing.get('color', '')
                            color = normalize_color(color_raw) if color_raw else 'unknown'
                            
                            # Get size
                            size = listing.get('size', 'M')
                            
                            # Get condition
                            condition = listing.get('condition', 'Good')
                            
                            # Parse price (format: "$123.00" or "$1,234.00")
                            price_str = listing.get('price', '$0')
                            price = float(price_str.replace('$', '').replace(',', ''))
                            
                            # Get cover photo
                            cover_photo = listing.get('cover_photo', {})
                            image_url = cover_photo.get('url', '') if cover_photo else None
                            
                            if not image_url:
                                continue
                            
                            item = {
                                'source': 'grailed',
                                'external_id': str(listing['id']),
                                'title': listing.get('title', ''),
                                'description': listing.get('description', ''),
                                'price': price,
                                'currency': 'USD',
                                'url': f"https://www.grailed.com/listings/{listing['id']}",
                                'image_url': image_url,
                                'seller_name': listing.get('seller', {}).get('username', ''),
                                
                                # ✅ STRUCTURED METADATA
                                'brand': brand,
                                'category': category,
                                'color': color,
                                'condition': condition,
                                'size': size
                            }
                            
                            items.append(item)
                            
                        except Exception as e:
                            logger.error(f"Error parsing listing: {e}")
                            continue
                    
                    logger.info(f"  Page {page}: {len(listings)} listings ({len(items)} total)")
                    
                    if len(items) >= max_items:
                        break
                    
                    # Rate limiting
                    await asyncio.sleep(random.uniform(1, 2))
                    
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
    
    return items[:max_items]


def save_items(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """Save items to fashion_items table with structured metadata."""
    saved, failed = 0, 0
    
    for item in items:
        try:
            execute_sync(
                """
                INSERT INTO fashion_items 
                (source, external_id, title, description, price, currency, url, image_url, seller_name,
                 brand, category, color, condition, size)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, external_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    price = EXCLUDED.price,
                    brand = EXCLUDED.brand,
                    category = EXCLUDED.category,
                    color = EXCLUDED.color,
                    condition = EXCLUDED.condition,
                    size = EXCLUDED.size,
                    updated_at = NOW();
                """,
                (item['source'], item['external_id'], item['title'], item['description'],
                 item['price'], item['currency'], item['url'], item['image_url'], item['seller_name'],
                 item['brand'], item['category'], item['color'], item['condition'], item['size'])
            )
            saved += 1
        except Exception as e:
            logger.error(f"DB error: {e}")
            failed += 1
    
    return {'saved': saved, 'failed': failed}


async def main():
    """Test Grailed API scraper"""
    logger.info("🚀 Grailed API Scraper - Structured Metadata")
    
    search_terms = ["supreme jacket", "nike sneakers"]
    total_saved = 0
    
    for term in search_terms:
        logger.info(f"\n🔍 Scraping: '{term}'")
        items = await scrape_grailed_api(term, max_items=100)
        
        if items:
            result = save_items(items)
            total_saved += result['saved']
            logger.info(f"✓ Saved {result['saved']}/{len(items)} items")
            
            # Show sample with metadata
            for item in items[:3]:
                logger.info(f"  • {item['brand']} {item['category']} ({item['color']}) - ${item['price']}")
        else:
            logger.warning(f"No items for '{term}'")
    
    logger.info(f"\n✅ Total saved: {total_saved}")
    return total_saved


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result > 0 else 1)
