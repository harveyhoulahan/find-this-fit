#!/usr/bin/env python3
"""
Generate FindThisFit App Icon
Creates a modern, minimalist fashion search icon for iOS
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_app_icon():
    """Create a stylish app icon with fashion theme"""
    
    # Create 1024x1024 canvas (iOS app icon size)
    size = 1024
    
    # Modern gradient background (fashion brand colors)
    img = Image.new('RGB', (size, size), color='white')
    draw = ImageDraw.Draw(img)
    
    # Gradient background (black to dark purple - luxury feel)
    for y in range(size):
        # Gradient from black (#000000) to deep purple (#1a0033)
        r = int(26 * (y / size))
        g = 0
        b = int(51 * (y / size))
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    
    # Draw camera lens icon (simplified, modern)
    center = size // 2
    
    # Outer circle (camera lens outer ring) - gold/brass color
    outer_radius = int(size * 0.35)
    draw.ellipse(
        [center - outer_radius, center - outer_radius, 
         center + outer_radius, center + outer_radius],
        outline='#D4AF37',  # Gold color
        width=int(size * 0.04)
    )
    
    # Inner circle (lens glass) - white with transparency effect
    inner_radius = int(size * 0.25)
    draw.ellipse(
        [center - inner_radius, center - inner_radius, 
         center + inner_radius, center + inner_radius],
        fill='#1a1a2e',
        outline='#D4AF37',
        width=int(size * 0.02)
    )
    
    # Add sparkle/AI effect (small circles around lens)
    sparkle_positions = [
        (center + int(outer_radius * 0.7), center - int(outer_radius * 0.7)),
        (center - int(outer_radius * 0.7), center + int(outer_radius * 0.7)),
        (center + int(outer_radius * 0.85), center),
    ]
    
    sparkle_size = int(size * 0.03)
    for x, y in sparkle_positions:
        draw.ellipse(
            [x - sparkle_size, y - sparkle_size, x + sparkle_size, y + sparkle_size],
            fill='#FFD700'  # Bright gold
        )
    
    # Add small lens reflection
    reflection_radius = int(size * 0.08)
    reflection_x = center - int(inner_radius * 0.4)
    reflection_y = center - int(inner_radius * 0.4)
    draw.ellipse(
        [reflection_x - reflection_radius, reflection_y - reflection_radius,
         reflection_x + reflection_radius, reflection_y + reflection_radius],
        fill='#ffffff',
        outline=None
    )
    
    # Add smaller reflection
    small_reflection = int(size * 0.04)
    small_x = reflection_x + int(reflection_radius * 1.5)
    small_y = reflection_y + int(reflection_radius * 1.5)
    draw.ellipse(
        [small_x - small_reflection, small_y - small_reflection,
         small_x + small_reflection, small_y + small_reflection],
        fill='#cccccc',
        outline=None
    )
    
    # Save the icon
    output_dir = 'FindThisFit/Assets.xcassets/AppIcon.appiconset'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save main icon
    img.save(f'{output_dir}/icon-1024.png', 'PNG')
    print(f"✓ Created {output_dir}/icon-1024.png")
    
    # Create alternate version for dark mode (lighter)
    img_dark = Image.new('RGB', (size, size), color='white')
    draw_dark = ImageDraw.Draw(img_dark)
    
    # Lighter gradient for dark mode
    for y in range(size):
        r = int(10 + 40 * (y / size))
        g = int(10 + 30 * (y / size))
        b = int(20 + 60 * (y / size))
        draw_dark.line([(0, y), (size, y)], fill=(r, g, b))
    
    # Redraw icons on dark version
    draw_dark.ellipse(
        [center - outer_radius, center - outer_radius, 
         center + outer_radius, center + outer_radius],
        outline='#FFD700',
        width=int(size * 0.04)
    )
    
    draw_dark.ellipse(
        [center - inner_radius, center - inner_radius, 
         center + inner_radius, center + inner_radius],
        fill='#0f0f1e',
        outline='#FFD700',
        width=int(size * 0.02)
    )
    
    for x, y in sparkle_positions:
        draw_dark.ellipse(
            [x - sparkle_size, y - sparkle_size, x + sparkle_size, y + sparkle_size],
            fill='#FFD700'
        )
    
    draw_dark.ellipse(
        [reflection_x - reflection_radius, reflection_y - reflection_radius,
         reflection_x + reflection_radius, reflection_y + reflection_radius],
        fill='#ffffff',
        outline=None
    )
    
    draw_dark.ellipse(
        [small_x - small_reflection, small_y - small_reflection,
         small_x + small_reflection, small_y + small_reflection],
        fill='#cccccc',
        outline=None
    )
    
    img_dark.save(f'{output_dir}/icon-1024-dark.png', 'PNG')
    print(f"✓ Created {output_dir}/icon-1024-dark.png")
    
    print("\n✨ App icons generated successfully!")
    print("\nNext steps:")
    print("1. Open Xcode project")
    print("2. Go to Assets.xcassets > AppIcon")
    print("3. Drag icon-1024.png to the 'iOS App' slot")
    print("4. Drag icon-1024-dark.png to the 'iOS App Dark' slot")
    print("5. Build and run - your icon will appear on the home screen!")

if __name__ == '__main__':
    try:
        create_app_icon()
    except ImportError:
        print("❌ PIL/Pillow not installed")
        print("Install with: pip3 install Pillow")
