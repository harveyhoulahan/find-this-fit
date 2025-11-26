#!/bin/bash
# Auto-scrape and embed script
# Keeps Mac awake, runs scraper, then automatically embeds all items

set -e

echo "============================================"
echo "🚀 AUTO SCRAPE & EMBED PIPELINE"
echo "============================================"
echo ""
echo "This will:"
echo "1. Keep your Mac awake"
echo "2. Run luxury brand scraper"
echo "3. Automatically embed all items when done"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to start..."
sleep 5

# Change to ingestion directory
cd "$(dirname "$0")"

echo ""
echo "📍 Working directory: $(pwd)"
echo ""

# Run scraper with caffeinate (keeps Mac awake)
echo "☕ Starting scraper (Mac will stay awake)..."
echo ""

caffeinate -i python3 luxury_brand_scrape.py all 50

SCRAPE_EXIT=$?

echo ""
echo "============================================"

if [ $SCRAPE_EXIT -eq 0 ] || [ $SCRAPE_EXIT -eq 130 ]; then
    echo "✅ Scraping complete!"
    echo ""
    
    # Check how many items need embedding
    echo "🔍 Checking items without embeddings..."
    UNEMBEDDED=$(docker exec -i findthisfit-db psql -U postgres -d find_this_fit -t -c "SELECT COUNT(*) FROM fashion_items WHERE embedding IS NULL;")
    UNEMBEDDED=$(echo $UNEMBEDDED | xargs)  # trim whitespace
    
    echo "Found $UNEMBEDDED items without embeddings"
    echo ""
    
    if [ "$UNEMBEDDED" -gt 0 ]; then
        echo "🧠 Starting automatic embedding..."
        echo ""
        
        # Run embedding (also with caffeinate)
        caffeinate -i python3 embed_items.py all
        
        EMBED_EXIT=$?
        
        echo ""
        if [ $EMBED_EXIT -eq 0 ]; then
            echo "============================================"
            echo "🎉 COMPLETE! Everything is embedded and ready!"
            echo "============================================"
            
            # Show final stats
            echo ""
            echo "📊 Final database stats:"
            docker exec -i findthisfit-db psql -U postgres -d find_this_fit -c "
                SELECT 
                    COUNT(*) as total_items,
                    COUNT(*) FILTER (WHERE embedding IS NOT NULL) as embedded,
                    COUNT(*) FILTER (WHERE embedding IS NULL) as not_embedded,
                    pg_size_pretty(pg_total_relation_size('fashion_items')) as size
                FROM fashion_items;
            "
            
            echo ""
            echo "✨ Your search API is ready to use!"
        else
            echo "⚠️  Embedding failed with exit code $EMBED_EXIT"
            echo "💡 You can run it manually: python3 embed_items.py all"
        fi
    else
        echo "✨ No new items to embed - you're all set!"
    fi
else
    echo "❌ Scraping failed with exit code $SCRAPE_EXIT"
    echo "💡 Check the logs above for errors"
fi

echo ""
echo "============================================"
