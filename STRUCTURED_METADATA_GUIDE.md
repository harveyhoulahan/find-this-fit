# Structured Metadata Implementation Guide

## Problem Statement

The Modaics ML models are performing poorly because training data has incorrect labels:
- **58.7% labeled "unknown" color** (should be blue, black, red, etc.)
- **32.5% labeled "other" category** (should be jacket, shirt, pants, etc.)  
- **Root cause**: Scraper only captures unstructured `title` fields, relying on keyword matching

## Solution

Extract **structured metadata from marketplace APIs** instead of parsing titles.

---

## Implementation Status

### ✅ Completed

1. **Created mapping tables** (`ingestion/marketplace_maps.py`)
   - Depop: brand_id → name, category_id → category, color_id → color
   - Grailed: designer_id → name, category paths → standardized categories
   - Vinted: catalog_branch_id → category, uses provided brand_title/color_title
   - Normalization functions for fuzzy matching

2. **Updated database schema** (`database/add_structured_metadata.sql`)
   - Added columns: `color`, `condition`, `size`
   - Created indexes for filtering
   - Added data quality constraints
   - Statistics queries to monitor data quality

### 🔄 In Progress

3. **Update scrapers to extract structured data**
   - Need to modify: `depop_scraper_working.py`, `grailed_scraper.py`, `vinted_scraper.py`
   - Extract from API responses instead of HTML parsing
   - Map IDs to standardized names using `marketplace_maps.py`

---

## Next Steps

### Step 1: Switch from HTML scraping to API scraping

Current scrapers use Playwright to parse HTML. This is fragile and doesn't give us structured data.

**Better approach**: Use marketplace APIs directly.

#### Depop API

```python
import aiohttp

async def scrape_depop_api(search_term: str, max_items: int = 1000):
    """Scrape Depop using their public API"""
    items = []
    
    async with aiohttp.ClientSession() as session:
        for page in range(1, (max_items // 100) + 1):
            url = f"https://webapi.depop.com/api/v2/search/?limit=100&page={page}&q={search_term}"
            
            async with session.get(url) as resp:
                if resp.status != 200:
                    break
                
                data = await resp.json()
                
                for product in data.get('products', []):
                    # ✅ STRUCTURED DATA DIRECTLY FROM API
                    item = {
                        'source': 'depop',
                        'external_id': str(product['id']),
                        'title': product['title'],
                        'description': product.get('description', ''),
                        'price': product['priceAmount'] / 100,  # Convert cents to dollars
                        'currency': product['priceCurrency'],
                        'url': f"https://depop.com/products/{product['slug']}",
                        'image_url': product['pictures'][0]['formats']['P6']['url'] if product.get('pictures') else None,
                        'seller_name': product['seller']['username'],
                        
                        # STRUCTURED METADATA
                        'brand': DEPOP_BRANDS.get(product.get('brandId'), 'Unknown'),
                        'category': DEPOP_CATEGORIES.get(product.get('categoryId'), 'other'),
                        'color': normalize_color(product.get('colour', '')),
                        'condition': product.get('condition', 'Good'),
                        'size': product.get('size', {}).get('text', 'M') if product.get('size') else 'M'
                    }
                    items.append(item)
            
            await asyncio.sleep(1)  # Rate limiting
    
    return items
```

#### Grailed API

```python
async def scrape_grailed_api(search_term: str, max_items: int = 1000):
    """Scrape Grailed using their GraphQL API"""
    items = []
    
    async with aiohttp.ClientSession() as session:
        # Grailed uses GraphQL
        url = "https://www.grailed.com/api/listings/search"
        
        for page in range(1, (max_items // 40) + 1):
            params = {
                'query': search_term,
                'page': page,
                'per_page': 40
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    break
                
                data = await resp.json()
                
                for listing in data.get('data', []):
                    # Extract category path
                    category_path = tuple(listing.get('category', {}).get('path', []))
                    category = GRAILED_CATEGORY_MAP.get(category_path, 'other')
                    
                    item = {
                        'source': 'grailed',
                        'external_id': str(listing['id']),
                        'title': listing['title'],
                        'description': listing.get('description', ''),
                        'price': float(listing['price'].replace('$', '').replace(',', '')),
                        'currency': 'USD',
                        'url': f"https://www.grailed.com/listings/{listing['id']}",
                        'image_url': listing['cover_photo']['url'],
                        'seller_name': listing['seller']['username'],
                        
                        # STRUCTURED METADATA
                        'brand': listing.get('designer', {}).get('name', 'Unknown'),
                        'category': category,
                        'color': normalize_color(listing.get('color', '')),
                        'condition': listing.get('condition', 'Good'),
                        'size': listing.get('size', 'M')
                    }
                    items.append(item)
            
            await asyncio.sleep(1)
    
    return items
```

#### Vinted API

```python
async def scrape_vinted_api(search_term: str, max_items: int = 1000):
    """Scrape Vinted using their catalog API"""
    items = []
    
    async with aiohttp.ClientSession() as session:
        for page in range(1, (max_items // 96) + 1):
            url = "https://www.vinted.com/api/v2/catalog/items"
            params = {
                'search_text': search_term,
                'page': page,
                'per_page': 96
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    break
                
                data = await resp.json()
                
                for product in data.get('items', []):
                    item = {
                        'source': 'vinted',
                        'external_id': str(product['id']),
                        'title': product['title'],
                        'description': product.get('description', ''),
                        'price': float(product['price']),
                        'currency': product['currency'],
                        'url': product['url'],
                        'image_url': product['photo']['url'],
                        'seller_name': product['user']['login'],
                        
                        # STRUCTURED METADATA (Vinted provides these as text!)
                        'brand': product.get('brand_title', 'Unknown'),  # Already a string!
                        'category': normalize_category(product.get('catalog_path', 'other')),
                        'color': normalize_color(product.get('color_title', '')),  # Already a string!
                        'condition': product.get('status', 'Good'),
                        'size': product.get('size_title', 'M')
                    }
                    items.append(item)
            
            await asyncio.sleep(1)
    
    return items
```

### Step 2: Create unified scraper

```python
# ingestion/scrape_structured.py
from marketplace_maps import *
import asyncio

async def scrape_all_structured(search_terms: List[str], items_per_platform: int = 1000):
    """
    Scrape all marketplaces with structured metadata.
    This replaces the old HTML scraping approach.
    """
    all_items = []
    
    for term in search_terms:
        logger.info(f"Scraping: {term}")
        
        # Scrape all platforms in parallel
        depop_items, grailed_items, vinted_items = await asyncio.gather(
            scrape_depop_api(term, items_per_platform),
            scrape_grailed_api(term, items_per_platform),
            scrape_vinted_api(term, items_per_platform)
        )
        
        all_items.extend(depop_items + grailed_items + vinted_items)
        
        # Save to database
        for item in depop_items + grailed_items + vinted_items:
            execute_sync("""
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
            """, (
                item['source'], item['external_id'], item['title'], item['description'],
                item['price'], item['currency'], item['url'], item['image_url'], item['seller_name'],
                item['brand'], item['category'], item['color'], item['condition'], item['size']
            ))
        
        logger.info(f"✓ Saved {len(depop_items + grailed_items + vinted_items)} items for '{term}'")
        await asyncio.sleep(3)
    
    return all_items
```

### Step 3: Verify data quality

```bash
# Run this after scraping
docker exec -i findthisfit-db psql -U postgres -d find_this_fit << 'EOF'
SELECT 
    source,
    COUNT(*) as total,
    COUNT(CASE WHEN brand != 'Unknown' THEN 1 END) as with_brand,
    COUNT(CASE WHEN category != 'other' THEN 1 END) as with_category,
    COUNT(CASE WHEN color != 'unknown' THEN 1 END) as with_color,
    ROUND(100.0 * COUNT(CASE WHEN brand != 'Unknown' THEN 1 END) / COUNT(*), 1) as brand_pct,
    ROUND(100.0 * COUNT(CASE WHEN category != 'other' THEN 1 END) / COUNT(*), 1) as category_pct,
    ROUND(100.0 * COUNT(CASE WHEN color != 'unknown' THEN 1 END) / COUNT(*), 1) as color_pct
FROM fashion_items
GROUP BY source
ORDER BY total DESC;
EOF
```

**Target metrics:**
- `brand_pct >= 90%` (90%+ items should have known brand)
- `category_pct >= 95%` (95%+ should have category)
- `color_pct >= 85%` (85%+ should have color)

### Step 4: Export ML training data

```python
# ingestion/export_ml_training_data.py
"""
Export images organized by label for ML training.
Uses STRUCTURED metadata, not title parsing!
"""
import os
import asyncio
import aiohttp
from pathlib import Path
from db import fetch_all_sync

async def download_image(session, url, path):
    """Download image to path"""
    async with session.get(url, timeout=10) as resp:
        if resp.status == 200:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                f.write(await resp.read())
            return True
    return False

async def export_color_classifier_data(output_dir: str = "ml_data/color_classifier"):
    """Export images for color classification training"""
    
    # Get all items with known colors
    items = fetch_all_sync("""
        SELECT id, image_url, color, source, external_id
        FROM fashion_items
        WHERE color != 'unknown' 
          AND color IS NOT NULL
          AND image_url IS NOT NULL
        ORDER BY color, RANDOM()
        LIMIT 50000;
    """)
    
    logger.info(f"Exporting {len(items)} items for color classifier")
    
    async with aiohttp.ClientSession() as session:
        for item in items:
            color_dir = Path(output_dir) / item['color']
            filename = f"{item['source']}_{item['external_id']}.jpg"
            filepath = color_dir / filename
            
            if await download_image(session, item['image_url'], filepath):
                logger.info(f"✓ {item['color']}/{filename}")
    
    # Show distribution
    color_counts = {}
    for item in items:
        color_counts[item['color']] = color_counts.get(item['color'], 0) + 1
    
    logger.info("\n Color distribution:")
    for color, count in sorted(color_counts.items(), key=lambda x: -x[1]):
        logger.info(f"  {color}: {count} images")

async def export_category_classifier_data(output_dir: str = "ml_data/category_classifier"):
    """Export images for category classification training"""
    
    items = fetch_all_sync("""
        SELECT id, image_url, category, source, external_id
        FROM fashion_items
        WHERE category != 'other' 
          AND category IS NOT NULL
          AND image_url IS NOT NULL
        ORDER BY category, RANDOM()
        LIMIT 50000;
    """)
    
    logger.info(f"Exporting {len(items)} items for category classifier")
    
    async with aiohttp.ClientSession() as session:
        for item in items:
            category_dir = Path(output_dir) / item['category']
            filename = f"{item['source']}_{item['external_id']}.jpg"
            filepath = category_dir / filename
            
            if await download_image(session, item['image_url'], filepath):
                logger.info(f"✓ {item['category']}/{filename}")

# Run both exports
asyncio.run(export_color_classifier_data())
asyncio.run(export_category_classifier_data())
```

---

## Expected Results

### Before (Current State)
```
Database quality:
- Items with brand: 0%
- Items with category: 0% 
- Items with color: 0%

ML training data (after title parsing):
- Unknown colors: 58.7%
- Other categories: 32.5%

Model performance:
- Color accuracy: 92.7% (predicting "unknown")
- Category accuracy: 41.8%
```

### After (With Structured Data)
```
Database quality:
- Items with brand: 92%+
- Items with category: 98%+
- Items with color: 89%+

ML training data:
- Unknown colors: <12%
- Other categories: <3%

Model performance:
- Color accuracy: 85-90%
- Category accuracy: 88-93%
- Brand accuracy: 99.6%
```

---

## Implementation Checklist

- [x] Create marketplace_maps.py with ID mappings
- [x] Update database schema (add color, condition, size columns)
- [ ] Switch Depop scraper from HTML → API
- [ ] Switch Grailed scraper from HTML → API  
- [ ] Switch Vinted scraper from HTML → API
- [ ] Create unified scrape_structured.py
- [ ] Run large scrape (target 100k+ items)
- [ ] Verify data quality (>90% brand, >95% category, >85% color)
- [ ] Create export_ml_training_data.py
- [ ] Export training data using structured fields
- [ ] Retrain ML models
- [ ] Validate model accuracy improvements

---

## Files Created

1. `ingestion/marketplace_maps.py` - Brand/category/color ID mappings
2. `database/add_structured_metadata.sql` - Schema migration
3. This guide - `STRUCTURED_METADATA_GUIDE.md`

## Files To Update

1. `ingestion/depop_scraper_working.py` → Switch to API scraping
2. `ingestion/grailed_scraper.py` → Switch to API scraping
3. `ingestion/vinted_scraper.py` → Switch to API scraping
4. Create `ingestion/scrape_structured.py` - Unified API scraper
5. Create `ingestion/export_ml_training_data.py` - Training data export
