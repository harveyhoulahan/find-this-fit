#!/usr/bin/env python3
"""
Vinted API Scraper - Extracts STRUCTURED metadata for ML training.
Uses Vinted's catalog API instead of HTML scraping.
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
from marketplace_maps import VINTED_CATEGORIES, normalize_color, normalize_category

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def scrape_vinted_api(search_term: str, max_items: int = 1000) -> List[Dict[str, Any]]:
    """
    Scrape Vinted using their catalog API with structured metadata.
    
    Vinted provides brand_title and color_title directly - no mapping needed!
    
    Returns items with: brand, category, color, condition, size
    """
    items = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        pages_to_scrape = (max_items // 96) + 1
        
        for page in range(1, pages_to_scrape + 1):
            url = "https://www.vinted.com/api/v2/catalog/items"
            params = {
                'search_text': search_term,
                'page': page,
                'per_page': 96
            }
            
            try:
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status != 200:
                        logger.warning(f"HTTP {resp.status} for page {page}")
                        break
                    
                    data = await resp.json()
                    products = data.get('items', [])
                    
                    if not products:
                        break
                    
                    for product in products:
                        try:
                            # Vinted provides brand_title directly!
                            brand = product.get('brand_title', 'Unknown')
                            
                            # Category from catalog_path or catalog_branch_id
                            catalog_path = product.get('catalog_path', '')
                            category_id = product.get('catalog_branch_id')
                            category = VINTED_CATEGORIES.get(category_id, normalize_category(catalog_path))
                            
                            # Vinted provides color_title directly!
                            color_title = product.get('color_title', '')
                            color = normalize_color(color_title) if color_title else 'unknown'
                            
                            # Size from size_title
                            size = product.get('size_title', 'M')
                            
                            # Condition from status
                            status = product.get('status', 'good')
                            condition_map = {
                                'good': 'Good',
                                'satisfactory': 'Fair',
                                'new_with_tag': 'New',
                                'new_without_tag': 'Like New'
                            }
                            condition = condition_map.get(status, 'Good')
                            
                            # Price
                            price = float(product.get('price', '0'))
                            
                            # Photo URL
                            photo = product.get('photo', {})
                            image_url = photo.get('url', '') if photo else None
                            
                            if not image_url:
                                continue
                            
                            item = {
                                'source': 'vinted',
                                'external_id': str(product['id']),
                                'title': product.get('title', ''),
                                'description': product.get('description', ''),
                                'price': price,
                                'currency': product.get('currency', 'USD'),
                                'url': product.get('url', ''),
                                'image_url': image_url,
                                'seller_name': product.get('user', {}).get('login', ''),
                                
                                # ✅ STRUCTURED METADATA (Vinted provides most as strings!)
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
    """Test Vinted API scraper"""
    logger.info("🚀 Vinted API Scraper - Structured Metadata")
    
    search_terms = ["nike jacket", "black jeans"]
    total_saved = 0
    
    for term in search_terms:
        logger.info(f"\n🔍 Scraping: '{term}'")
        items = await scrape_vinted_api(term, max_items=100)
        
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
