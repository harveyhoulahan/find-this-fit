"""
Marketplace API ID mappings for structured metadata extraction.
Maps brand_id, category_id, color_id to standardized names.

These mappings should be periodically updated from marketplace APIs.
"""

# Standardized color names (all lowercase for consistency)
STANDARD_COLORS = {
    'black', 'white', 'grey', 'gray', 'navy', 'blue', 'red', 'pink',
    'green', 'yellow', 'orange', 'purple', 'brown', 'beige', 'tan',
    'cream', 'gold', 'silver', 'multicolor', 'unknown'
}

# Standardized category names
STANDARD_CATEGORIES = {
    # Tops
    'tshirt', 't-shirt', 'shirt', 'blouse', 'top', 'tank', 'crop-top',
    'sweater', 'sweatshirt', 'hoodie', 'cardigan', 'pullover',
    
    # Bottoms
    'jeans', 'pants', 'trousers', 'shorts', 'skirt', 'leggings',
    
    # Outerwear
    'jacket', 'coat', 'blazer', 'parka', 'windbreaker', 'vest',
    
    # Dresses & Sets
    'dress', 'jumpsuit', 'romper', 'suit',
    
    # Footwear
    'sneakers', 'boots', 'shoes', 'sandals', 'heels', 'loafers',
    
    # Accessories
    'bag', 'backpack', 'handbag', 'wallet', 'belt', 'hat', 'scarf',
    'sunglasses', 'jewelry', 'watch',
    
    # Other
    'other', 'unknown'
}

# Depop Brand ID → Name mapping
# Source: https://webapi.depop.com/api/v2/brands/
DEPOP_BRANDS = {
    1: "Nike",
    2: "Adidas",
    3: "Supreme",
    4: "Vans",
    5: "Converse",
    6: "Jordan",
    7: "Puma",
    8: "Reebok",
    9: "New Balance",
    10: "Carhartt",
    11: "Champion",
    12: "The North Face",
    13: "Patagonia",
    14: "Ralph Lauren",
    15: "Tommy Hilfiger",
    16: "Lacoste",
    17: "Calvin Klein",
    18: "Levi's",
    19: "Wrangler",
    20: "Lee",
    25: "Gucci",
    26: "Prada",
    27: "Louis Vuitton",
    28: "Chanel",
    29: "Burberry",
    30: "Balenciaga",
    31: "Saint Laurent",
    32: "Givenchy",
    33: "Dior",
    34: "Celine",
    35: "Bottega Veneta",
    40: "Stussy",
    41: "Palace",
    42: "BAPE",
    43: "Off-White",
    44: "Fear of God",
    45: "Yeezy",
    50: "Acne Studios",
    51: "AMI Paris",
    52: "A.P.C.",
    53: "Comme des Garcons",
    54: "Rick Owens",
    55: "Maison Margiela",
    56: "Yohji Yamamoto",
    57: "Issey Miyake",
    # Add more as needed from Depop API
}

# Depop Category ID → Standardized category
# Source: https://webapi.depop.com/api/v2/categories/
DEPOP_CATEGORIES = {
    1: "t-shirt",
    2: "shirt",
    3: "sweater",
    4: "hoodie",
    5: "sweatshirt",
    6: "cardigan",
    10: "jeans",
    11: "pants",
    12: "shorts",
    13: "skirt",
    14: "leggings",
    20: "jacket",
    21: "coat",
    22: "blazer",
    23: "vest",
    30: "dress",
    31: "jumpsuit",
    40: "sneakers",
    41: "boots",
    42: "shoes",
    43: "sandals",
    44: "heels",
    50: "bag",
    51: "backpack",
    52: "handbag",
    53: "wallet",
    60: "hat",
    61: "belt",
    62: "scarf",
    63: "sunglasses",
    64: "jewelry",
    # Add more from Depop API
}

# Depop Color ID → Standardized color name
DEPOP_COLORS = {
    1: "black",
    2: "white",
    3: "grey",
    4: "navy",
    5: "blue",
    6: "red",
    7: "pink",
    8: "green",
    9: "yellow",
    10: "orange",
    11: "purple",
    12: "brown",
    13: "beige",
    14: "cream",
    15: "gold",
    16: "silver",
    17: "multicolor",
}

# Grailed Designer ID → Name mapping
# Source: https://www.grailed.com/api/designers
GRAILED_BRANDS = {
    1: "Supreme",
    2: "Nike",
    3: "Adidas",
    5: "Gucci",
    10: "Prada",
    15: "Saint Laurent",
    20: "Balenciaga",
    25: "Off-White",
    30: "Rick Owens",
    35: "Yohji Yamamoto",
    40: "Comme des Garcons",
    45: "Acne Studios",
    50: "AMI Paris",
    55: "A.P.C.",
    60: "Maison Margiela",
    65: "Stone Island",
    70: "Carhartt WIP",
    75: "Arc'teryx",
    80: "Patagonia",
    85: "The North Face",
    # Add more from Grailed designers API
}

# Grailed Category mapping
# Categories follow path structure: ["Menswear", "Outerwear", "Jackets"]
GRAILED_CATEGORY_MAP = {
    ("Menswear", "Tops", "T-Shirts"): "t-shirt",
    ("Menswear", "Tops", "Shirts"): "shirt",
    ("Menswear", "Tops", "Sweaters"): "sweater",
    ("Menswear", "Tops", "Sweatshirts & Hoodies"): "hoodie",
    ("Menswear", "Bottoms", "Denim"): "jeans",
    ("Menswear", "Bottoms", "Trousers"): "pants",
    ("Menswear", "Bottoms", "Shorts"): "shorts",
    ("Menswear", "Outerwear", "Jackets"): "jacket",
    ("Menswear", "Outerwear", "Coats"): "coat",
    ("Menswear", "Footwear", "Sneakers"): "sneakers",
    ("Menswear", "Footwear", "Boots"): "boots",
    ("Menswear", "Accessories", "Bags"): "bag",
    ("Womenswear", "Tops"): "top",
    ("Womenswear", "Dresses"): "dress",
    # Add more category paths
}

# Vinted Brand ID → Name
# Note: Vinted often provides brand_title directly, use that when available
VINTED_BRANDS = {
    1: "Nike",
    2: "Adidas",
    3: "H&M",
    4: "Zara",
    5: "Uniqlo",
    # Vinted usually provides brand_title, so this is backup
}

# Vinted catalog_branch_id → Category
VINTED_CATEGORIES = {
    1: "t-shirt",
    2: "shirt",
    5: "sweater",
    8: "jeans",
    10: "pants",
    12: "jacket",
    15: "dress",
    20: "sneakers",
    25: "bag",
    # Add more from Vinted catalog API
}

# Vinted color_id → Standardized color
# Note: Vinted often provides color_title directly
VINTED_COLORS = {
    1: "black",
    2: "white",
    3: "grey",
    4: "blue",
    5: "navy",
    6: "red",
    7: "pink",
    8: "green",
    9: "yellow",
    10: "beige",
    11: "brown",
    12: "purple",
    # Vinted usually provides color_title, so this is backup
}

def normalize_color(color_str: str) -> str:
    """Normalize color string to standard color."""
    if not color_str:
        return "unknown"
    
    color_lower = color_str.lower().strip()
    
    # Direct match
    if color_lower in STANDARD_COLORS:
        return color_lower
    
    # Fuzzy matching for common variations
    if "black" in color_lower or "noir" in color_lower:
        return "black"
    if "white" in color_lower or "blanc" in color_lower:
        return "white"
    if "grey" in color_lower or "gray" in color_lower:
        return "grey"
    if "navy" in color_lower:
        return "navy"
    if "blue" in color_lower or "bleu" in color_lower:
        return "blue"
    if "red" in color_lower or "rouge" in color_lower:
        return "red"
    if "pink" in color_lower or "rose" in color_lower:
        return "pink"
    if "green" in color_lower or "vert" in color_lower:
        return "green"
    if "yellow" in color_lower or "jaune" in color_lower:
        return "yellow"
    if "orange" in color_lower:
        return "orange"
    if "purple" in color_lower or "violet" in color_lower:
        return "purple"
    if "brown" in color_lower or "marron" in color_lower:
        return "brown"
    if "beige" in color_lower or "tan" in color_lower or "cream" in color_lower:
        return "beige"
    if "gold" in color_lower or "golden" in color_lower:
        return "gold"
    if "silver" in color_lower:
        return "silver"
    if "multi" in color_lower or "print" in color_lower:
        return "multicolor"
    
    return "unknown"

def normalize_category(category_str: str) -> str:
    """Normalize category string to standard category."""
    if not category_str:
        return "other"
    
    cat_lower = category_str.lower().strip()
    
    # Direct match
    if cat_lower in STANDARD_CATEGORIES:
        return cat_lower
    
    # Fuzzy matching
    if "t-shirt" in cat_lower or "tee" in cat_lower:
        return "t-shirt"
    if "shirt" in cat_lower and "t-shirt" not in cat_lower:
        return "shirt"
    if "hoodie" in cat_lower or "hood" in cat_lower:
        return "hoodie"
    if "sweater" in cat_lower or "pullover" in cat_lower or "knit" in cat_lower:
        return "sweater"
    if "sweatshirt" in cat_lower:
        return "sweatshirt"
    if "jean" in cat_lower or "denim" in cat_lower:
        return "jeans"
    if "pant" in cat_lower or "trouser" in cat_lower or "chino" in cat_lower:
        return "pants"
    if "short" in cat_lower:
        return "shorts"
    if "jacket" in cat_lower or "blouson" in cat_lower:
        return "jacket"
    if "coat" in cat_lower or "parka" in cat_lower:
        return "coat"
    if "dress" in cat_lower:
        return "dress"
    if "sneaker" in cat_lower or "trainer" in cat_lower:
        return "sneakers"
    if "boot" in cat_lower:
        return "boots"
    if "shoe" in cat_lower:
        return "shoes"
    if "bag" in cat_lower or "purse" in cat_lower or "sac" in cat_lower:
        return "bag"
    if "skirt" in cat_lower:
        return "skirt"
    
    return "other"
