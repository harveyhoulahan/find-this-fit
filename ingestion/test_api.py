#!/usr/bin/env python3
"""
Test the Find This Fit API with image upload.
Shows how the iOS Mini App will send camera images.
"""
import base64
import requests
import json


def search_by_image_file(image_path: str, api_url: str = "http://localhost:8000"):
    """
    Upload an image to the API and get similar fashion items.
    
    This simulates what the iOS Mini App camera will do:
    1. Capture photo
    2. Encode as base64
    3. POST to /search_by_image
    4. Display results
    """
    print(f"📸 Loading image: {image_path}")
    
    # Read and encode image
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    print(f"🔍 Searching for similar items...")
    
    # Call API
    response = requests.post(
        f"{api_url}/search_by_image",
        json={"image_base64": image_b64},
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"❌ API Error: {response.status_code}")
        print(response.text)
        return None
    
    results = response.json()
    items = results.get("items", [])
    
    print(f"\n✅ Found {len(items)} similar items:\n")
    print("="*80)
    
    for idx, item in enumerate(items, 1):
        similarity = 1 - item.get("distance", 0) if item.get("distance") is not None else 0
        print(f"\n{idx}. {item.get('title', 'N/A')}")
        print(f"   💰 Price: ${item.get('price', 'N/A')}")
        print(f"   📊 Similarity: {similarity:.3f}")
        print(f"   🔗 URL: {item.get('url', 'N/A')}")
        print(f"   🖼️  Image: {item.get('image_url', 'N/A')[:70]}...")
        if item.get('redirect_url'):
            print(f"   📱 Deep Link: {item['redirect_url']}")
    
    print("\n" + "="*80)
    print(f"\n💡 API Response Time: {response.elapsed.total_seconds():.2f}s")
    
    return items


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 test_api.py <image_path>")
        print("\nExample:")
        print("  python3 test_api.py /Users/harveyhoulahan/Desktop/puffer_jacket.png")
        return 1
    
    image_path = sys.argv[1]
    
    print("\n" + "█"*80)
    print("  FIND THIS FIT - API IMAGE SEARCH TEST")
    print("█"*80 + "\n")
    
    search_by_image_file(image_path)
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
