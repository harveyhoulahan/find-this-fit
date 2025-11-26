# Depop Scraping Guide

## Quick Reference

### 1. **Quick Test** (40-100 items, ~2 minutes)
```bash
python3 depop_scraper_working.py
```

### 2. **Full Scrape** (500-800 items, ~8 minutes)
```bash
python3 full_scrape.py
# or
python3 full_scrape.py quick    # 30 items/category
python3 full_scrape.py medium   # 100 items/category
python3 full_scrape.py large    # 500 items/category
```

### 3. **Unlimited Single Category** (100s-1000s items)
```bash
python3 depop_scraper_unlimited.py
# Interactive prompts:
#  - Search term: "vintage hoodie"
#  - Max items: 500 (or 0 for unlimited)
#  - Max scrolls: 50 (~1200 items)
```

### 4. **Massive Production Scrape** (5000+ items, ~2-4 hours)
```bash
python3 massive_scrape.py          # Default: 5000 items
python3 massive_scrape.py 10000    # Target 10k items
python3 massive_scrape.py 20000 150  # 20k items, 150/search
```

---

## How It Works

### Current Limitation (30 items)
The `full_scrape.py` is set to **30 items per category** to:
- Be respectful to Depop (avoid IP bans)
- Get diverse results quickly
- Test the pipeline end-to-end

### What's Actually Available
Each search finds **72-96+ product cards** on the page initially.
With **infinite scroll**, you can load:
- **3 scrolls** → ~72-96 items
- **10 scrolls** → ~240 items
- **50 scrolls** → ~1200 items
- **100+ scrolls** → 2400+ items per search

### Scaling Up

The scraper extracts items using:
```python
containers = await page.query_selector_all('[class*="productCardRoot"]')
# Returns ALL items on page (not limited)

# Then we limit:
for container in containers[:max_items]:  # ← This limits
```

---

## Embedding After Scraping

After any scrape, generate embeddings:

```bash
# Process first 50 items (test)
python3 embed_items.py

# Process ALL items in database
python3 embed_items.py all
```

---

## Production Recommendations

### Small Dataset (500-1000 items)
Perfect for MVP/testing:
```bash
python3 full_scrape.py medium
python3 embed_items.py all
```

### Medium Dataset (5000-10000 items)
Good for production launch:
```bash
python3 massive_scrape.py 10000
python3 embed_items.py all
```

### Large Dataset (50000+ items)
For serious scale (run overnight):
```bash
# Run in screen/tmux session
screen -S depop-scrape
python3 massive_scrape.py 50000 200
# Ctrl+A, D to detach

# Later: generate embeddings (may take hours)
python3 embed_items.py all
```

---

## Avoiding Bans

The scraper includes anti-detection:
- ✅ User-agent rotation
- ✅ Random delays (3-10 seconds between searches)
- ✅ Headless browser stealth mode
- ✅ Human-like scrolling patterns

**Best practices:**
1. Don't scrape 24/7
2. Use delays between runs (run once/day or once/week)
3. For huge datasets, spread across multiple days
4. Monitor for CAPTCHA or blocks (scraper will fail gracefully)

---

## Sample Sizes

| Script | Categories | Items/Cat | Total Items | Time |
|--------|-----------|-----------|-------------|------|
| `depop_scraper_working.py` | 2 | 20 | 40 | 1 min |
| `full_scrape.py` (quick) | 26 | 30 | ~780 | 8 min |
| `full_scrape.py` (medium) | 26 | 100 | ~2600 | 20 min |
| `full_scrape.py` (large) | 26 | 500 | ~13000 | 90 min |
| `massive_scrape.py` (5k) | ~95 | 100 | 5000 | 2 hrs |
| `massive_scrape.py` (20k) | ~95 | 200 | 20000 | 6 hrs |

---

## Current Status

As of your last run:
- ✅ Scraper working perfectly
- ✅ Database configured
- ✅ 40+ items already in database
- ⏳ Embedding script ready

**Next steps:**
1. Wait for current `full_scrape.py` to finish (~5 more minutes)
2. Run `python3 embed_items.py all` to generate embeddings
3. Test search API with image queries

---

## Files

| File | Purpose |
|------|---------|
| `depop_scraper_working.py` | Core scraper (imported by others) |
| `full_scrape.py` | Multi-category scrape (configurable) |
| `depop_scraper_unlimited.py` | Single-category deep scrape |
| `massive_scrape.py` | Production-scale scraping |
| `embed_items.py` | Generate CLIP embeddings |
| `test_scraper.py` | Quick test/debug |
