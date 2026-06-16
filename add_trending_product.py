import os
import sys
import json
import re
import requests

# Force UTF-8 for console output to avoid emoji/unicode encode errors on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def load_env(filepath=".env"):
    """Manually parse a .env file to load variables into os.environ."""
    if not os.path.exists(filepath):
        return False
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                val_str = val.strip().strip("'").strip('"')
                os.environ[key.strip()] = val_str
    return True

def verify_asin_image(asin):
    """Checks if the ASIN has a valid main product image on Amazon's legacy image database."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    url = f"https://images.amazon.com/images/P/{asin}.01.LZZZZZZZ.jpg"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        # Check if the content is a real image (>1000 bytes). A blank/1x1 transparent gif is 43 bytes.
        return r.status_code == 200 and len(r.content) > 1000
    except Exception:
        return False

import time

def get_trending_suggestions(api_key):
    """Asks Gemini to suggest trending Amazon India tech products under Rs. 2000 with retries."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = (
        "Suggest 8 trending tech accessories, gadgets, or smart devices under Rs. 2000 that are highly popular, expected to be searched, and sell well on Amazon India (amazon.in).\n"
        "Provide accurate details including their actual Amazon India ASIN (10-digit uppercase alphanumeric identifier starting with B).\n"
        "Ensure the ASINs are real and correct for the specific products.\n"
        "For each product, write exactly 4 strong, appealing selling points in short bullet format."
    )
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {
                            "type": "STRING", 
                            "description": "Exact product name (e.g. 'Wipro 9W Smart LED Bulb')."
                        },
                        "category": {
                            "type": "STRING", 
                            "description": "General lowercase category name (e.g. 'smart bulb', 'power bank')."
                        },
                        "asin": {
                            "type": "STRING", 
                            "description": "The exact 10-character Amazon India ASIN (must start with B)."
                        },
                        "selling_points": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                            "description": "Exactly 4 key features/selling points."
                        }
                    },
                    "required": ["name", "category", "asin", "selling_points"]
                }
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        print(f"Calling Gemini API to discover trending gadgets in India (Attempt {attempt}/{max_retries})...")
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return []
                text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text")
                if text_content:
                    return json.loads(text_content.strip())
            elif r.status_code == 503:
                print(f"  Service unavailable (503). Retrying in 6 seconds...")
                time.sleep(6)
            else:
                print(f"  Error calling Gemini API (Status Code {r.status_code}): {r.text}")
                break
        except Exception as e:
            print(f"  Error calling Gemini: {e}")
            time.sleep(3)
    return []


def main():
    print("=== ReelFlow AI Product Discovery ===")
    
    if not load_env():
        print("Error: '.env' file not found.")
        sys.exit(1)
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not configured in your '.env' file.")
        sys.exit(1)
        
    suggestions = get_trending_suggestions(api_key)
    if not suggestions:
        print("Failed to get trending recommendations from AI.")
        sys.exit(1)
        
    print(f"AI suggested {len(suggestions)} products. Verifying availability...")
    
    # Load existing database to check for duplicates
    db_file = "products.json"
    existing_products = []
    if os.path.exists(db_file):
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                existing_products = json.load(f)
        except Exception:
            pass
            
    existing_names = {p["name"].lower() for p in existing_products}
    existing_asins = set()
    for p in existing_products:
        match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', p.get("affiliate_link", ""))
        if match:
            existing_asins.add(match.group(1))
            
    added_count = 0
    for s in suggestions:
        name = s.get("name")
        category = s.get("category")
        asin = s.get("asin")
        selling_points = s.get("selling_points")
        
        if not name or not category or not asin or not selling_points:
            continue
            
        # Clean ASIN
        asin = asin.strip().upper()
        if not re.match(r'^B[A-Z0-9]{9}$', asin):
            print(f"Skipping '{name}': Invalid ASIN format '{asin}'")
            continue
            
        # Check for duplicates
        if name.lower() in existing_names or asin in existing_asins:
            print(f"Skipping '{name}' ({asin}): Already exists in database.")
            continue
            
        # Verify image availability on Amazon servers
        print(f"Verifying image for '{name}' (ASIN: {asin})...")
        if verify_asin_image(asin):
            # Construct product entry
            associate_tag = os.environ.get("AMAZON_ASSOCIATE_TAG", "your_tag-21").strip()
            new_entry = {
                "name": name,
                "category": category,
                "affiliate_link": f"https://www.amazon.in/dp/{asin}?tag={associate_tag}",
                "selling_points": selling_points
            }
            existing_products.append(new_entry)
            existing_names.add(name.lower())
            existing_asins.add(asin)
            added_count += 1
            print(f"  --> ✅ Added successfully!")
        else:
            print(f"  --> ❌ Verification failed: Legacy Amazon images database lacks catalog photos for ASIN '{asin}'.")
            
    if added_count > 0:
        # Write back to products.json
        try:
            with open(db_file, "w", encoding="utf-8") as f:
                json.dump(existing_products, f, indent=4, ensure_ascii=False)
            print(f"\nSuccessfully updated products.json! Added {added_count} new products.")
        except Exception as e:
            print(f"Error saving updated database: {e}")
    else:
        print("\nNo new products were added (either duplicates or image verification failed).")

if __name__ == "__main__":
    main()
