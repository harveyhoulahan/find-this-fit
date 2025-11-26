#!/usr/bin/env python3
"""
Depop API Scraper - Extracts STRUCTURED metadata for ML training.
Uses Depop's public API instead of HTML scraping.
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
from marketplace_maps import DEPOP_BRANDS, DEPOP_CATEGORIES, normalize_color, normalize_category

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def scrape_depop_api(search_term: str, max_items: int = 1000) -> List[Dict[str, Any]]:
    """
    Scrape Depop using their public API with structured metadata.
    
    Returns items with: brand, category, color, condition, size
    """
    items = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        pages_to_scrape = (max_items // 100) + 1
        
        for page in range(1, pages_to_scrape + 1):
            url = f"https://webapi.depop.com/api/v2/search/?limit=100&page={page}&q={search_term}"
            
            try:
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        logger.warning(f"HTTP {resp.status} for page {page}")
                        break
                    
                    data = await resp.json()
                    products = data.get('products', [])
                    
                    if not products:
                        break
                    
                    for product in products:
                        try:
                            # Extract structured metadata from API response
                            brand_id = product.get('brandId')
                            category_id = product.get('categoryId')
                            
                            # Get picture URL
                            pictures = product.get('pictures', [])
                            image_url = None
                            if pictures:
                                formats = pictures[0].get('formats', {})
                                if 'P6' in formats:
                                    image_url = formats['P6']['url']
                                elif 'P0' in formats:
                                    image_url = formats['P0']['url']
                            
                            if not image_url:
                                continue
                            
                            # Map IDs to names using our mapping tables
                            brand = DEPOP_BRANDS.get(brand_id, 'Unknown')
                            category = DEPOP_CATEGORIES.get(category_id, 'other')
                            
                            # Normalize color
                            color_raw = product.get('colour', '')
                            color = normalize_color(color_raw) if color_raw else 'unknown'
                            
                            # Get size
                            size_data = product.get('size', {})
                            size = size_data.get('text', 'M') if isinstance(size_data, dict) else 'M'
                            
                            # Condition
                            condition = product.get('condition', 'Good')
                            
                            # Price (in cents, convert to dollars)
                            price_amount = product.get('priceAmount', 0)
                            price = price_amount / 100 if price_amount else 0
                            
                            item = {
                                'source': 'depop',
                                'external_id': str(product['id']),
                                'title': product.get('title', ''),
                                'description': product.get('description', ''),
                                'price': price,
                                'currency': product.get('priceCurrency', 'USD'),
                                'url': f"https://depop.com/products/{product.get('slug', '')}",
                                'image_url': image_url,
                                'seller_name': product.get('seller', {}).get('username', ''),
                                
                                # ✅ STRUCTURED METADATA
                                'brand': brand,
                                'category': category,
                                'color': color,
                                'condition': condition,
                                'size': size
                            }
                            
                            items.append(item)
                            
                        except Exception as e:
                            logger.error(f"Error parsing product: {e}")
                            continue
                    
                    logger.info(f"  Page {page}: {len(products)} products ({len(items)} total)")
                    
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
    """Test Depop API scraper"""
    logger.info("🚀 Depop API Scraper - Structured Metadata")
    
    search_terms = ["prada bag", "gucci jacket"]
    total_saved = 0
    
    for term in search_terms:
        logger.info(f"\n🔍 Scraping: '{term}'")
        items = await scrape_depop_api(term, max_items=100)
        
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
