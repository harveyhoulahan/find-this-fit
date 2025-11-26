# 🌙 Overnight Mass Scraper

## Overview

The overnight mass scraper is a comprehensive data collection tool that replaces all existing fashion items in your database with fresh, high-quality data from Depop, Grailed, and Vinted.

## Features

- **Automatic Database Backup**: Creates timestamped backup before clearing data
- **Large-Scale Scraping**: Targets ~50,000+ items across 3 platforms
- **Structured Metadata**: All items include brand, category, color, condition, size
- **Comprehensive Coverage**: 150+ search terms across all major fashion categories
- **Smart Rate Limiting**: Avoids API bans with intelligent delays
- **Detailed Logging**: Full progress logs for monitoring and debugging

## What Gets Scraped

### Categories Covered (150+ search terms)

1. **Luxury Brands** (500 items/search)
   - Gucci, Prada, Louis Vuitton, Chanel, Dior, Balenciaga, Saint Laurent, etc.

2. **Streetwear** (400 items/search)
   - Supreme, Palace, BAPE, Stussy, Off-White, Fear of God, etc.

3. **Sportswear** (400 items/search)
   - Nike, Adidas, Jordan, Yeezy, New Balance, Puma, etc.

4. **Designer/Contemporary** (300 items/search)
   - Acne Studios, AMI Paris, Rick Owens, Comme des Garçons, etc.

5. **Outdoor/Technical** (200 items/search)
   - Patagonia, The North Face, Arc'teryx, Carhartt, etc.

6. **Denim** (300 items/search)
   - Levi's, Wrangler, vintage jeans, distressed, skinny, straight, etc.

7. **Tops** (200 items/search)
   - T-shirts, shirts, sweaters, hoodies, cardigans, etc.

8. **Outerwear** (300 items/search)
   - Jackets, coats, parkas, bombers, leather, denim, etc.

9. **Bottoms** (200 items/search)
   - Pants, shorts, cargo, track, sweatpants, chinos, etc.

10. **Footwear** (300 items/search)
    - Sneakers, boots, loafers, sandals, Doc Martens, Converse, Vans, etc.

11. **Accessories** (200 items/search)
    - Bags, wallets, hats, scarves, sunglasses, watches, jewelry, etc.

12. **Color-Specific** (100 items/search)
    - Black jacket, white sneakers, navy sweater, grey hoodie, etc.

13. **Style-Specific** (100 items/search)
    - Vintage, retro, Y2K, 90s, oversized, minimalist, etc.

## Expected Results

- **Total Items**: ~50,000-60,000 items
- **Platforms**: Depop, Grailed, Vinted (equal distribution)
- **Brands**: 500+ unique brands
- **Categories**: 30+ categories
- **Colors**: 20+ color variations
- **Duration**: 8-12 hours

## Usage

### Quick Start

```bash
cd ingestion
./RUN_OVERNIGHT_SCRAPE.sh
```

### Manual Run

```bash
cd ingestion
python3 overnight_mass_scrape.py
```

### Monitor Progress

```bash
# Watch live progress
tail -f ingestion/overnight_scrape_*.log

# Check database stats (in another terminal)
docker exec -i findthisfit-db psql -U postgres -d find_this_fit -c "SELECT source, COUNT(*) FROM fashion_items GROUP BY source;"
```

## What Happens

1. **Backup Phase** (1-2 minutes)
   - Creates SQL backup of current `fashion_items` table
   - Saved to `ingestion/backups/fashion_items_backup_TIMESTAMP.sql`

2. **Clear Phase** (1 minute)
   - Deletes all existing items
   - Resets ID sequence

3. **Scraping Phase** (8-12 hours)
   - Scrapes Depop API (3-4 hours)
   - Scrapes Grailed API (3-4 hours)
   - Scrapes Vinted API (3-4 hours)
   - Each platform gets all 150+ search terms

4. **Summary Phase** (1 minute)
   - Shows statistics by platform
   - Shows total brands, categories, colors
   - Lists next steps

## Output Files

```
ingestion/
├── overnight_scrape_20250126_220000.log   # Full log file
└── backups/
    └── fashion_items_backup_20250126_220000.sql  # Database backup
```

## After Scraping

Once scraping completes, you need to generate embeddings:

```bash
cd ingestion
python3 embed_items.py all
```

This will:
- Generate CLIP embeddings for all images
- Take 4-6 hours for 50,000 items
- Required for visual search functionality

## Database Schema

All items are saved with:

```sql
CREATE TABLE fashion_items (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50),           -- 'depop', 'grailed', 'vinted'
    external_id TEXT,             -- Platform's item ID
    title TEXT,
    description TEXT,
    price NUMERIC(10, 2),
    currency VARCHAR(3),
    url TEXT,
    image_url TEXT,
    seller_name TEXT,
    
    -- Structured Metadata (NEW!)
    brand VARCHAR(100),           -- 'Nike', 'Supreme', 'Gucci'
    category VARCHAR(50),         -- 'sneakers', 'jacket', 't-shirt'
    color VARCHAR(50),            -- 'black', 'white', 'navy'
    condition VARCHAR(50),        -- 'New', 'Like New', 'Good'
    size VARCHAR(20),             -- 'M', 'L', '10', '32'
    
    embedding vector(768),        -- CLIP embedding (added later)
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Customization

### Adjust Items Per Category

Edit `ITEMS_PER_SEARCH` in `overnight_mass_scrape.py`:

```python
ITEMS_PER_SEARCH = {
    "luxury": 1000,      # Increase luxury items
    "streetwear": 200,   # Decrease streetwear
    # ...
}
```

### Add Custom Search Terms

Edit `SEARCH_TERMS` dict:

```python
SEARCH_TERMS = {
    # ...
    "custom_category": [
        "search term 1",
        "search term 2",
    ]
}
```

### Change Target Platforms

Comment out platforms in `main()`:

```python
for platform in ["depop", "grailed"]:  # Skip vinted
    result = await scrape_platform(platform, ...)
```

## Safety Features

- **Automatic Backup**: Never lose your existing data
- **Rate Limiting**: Smart delays prevent API bans
- **Error Handling**: Continues on individual item failures
- **Duplicate Protection**: `ON CONFLICT` updates existing items
- **Progress Logging**: Monitor every step

## Troubleshooting

### Database Connection Failed

```bash
# Check if Docker is running
docker ps | grep findthisfit-db

# If not, start it
cd /Users/harveyhoulahan/Desktop/MiniApp/find-this-fit
docker-compose up -d
```

### Script Interrupted

The backup is safe! To restore:

```bash
docker exec -i findthisfit-db psql -U postgres -d find_this_fit < ingestion/backups/fashion_items_backup_TIMESTAMP.sql
```

### Low Item Count

Some search terms may return fewer items than expected. This is normal - the APIs may have limited results for niche searches.

### API Rate Limiting

If you see many 429 errors, the script has built-in rate limiting. It will automatically slow down and retry.

## Performance Tips

1. **Run overnight**: This script is designed for long-running execution
2. **Use stable internet**: Wireless connections may drop
3. **Keep laptop plugged in**: Prevent sleep mode
4. **Monitor initially**: Watch first 30 minutes to ensure it's working
5. **Check logs periodically**: Use `tail -f` to monitor progress

## Next Steps After Completion

1. **Review Log File**: Check for any errors or warnings
2. **Generate Embeddings**: `python3 embed_items.py all`
3. **Test Search API**: Try some visual searches in your app
4. **Check Data Quality**: Query database for brand/category distribution
5. **Celebrate** 🎉: You now have a massive, high-quality dataset!

## Statistics to Monitor

```sql
-- Total items by platform
SELECT source, COUNT(*) as total
FROM fashion_items
GROUP BY source;

-- Top brands
SELECT brand, COUNT(*) as count
FROM fashion_items
GROUP BY brand
ORDER BY count DESC
LIMIT 20;

-- Category distribution
SELECT category, COUNT(*) as count
FROM fashion_items
GROUP BY category
ORDER BY count DESC;

-- Color distribution
SELECT color, COUNT(*) as count
FROM fashion_items
GROUP BY color
ORDER BY count DESC;

-- Items needing embeddings
SELECT COUNT(*) as need_embedding
FROM fashion_items
WHERE embedding IS NULL;
```

## Support

If you encounter issues:

1. Check the log file for specific errors
2. Verify database is running: `docker ps`
3. Test individual scrapers: `python3 depop_api_scraper.py`
4. Check network connection
5. Review rate limiting settings

Happy scraping! 🌙✨
