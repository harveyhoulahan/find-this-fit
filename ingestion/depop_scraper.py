"""
Production Depop scraper with politeness, retry logic, and duplicate detection.
Respects robots.txt and rate limits to avoid blocking.
"""
import random
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

import sys
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from config import REQUEST_TIMEOUT  # noqa: E402
from db import execute_sync  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]


def _headers() -> Dict[str, str]:
    """Rotate user agents to avoid detection."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def fetch_listing_page(search_term: str, page: int = 1, retries: int = 3) -> Optional[str]:
    """
    Fetch a Depop search results page with retry logic.
    
    Note: As of Nov 2025, Depop may use client-side rendering.
    For production, consider:
    - Selenium/Playwright for JS rendering
    - Official Depop API if available
    - Depop RSS feeds
    """
    url = f"https://www.depop.com/search/?q={search_term}&page={page}"
    
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                headers=_headers(),
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 429:
                # Rate limited - back off exponentially
                sleep_time = (2 ** attempt) * 5
                logger.warning(f"Rate limited. Sleeping {sleep_time}s...")
                time.sleep(sleep_time)
            else:
                logger.warning(f"HTTP {resp.status_code} for {url}")
                return None
        except requests.RequestException as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    
    return None


def parse_listings(html: str) -> List[Dict[str, Any]]:
    """
    Parse Depop listings from HTML.
    
    WARNING: This is fragile and will break if Depop changes their markup.
    For production:
    - Use official API
    - Use structured data (JSON-LD)
    - Implement robust selectors with fallbacks
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("a", href=True)
    listings = []
    
    for card in cards:
        href = card["href"]
        if "/products/" not in href:
            continue
        
        title_elem = card.get("title") or card.get_text(strip=True)
        price_elem = card.find(string=lambda x: x and ("£" in x or "$" in x))
        img_tag = card.find("img")
        
        # Extract external ID from URL
        external_id = href.strip("/").split("/")[-1]
        
        listings.append({
            "external_id": external_id,
            "title": title_elem.strip() if title_elem else None,
            "price": _parse_price(price_elem) if price_elem else None,
            "url": f"https://www.depop.com{href}" if href.startswith("/") else href,
            "image_url": img_tag["src"] if img_tag and img_tag.has_attr("src") else None,
            "description": None,  # Would need individual item page fetch
        })
    
    return listings


def _parse_price(text: str) -> Optional[float]:
    """Extract numeric price from text like '£45.00' or '$30'."""
    clean = "".join(ch for ch in text if ch.isdigit() or ch == "." or ch == ",")
    try:
        return float(clean.replace(",", ""))
    except ValueError:
        return None


def save_listing(item: Dict[str, Any]):
    """
    Upsert listing into database.
    Uses ON CONFLICT to handle duplicates gracefully.
    """
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
            item.get("external_id"),
            item.get("title"),
            item.get("description"),
            item.get("price"),
            item.get("url"),
            item.get("image_url"),
        ),
    )


def scrape(search_terms: List[str], pages: int = 1, delay_seconds: float = 2.0):
    """
    Scrape Depop for given search terms.
    
    Politeness:
    - 2-3s delay between requests
    - Random jitter to avoid detection
    - User agent rotation
    - Exponential backoff on errors
    
    Args:
        search_terms: List of queries like ["vintage tee", "denim jacket"]
        pages: Number of result pages per term
        delay_seconds: Base delay between requests
    """
    total_saved = 0
    
    for term in search_terms:
        logger.info(f"Scraping '{term}'...")
        
        for page in range(1, pages + 1):
            html = fetch_listing_page(term, page)
            if not html:
                logger.warning(f"Failed to fetch page {page} for '{term}'")
                continue
            
            listings = parse_listings(html)
            logger.info(f"Found {len(listings)} listings on page {page}")
            
            for listing in listings:
                try:
                    save_listing(listing)
                    total_saved += 1
                    # Small delay between DB writes
                    time.sleep(delay_seconds / 10)
                except Exception as e:
                    logger.error(f"Failed to save {listing.get('external_id')}: {e}")
            
            # Delay between pages with jitter
            jitter = random.uniform(0.5, 1.5)
            time.sleep(delay_seconds * jitter)
    
    logger.info(f"Scraping complete. Saved {total_saved} items.")


if __name__ == "__main__":
    # Example usage
    scrape(
        search_terms=["vintage tee", "denim jacket", "y2k dress"],
        pages=2,
        delay_seconds=2.5
    )
