"""
Enhanced metadata extraction from unstructured title/description fields.
Extracts brand, category, color, size from text when API data unavailable.
"""
import re
from marketplace_maps import normalize_color, normalize_category, STANDARD_COLORS, STANDARD_CATEGORIES

# Common brand keywords to extract from titles
KNOWN_BRANDS = [
    # Luxury
    'gucci', 'prada', 'louis vuitton', 'lv', 'chanel', 'burberry', 'balenciaga',
    'saint laurent', 'ysl', 'givenchy', 'dior', 'celine', 'bottega veneta', 'loewe',
    
    # Designer
    'acne studios', 'ami paris', 'apc', 'a.p.c.', 'comme des garcons', 'cdg',
    'rick owens', 'maison margiela', 'margiela', 'yohji yamamoto', 'issey miyake',
    'jil sander', 'helmut lang', 'raf simons', 'undercover',
    
    # Streetwear
    'supreme', 'palace', 'bape', 'off-white', 'fear of god', 'fog', 'stussy',
    'carhartt wip', 'carhartt', 'stone island', 'cp company',
    
    # Sportswear  
    'nike', 'adidas', 'jordan', 'puma', 'reebok', 'new balance', 'vans',
    'converse', 'champion', 'under armour', 'asics', 'saucony',
    
    # Outdoor
    "arc'teryx", 'arcteryx', 'patagonia', 'the north face', 'north face',
    'columbia', 'fjallraven', 'll bean',
    
    # Classic
    'ralph lauren', 'polo', 'tommy hilfiger', 'calvin klein', 'lacoste',
    "levi's", 'levis', 'wrangler', 'lee', 'diesel',
    
    # Contemporary
    'allsaints', 'cos', 'uniqlo', 'muji', 'everlane', 'madewell',
]

# Category keywords
CATEGORY_KEYWORDS = {
    't-shirt': ['t-shirt', 'tee', 'tshirt', 'graphic tee'],
    'shirt': ['shirt', 'button up', 'button-up', 'oxford', 'flannel'],
    'hoodie': ['hoodie', 'hood', 'hooded sweatshirt'],
    'sweater': ['sweater', 'pullover', 'knit', 'jumper', 'crewneck'],
    'sweatshirt': ['sweatshirt', 'crewneck sweatshirt'],
    'cardigan': ['cardigan'],
    'jeans': ['jeans', 'denim pants', 'selvedge'],
    'pants': ['pants', 'trousers', 'chinos', 'slacks', 'cargo pants'],
    'shorts': ['shorts'],
    'jacket': ['jacket', 'bomber', 'trucker', 'windbreaker', 'anorak', 'fleece jacket'],
    'coat': ['coat', 'overcoat', 'trench', 'parka', 'peacoat'],
    'vest': ['vest', 'gilet', 'waistcoat'],
    'dress': ['dress'],
    'skirt': ['skirt'],
    'sneakers': ['sneakers', 'trainers', 'running shoes'],
    'boots': ['boots', 'chelsea boots', 'combat boots', 'work boots'],
    'shoes': ['shoes', 'oxfords', 'derbies', 'loafers'],
    'bag': ['bag', 'backpack', 'tote', 'messenger bag', 'duffle'],
    'hat': ['hat', 'beanie', 'cap', 'snapback'],
    'belt': ['belt'],
}

# Color keywords - expanded with more variations
COLOR_KEYWORDS = {
    'black': ['black', 'noir', 'onyx', 'ebony', 'jet black', 'matte black'],
    'white': ['white', 'cream', 'ivory', 'off-white', 'blanc', 'eggshell', 'pearl', 'snow'],
    'grey': ['grey', 'gray', 'charcoal', 'heather', 'gris', 'slate', 'ash', 'silver', 'gunmetal'],
    'navy': ['navy', 'navy blue', 'marine', 'midnight blue', 'dark blue'],
    'blue': ['blue', 'cobalt', 'royal blue', 'sky blue', 'bleu', 'azure', 'cerulean', 'teal', 'turquoise', 'cyan'],
    'red': ['red', 'burgundy', 'maroon', 'crimson', 'rouge', 'scarlet', 'cherry', 'wine'],
    'pink': ['pink', 'rose', 'blush', 'fuchsia', 'magenta', 'hot pink', 'salmon', 'coral'],
    'green': ['green', 'olive', 'forest', 'sage', 'mint', 'vert', 'lime', 'emerald', 'jade', 'hunter green'],
    'yellow': ['yellow', 'mustard', 'gold', 'jaune', 'lemon', 'butter', 'golden'],
    'orange': ['orange', 'rust', 'burnt orange', 'amber', 'copper', 'peach'],
    'purple': ['purple', 'violet', 'lavender', 'plum', 'mauve', 'lilac', 'grape'],
    'brown': ['brown', 'tan', 'khaki', 'camel', 'chocolate', 'marron', 'coffee', 'mocha', 'chestnut', 'cognac'],
    'beige': ['beige', 'sand', 'taupe', 'nude', 'wheat', 'oatmeal', 'ecru'],
    'multi': ['multi', 'multicolor', 'rainbow', 'tie dye', 'print', 'pattern', 'camo', 'camouflage', 'floral'],
}

# Size patterns
SIZE_PATTERNS = [
    r'\bsize[:\s]+([xsmlXSML\d]+)\b',  # "Size: L", "size M"
    r'\b([xsmlXSML]{1,3})\b',          # Standalone: "L", "XL", "XXL"
    r'\b(\d{1,2})\b',                  # Numeric: "32", "10"
    r'\b(\d{1,2}[rRwW])\b',            # Waist: "32w", "34R"
    r'\b(\d{1,2}x\d{1,2})\b',          # Pants: "32x34"
]


def extract_brand(text: str) -> str:
    """
    Extract brand from title or description.
    Returns 'Unknown' if not found.
    """
    if not text:
        return 'Unknown'
    
    text_lower = text.lower()
    
    # Check for each known brand
    for brand in KNOWN_BRANDS:
        if brand in text_lower:
            # Return properly capitalized version
            if brand == 'lv':
                return 'Louis Vuitton'
            elif brand == 'ysl':
                return 'Saint Laurent'
            elif brand == 'cdg':
                return 'Comme des Garcons'
            elif brand == 'fog':
                return 'Fear of God'
            elif brand == 'north face':
                return 'The North Face'
            elif brand == 'arcteryx':
                return "Arc'teryx"
            elif brand == 'apc' or brand == 'a.p.c.':
                return 'A.P.C.'
            else:
                # Title case the brand
                return ' '.join(word.capitalize() for word in brand.split())
    
    return 'Unknown'


def extract_category(text: str) -> str:
    """
    Extract category from title or description.
    Returns 'other' if not found.
    """
    if not text:
        return 'other'
    
    text_lower = text.lower()
    
    # Check for category keywords (order matters - more specific first)
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category
    
    return 'other'


def extract_color(text: str) -> str:
    """
    Extract color from title or description.
    Returns 'unknown' if not found.
    """
    if not text:
        return 'unknown'
    
    text_lower = text.lower()
    
    # Check for color keywords (prioritize more specific matches)
    # Sort by keyword length descending to match "navy blue" before "blue"
    matches = []
    for color, keywords in COLOR_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                # Store match with keyword length for prioritization
                matches.append((color, len(keyword)))
    
    # Return the color with the longest matching keyword (most specific)
    if matches:
        matches.sort(key=lambda x: -x[1])  # Sort by length descending
        return matches[0][0]
    
    return 'unknown'


def extract_size(text: str) -> str:
    """
    Extract size from title or description.
    Returns 'M' (medium) as default if not found.
    """
    if not text:
        return 'M'
    
    # Try each size pattern
    for pattern in SIZE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            size = match.group(1).upper()
            # Validate it's a reasonable size
            if len(size) <= 6:  # Avoid matching random numbers
                return size
    
    return 'M'


def extract_condition(text: str) -> str:
    """
    Extract condition from title or description.
    Returns 'Good' as default.
    """
    if not text:
        return 'Good'
    
    text_lower = text.lower()
    
    if 'new with tags' in text_lower or 'nwt' in text_lower:
        return 'New'
    if 'new without tags' in text_lower or 'nwot' in text_lower:
        return 'Like New'
    if 'excellent' in text_lower or 'mint' in text_lower:
        return 'Excellent'
    if 'good' in text_lower:
        return 'Good'
    if 'fair' in text_lower or 'worn' in text_lower:
        return 'Fair'
    if 'poor' in text_lower or 'damaged' in text_lower:
        return 'Poor'
    
    return 'Good'


def enhance_item_metadata(item: dict) -> dict:
    """
    Enhance an item dict with extracted structured metadata.
    
    Args:
        item: Dict with at minimum 'title', optionally 'description'
    
    Returns:
        Enhanced item dict with brand, category, color, size, condition
    """
    text = f"{item.get('title', '')} {item.get('description', '')}"
    
    # Extract if not already present
    if not item.get('brand') or item['brand'] == 'Unknown':
        item['brand'] = extract_brand(text)
    
    if not item.get('category') or item['category'] == 'other':
        item['category'] = extract_category(text)
    
    if not item.get('color') or item['color'] == 'unknown':
        item['color'] = extract_color(text)
    
    if not item.get('size'):
        item['size'] = extract_size(text)
    
    if not item.get('condition'):
        item['condition'] = extract_condition(text)
    
    return item


# Test function
if __name__ == '__main__':
    # Test extraction
    test_items = [
        {
            'title': 'Nike ACG Skull Peak Reversible Vest Purple Black Size L',
            'description': 'Excellent condition, barely worn'
        },
        {
            'title': 'Supreme Box Logo Hoodie Red Size M',
            'description': 'New with tags'
        },
        {
            'title': 'Vintage Levis 501 Jeans Blue Denim 32x34',
            'description': 'Good condition, some fading'
        },
        {
            'title': "Arc'teryx Beta AR Jacket Navy Men's Medium",
            'description': 'Like new condition'
        }
    ]
    
    print("Testing metadata extraction:\n")
    for item in test_items:
        enhanced = enhance_item_metadata(item.copy())
        print(f"Title: {item['title']}")
        print(f"  Brand: {enhanced['brand']}")
        print(f"  Category: {enhanced['category']}")
        print(f"  Color: {enhanced['color']}")
        print(f"  Size: {enhanced['size']}")
        print(f"  Condition: {enhanced['condition']}")
        print()
