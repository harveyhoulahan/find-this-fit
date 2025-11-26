#!/bin/bash
# 🌙 OVERNIGHT SCRAPE RUNNER 🌙
# Run this script and let it work overnight

set -e

echo "============================================================================"
echo "🌙 OVERNIGHT MASS SCRAPER 🌙"
echo "============================================================================"
echo ""
echo "This will:"
echo "  1. Backup your current database"
echo "  2. Clear all existing fashion_items"
echo "  3. Scrape ~50,000+ items from Depop, Grailed, and Vinted"
echo "  4. Take 8-12 hours to complete"
echo ""
echo "⚠️  WARNING: This will DELETE all current items!"
echo ""
read -p "Are you sure you want to proceed? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Scrape cancelled"
    exit 1
fi

echo ""
echo "✅ Starting overnight scrape..."
echo ""

# Navigate to ingestion directory
cd "$(dirname "$0")"

# Check if docker container is running
if ! docker ps | grep -q findthisfit-db; then
    echo "❌ Database container is not running!"
    echo "Please start it with: docker-compose up -d"
    exit 1
fi

# Check Python dependencies
if ! python3 -c "import aiohttp" 2>/dev/null; then
    echo "📦 Installing required packages..."
    pip3 install -r requirements.txt
fi

# Run the scraper
echo "🚀 Starting scraper (this will take 8-12 hours)..."
echo "📝 Progress will be logged to: overnight_scrape_*.log"
echo ""
echo "💡 Using: Playwright + CLIP visual analysis for accurate metadata"
echo "💡 TIP: You can monitor progress with:"
echo "    tail -f ingestion/overnight_scrape_*.log"
echo ""
echo "Press Ctrl+C to stop (will be logged as interrupted)"
echo ""

python3 overnight_mass_scrape_v2.py

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "============================================================================"
    echo "✅ OVERNIGHT SCRAPE COMPLETED SUCCESSFULLY!"
    echo "============================================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Review the log file"
    echo "  2. Generate embeddings: cd ingestion && python3 embed_items.py all"
    echo "  3. Test the API"
    echo ""
else
    echo "============================================================================"
    echo "❌ Scrape failed or was interrupted"
    echo "============================================================================"
    echo ""
    echo "Check the log file for details"
    echo ""
fi

exit $exit_code
