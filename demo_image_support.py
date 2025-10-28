#!/usr/bin/env python3
"""
Demo script to show image support functionality.
This script demonstrates how the bot validates and handles images.
"""

from bot import AmazingRaceBot
import os

def demo_image_validation():
    """Demonstrate image validation features."""
    print("=" * 60)
    print("AmazingRaceBot Image Support Demo")
    print("=" * 60)
    print()
    
    # Create a minimal config for testing
    bot = AmazingRaceBot("config.example.yml")
    
    print("1. URL Validation Tests")
    print("-" * 60)
    
    test_urls = [
        ("https://example.com/image.jpg", True, "Valid HTTPS URL with extension"),
        ("http://example.com/image.jpg", False, "HTTP rejected (not HTTPS)"),
        ("https://i.imgur.com/abc123", True, "Trusted domain without extension"),
        ("https://random-site.com/noext", False, "Non-trusted domain without extension"),
    ]
    
    for url, expected, description in test_urls:
        result = bot.validate_image_url(url)
        status = "✓" if result == expected else "✗"
        print(f"{status} {description}")
        print(f"   URL: {url}")
        print(f"   Expected: {expected}, Got: {result}")
        print()
    
    print("\n2. Path Validation Tests")
    print("-" * 60)
    
    test_paths = [
        ("images/test_challenge.png", True, "Valid local path"),
        ("../../../etc/passwd", False, "Directory traversal rejected"),
        ("/tmp/image.png", False, "Absolute path rejected"),
        ("images/nonexistent.png", False, "Non-existent file rejected"),
    ]
    
    for path, should_pass, description in test_paths:
        result = bot.validate_image_path(path)
        status = "✓" if (result is not None) == should_pass else "✗"
        print(f"{status} {description}")
        print(f"   Path: {path}")
        print(f"   Expected: {'Valid' if should_pass else 'Invalid'}, Got: {'Valid' if result else 'Invalid'}")
        print()
    
    print("\n3. Feature Summary")
    print("-" * 60)
    print("✓ Challenge images supported (image_url or image_path)")
    print("✓ Hint images supported (hint_images mapping)")
    print("✓ HTTPS-only URL validation")
    print("✓ Path traversal protection")
    print("✓ File extension validation")
    print("✓ Trusted domain whitelist")
    print()
    
    print("4. Configuration Example")
    print("-" * 60)
    print("""
challenges:
  - id: 1
    name: "Identify the Landmark"
    description: "What landmark is shown?"
    image_url: "https://example.com/landmark.jpg"
    hints:
      - "It's in France"
    hint_images:
      0: "images/france_map.jpg"
    """)
    
    print("\n" + "=" * 60)
    print("Demo complete! See docs/IMAGE_SUPPORT.md for details.")
    print("=" * 60)

if __name__ == "__main__":
    demo_image_validation()
