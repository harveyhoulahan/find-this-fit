#!/usr/bin/env python3
"""
Test the image search API with real queries.
Tests both text and image-based search after embeddings are generated.
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/find_this_fit")

from db import fetch_all_sync, execute_sync
import numpy as np


def embed_text(text: str):
    """Generate text embedding using CLIP model."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("clip-ViT-B-32")
    embedding = model.encode(text, normalize_embeddings=True)
    # Pad to 768 dimensions
    if len(embedding) < 768:
        embedding = np.pad(embedding, (0, 768 - len(embedding)), mode='constant')
    return embedding.tolist()


def embed_image(image_path: str):
    """Generate image embedding using CLIP model."""
    from sentence_transformers import SentenceTransformer
    from PIL import Image
    
    model = SentenceTransformer("clip-ViT-B-32")
    image = Image.open(image_path).convert("RGB")
    embedding = model.encode(image, normalize_embeddings=True)
    # Pad to 768 dimensions
    if len(embedding) < 768:
        embedding = np.pad(embedding, (0, 768 - len(embedding)), mode='constant')
    return embedding.tolist()


def test_database_status():
    """Check how many items we have and how many are embedded."""
    print("="*70)
    print("📊 DATABASE STATUS")
    print("="*70)
    
    # Total items
    result = fetch_all_sync("SELECT COUNT(*) as count FROM fashion_items;")
    total = result[0]['count'] if result else 0
    
    # Items with embeddings
    result = fetch_all_sync("SELECT COUNT(*) as count FROM fashion_items WHERE embedding IS NOT NULL;")
    embedded = result[0]['count'] if result else 0
    
    # Items without embeddings
    pending = total - embedded
    
    print(f"Total items scraped: {total}")
    print(f"Items with embeddings: {embedded}")
    print(f"Items pending embedding: {pending}")
    
    if embedded > 0:
        print(f"\n✅ {embedded} items ready for search!")
    else:
        print(f"\n⚠️  No embeddings yet. Run: python3 embed_items.py all")
    
    print("="*70)
    print()
    
    return embedded > 0


def test_text_search(query: str, limit: int = 10):
    """
    Test text-based semantic search.
    
    Args:
        query: Text description of what you're looking for
        limit: Number of results to return
    """
    print(f"🔍 Searching for: \"{query}\"")
    print("-"*70)
    
    # Generate embedding for query text
    query_vector = embed_text(query)
    
    # Search database
    results = fetch_all_sync(
        """
        SELECT 
            id,
            external_id,
            title,
            price,
            url,
            image_url,
            source,
            1 - (embedding <=> %s::vector) as similarity
        FROM fashion_items
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """,
        (query_vector, query_vector, limit)
    )
    
    if not results:
        print("❌ No results found")
        return
    
    print(f"\n✅ Found {len(results)} results:\n")
    
    for idx, item in enumerate(results, 1):
        print(f"{idx}. {item['title']}")
        print(f"   Price: ${item['price']}")
        print(f"   Similarity: {item['similarity']:.3f}")
        print(f"   URL: {item['url']}")
        print(f"   Image: {item['image_url'][:60]}...")
        print()
    
    return results


def test_image_search(image_path: str, limit: int = 10):
    """
    Test image-based semantic search.
    
    Args:
        image_path: Path to the image file you want to search with
        limit: Number of results to return
    """
    print(f"🖼️  Searching with image: \"{image_path}\"")
    print("-"*70)
    
    # Generate embedding for query image
    query_vector = embed_image(image_path)
    
    # Search database
    results = fetch_all_sync(
        """
        SELECT 
            id,
            external_id,
            title,
            price,
            url,
            image_url,
            source,
            1 - (embedding <=> %s::vector) as similarity
        FROM fashion_items
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """,
        (query_vector, query_vector, limit)
    )
    
    if not results:
        print("❌ No results found")
        return
    
    print(f"\n✅ Found {len(results)} similar items:\n")
    
    for idx, item in enumerate(results, 1):
        print(f"{idx}. {item['title']}")
        print(f"   Price: ${item['price']}")
        print(f"   Similarity: {item['similarity']:.3f}")
        print(f"   URL: {item['url']}")
        print(f"   Image: {item['image_url'][:60]}...")
        print()
    
    return results


def test_sample_queries():
    """Run a series of test queries to demonstrate search quality."""
    
    queries = [
        "oversized vintage hoodie",
        "baggy cargo pants y2k style",
        "cropped graphic tee",
        "90s denim jacket",
        "streetwear windbreaker",
    ]
    
    print("="*70)
    print("🧪 RUNNING SAMPLE SEARCH QUERIES")
    print("="*70)
    print()
    
    for query in queries:
        test_text_search(query, limit=3)
        print("="*70)
        print()


def show_random_samples(limit: int = 10):
    """Show random items from the database."""
    print("="*70)
    print(f"📦 RANDOM SAMPLE ({limit} items)")
    print("="*70)
    print()
    
    items = fetch_all_sync(
        """
        SELECT title, price, image_url, source
        FROM fashion_items
        WHERE embedding IS NOT NULL
        ORDER BY RANDOM()
        LIMIT %s;
        """,
        (limit,)
    )
    
    for idx, item in enumerate(items, 1):
        print(f"{idx}. {item['title']}")
        print(f"   ${item['price']}")
        print(f"   {item['image_url'][:70]}...")
        print()


def main():
    """Main test runner."""
    print("\n")
    print("█" * 70)
    print("  FIND THIS FIT - SEARCH API TEST")
    print("█" * 70)
    print()
    
    # Check database status
    has_embeddings = test_database_status()
    
    if not has_embeddings:
        print("⚠️  Cannot test search without embeddings.")
        print("Run this first: python3 embed_items.py all")
        print()
        return 1
    
    # Show random samples
    show_random_samples(limit=5)
    print()
    
    # Run test queries
    test_sample_queries()
    
    # Interactive mode
    print("="*70)
    print("🎮 INTERACTIVE MODE")
    print("="*70)
    print("Enter search queries (or 'quit' to exit):")
    print()
    
    while True:
        try:
            query = input("Search: ").strip()
            
            if not query or query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            print()
            test_text_search(query, limit=5)
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            continue
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
