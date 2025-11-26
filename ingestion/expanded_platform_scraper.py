"""
Expanded Multi-Platform Scraper for Modaics
Adds 10+ new resale platforms to increase inventory diversity
"""

import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

# Platform configurations
PLATFORMS = {
    "vestiaire": {
        "base_url": "https://www.vestiairecollective.com",
        "search_path": "/search/?q=",
        "selectors": {
            "item_card": ".productSnippet",
            "title": ".productSnippet__name",
            "price": ".productSnippet__price",
            "image": ".productSnippet__image img",
            "link": ".productSnippet__link",
            "brand": ".productSnippet__brand",
            "condition": ".productSnippet__condition"
        },
        "authenticated": True,  # Requires auth to see prices
        "priority": 1
    },
    
    "therealreal": {
        "base_url": "https://www.therealreal.com",
        "search_path": "/search?keywords=",
        "selectors": {
            "item_card": ".product-tile",
            "title": ".product-tile__title",
            "price": ".product-tile__price",
            "image": ".product-tile__image img",
            "link": "a.product-tile__link",
            "brand": ".product-tile__brand",
            "condition": ".product-tile__condition"
        },
        "authenticated": False,
        "priority": 1
    },
    
    "poshmark": {
        "base_url": "https://poshmark.com",
        "search_path": "/search?query=",
        "selectors": {
            "item_card": ".tile",
            "title": ".tile__title",
            "price": ".tile__price",
            "image": ".tile__covershot img",
            "link": "a.tile__link",
            "brand": ".tile__brand",
            "size": ".tile__size"
        },
        "authenticated": False,
        "priority": 1
    },
    
    "thredup": {
        "base_url": "https://www.thredup.com",
        "search_path": "/search?search_term=",
        "selectors": {
            "item_card": "[data-testid='product-card']",
            "title": "[data-testid='product-title']",
            "price": "[data-testid='product-price']",
            "image": "[data-testid='product-image'] img",
            "link": "[data-testid='product-link']",
            "brand": "[data-testid='product-brand']",
            "condition": "[data-testid='product-condition']"
        },
        "authenticated": False,
        "priority": 1
    },
    
    "stockx": {
        "base_url": "https://stockx.com",
        "search_path": "/search?s=",
        "selectors": {
            "item_card": ".ProductTile",
            "title": ".ProductTile__title",
            "price": ".ProductTile__price",
            "image": ".ProductTile__image img",
            "link": "a.ProductTile",
            "brand": ".ProductTile__brand",
            "colorway": ".ProductTile__subtitle"
        },
        "authenticated": False,
        "priority": 2
    },
    
    "rebag": {
        "base_url": "https://www.rebag.com",
        "search_path": "/search?q=",
        "selectors": {
            "item_card": ".product-card",
            "title": ".product-card__name",
            "price": ".product-card__price",
            "image": ".product-card__image img",
            "link": ".product-card__link",
            "brand": ".product-card__brand",
            "condition": ".product-card__condition-badge"
        },
        "authenticated": False,
        "priority": 2
    },
    
    "goat": {
        "base_url": "https://www.goat.com",
        "search_path": "/search?query=",
        "selectors": {
            "item_card": "[data-qa='product-card']",
            "title": "[data-qa='product-name']",
            "price": "[data-qa='product-price']",
            "image": "[data-qa='product-image'] img",
            "link": "[data-qa='product-link']",
            "brand": "[data-qa='product-brand']",
            "size": "[data-qa='product-size']"
        },
        "authenticated": False,
        "priority": 2
    },
    
    "farfetch_preowned": {
        "base_url": "https://www.farfetch.com",
        "search_path": "/shopping/women/pre-owned/items.aspx?q=",
        "selectors": {
            "item_card": "[data-testid='productCard']",
            "title": "[data-testid='productCardDescription']",
            "price": "[data-testid='price']",
            "image": "[data-testid='productCardImage'] img",
            "link": "a[data-testid='productCardLink']",
            "brand": "[data-testid='productCardBrand']"
        },
        "authenticated": False,
        "priority": 2
    },
    
    "1stdibs": {
        "base_url": "https://www.1stdibs.com",
        "search_path": "/search/?q=",
        "selectors": {
            "item_card": ".product-card",
            "title": ".product-card__title",
            "price": ".product-card__price",
            "image": ".product-card__image img",
            "link": "a.product-card__link",
            "dealer": ".product-card__dealer",
            "period": ".product-card__period"
        },
        "authenticated": False,
        "priority": 3
    },
    
    "etsy_vintage": {
        "base_url": "https://www.etsy.com",
        "search_path": "/search?q=",
        "extra_params": "&explicit=1&category=vintage&subcategory=clothing",
        "selectors": {
            "item_card": "[data-search-results-item]",
            "title": "h3.v2-listing-card__title",
            "price": ".currency-value",
            "image": ".listing-link img",
            "link": "a.listing-link",
            "shop": ".v2-listing-card__shop"
        },
        "authenticated": False,
        "priority": 3
    }
}

# Luxury brand search terms (same as luxury_brand_scrape.py)
LUXURY_SEARCHES = [
    # Designer Brands
    "Prada", "Gucci", "Miu Miu", "Louis Vuitton", "Hermès", "Chanel",
    "Dior", "Saint Laurent", "Balenciaga", "Bottega Veneta", "Loewe",
    
    # Streetwear/Contemporary
    "Rick Owens", "Comme des Garçons", "Yohji Yamamoto", "Acne Studios",
    "Maison Margiela", "Off-White", "Fear of God", "Stone Island",
    
    # Sneakers/Sportswear
    "Nike Dunk", "Air Jordan", "Yeezy", "New Balance 550", "Salomon",
    
    # Vintage/Archive
    "Vintage Prada Sport", "Archive Helmut Lang", "Vintage Jean Paul Gaultier"
]


async def scrape_platform(platform_name: str, search_term: str, max_items: int = 50):
    """Scrape a single platform for a search term"""
    config = PLATFORMS[platform_name]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Build search URL
        search_url = f"{config['base_url']}{config['search_path']}{search_term}"
        if 'extra_params' in config:
            search_url += config['extra_params']
        
        print(f"🔍 Scraping {platform_name}: {search_term}")
        
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)  # Let dynamic content load
            
            # Scroll to load lazy images
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await page.wait_for_timeout(500)
            
            # Extract items
            items = []
            item_cards = await page.query_selector_all(config['selectors']['item_card'])
            
            for card in item_cards[:max_items]:
                try:
                    item = {
                        'platform': platform_name,
                        'search_term': search_term,
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    # Extract each field
                    for field, selector in config['selectors'].items():
                        if field == 'item_card':
                            continue
                        
                        element = await card.query_selector(selector)
                        if element:
                            if field == 'image':
                                item['image_url'] = await element.get_attribute('src')
                            elif field == 'link':
                                href = await element.get_attribute('href')
                                # Make absolute URL
                                if href and not href.startswith('http'):
                                    item['item_url'] = f"{config['base_url']}{href}"
                                else:
                                    item['item_url'] = href
                            else:
                                item[field] = await element.inner_text()
                    
                    # Parse price to numeric
                    if 'price' in item:
                        price_text = item['price'].replace('$', '').replace(',', '').split()[0]
                        try:
                            item['price_numeric'] = float(price_text)
                        except:
                            item['price_numeric'] = None
                    
                    items.append(item)
                    
                except Exception as e:
                    print(f"  ⚠️ Error extracting item: {e}")
                    continue
            
            print(f"  ✅ Found {len(items)} items from {platform_name}")
            await browser.close()
            return items
            
        except Exception as e:
            print(f"  ❌ Error scraping {platform_name}: {e}")
            await browser.close()
            return []


async def scrape_all_platforms(search_terms: list, platforms_to_scrape: list, items_per_search: int = 50):
    """Scrape multiple platforms in parallel"""
    all_items = []
    
    for search_term in search_terms:
        print(f"\n{'='*60}")
        print(f"🔎 Searching for: {search_term}")
        print(f"{'='*60}")
        
        # Scrape all platforms for this search term
        tasks = [
            scrape_platform(platform, search_term, items_per_search)
            for platform in platforms_to_scrape
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)
        
        # Small delay between search terms
        await asyncio.sleep(2)
    
    return all_items


async def save_to_database(items: list):
    """Save scraped items to PostgreSQL (same DB as FindThisFit)"""
    import psycopg2
    from psycopg2.extras import execute_batch
    
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="find_this_fit",
        user="postgres",
        password="postgres"
    )
    
    cursor = conn.cursor()
    
    # Insert items
    insert_query = """
        INSERT INTO fashion_items 
        (title, price, image_url, item_url, platform, brand, size, condition, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (item_url) DO NOTHING
    """
    
    data = [
        (
            item.get('title', ''),
            item.get('price_numeric'),
            item.get('image_url', ''),
            item.get('item_url', ''),
            item.get('platform', ''),
            item.get('brand', ''),
            item.get('size', ''),
            item.get('condition', '')
        )
        for item in items
        if item.get('item_url')  # Only insert if we have a URL
    ]
    
    execute_batch(cursor, insert_query, data, page_size=100)
    conn.commit()
    
    print(f"\n✅ Inserted {len(data)} items into database")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    # Configuration
    PLATFORMS_TO_SCRAPE = [
        "poshmark",        # Priority 1: Huge inventory
        "thredup",         # Priority 1: Sustainability focus
        "therealreal",     # Priority 1: Luxury authentication
        "vestiaire",       # Priority 1: High-end (may need auth)
        "stockx",          # Priority 2: Streetwear/sneakers
    ]
    
    # Use subset of luxury searches for testing
    SEARCH_TERMS = LUXURY_SEARCHES[:10]  # Start with 10 brands
    
    ITEMS_PER_PLATFORM = 30
    
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║     EXPANDED MULTI-PLATFORM SCRAPER FOR MODAICS         ║
    ╚══════════════════════════════════════════════════════════╝
    
    Platforms: {', '.join(PLATFORMS_TO_SCRAPE)}
    Search Terms: {len(SEARCH_TERMS)}
    Items per search per platform: {ITEMS_PER_PLATFORM}
    Expected total: ~{len(SEARCH_TERMS) * len(PLATFORMS_TO_SCRAPE) * ITEMS_PER_PLATFORM:,}
    
    Starting scrape...
    """)
    
    # Run scraper
    items = asyncio.run(
        scrape_all_platforms(SEARCH_TERMS, PLATFORMS_TO_SCRAPE, ITEMS_PER_PLATFORM)
    )
    
    print(f"\n{'='*60}")
    print(f"📊 SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"Total items scraped: {len(items):,}")
    
    # Platform breakdown
    platform_counts = {}
    for item in items:
        platform = item.get('platform', 'unknown')
        platform_counts[platform] = platform_counts.get(platform, 0) + 1
    
    print("\nBreakdown by platform:")
    for platform, count in sorted(platform_counts.items(), key=lambda x: -x[1]):
        print(f"  {platform}: {count:,} items")
    
    # Save to database
    print(f"\n💾 Saving to database...")
    asyncio.run(save_to_database(items))
    
    # Save JSON backup
    output_file = f"expanded_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(items, f, indent=2)
    print(f"📄 Backup saved to {output_file}")
