import os
import sys
import json
import random
import re
import requests
import urllib.parse

# Force UTF-8 for console output to avoid emoji/unicode encode errors on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def slugify(text):
    """Converts product name into a standard lowercase directory name."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')

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

def select_product(topic=None):
    """Selects a product from products.json. If topic is provided, tries to find a matching product."""
    db_file = "products.json"
    if not os.path.exists(db_file):
        return None
        
    try:
        with open(db_file, "r", encoding="utf-8") as f:
            products = json.load(f)
    except Exception as e:
        print(f"Error loading products database: {e}")
        return None
        
    if not products:
        return None
        
    # Case 1: Custom topic is provided. Try to match a product name or category.
    if topic:
        topic_lower = topic.lower()
        for p in products:
            if topic_lower in p["name"].lower() or p["category"].lower() in topic_lower:
                print(f"Matched custom topic to product pool: '{p['name']}'")
                return p
        # If no match is found, we return None and generate a script based on the custom topic directly.
        return None
        
    # Case 2: No custom topic. Select randomly with history tracking.
    history_file = "history.json"
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
            
    # Filter products that are not in history
    available = [p for p in products if p["name"] not in history]
    
    # If all products have been used, reset history
    if not available:
        print("All products in pool have been used. Resetting history...")
        history = []
        available = products
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not reset history.json: {e}")
        
    selected = random.choice(available)
    
    print(f"Selected product from pool: '{selected['name']}'")
    return selected

def download_from_bing(query, folder):
    """Searches Bing Images for the product name, downloads up to 4 scaled-up thumbnails, and saves them."""
    print(f"Attempting to download product photos from Bing Images for: '{query}'...")
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    downloaded_images = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"  Bing search failed (Status Code {r.status_code})")
            return []
            
        turls = re.findall(r'&quot;turl&quot;:&quot;(https://.+?)&quot;', r.text)
        unique_turls = list(set(turls))
        print(f"  Found {len(unique_turls)} unique image thumbnails on Bing.")
        
        for t in unique_turls:
            if len(downloaded_images) >= 4:
                break
            t_clean = t.replace("&amp;", "&")
            m_id = re.search(r'id=([^&]+)', t_clean)
            if m_id:
                img_id = m_id.group(1)
                large_url = f"https://ts1.mm.bing.net/th?id={img_id}&w=600&h=600&rs=1&pid=ImgDet"
                try:
                    r_img = requests.get(large_url, headers=headers, timeout=5)
                    if r_img.status_code == 200 and len(r_img.content) > 1000:
                        downloaded_images.append(r_img.content)
                        print(f"  Successfully downloaded Bing thumbnail #{len(downloaded_images)}")
                except Exception:
                    pass
        return downloaded_images
    except Exception as e:
        print(f"  Warning: Error searching Bing: {e}")
        return []

def download_product_images(product):
    """Downloads actual product images from Amazon or Bing (using ASIN and search) and falls back to Pexels if needed."""
    product_name = product["name"]
    category = product["category"]
    affiliate_link = product["affiliate_link"]
    
    slug = slugify(product_name)
    folder = os.path.join("product_images", slug)
    
    # Check if we already have images
    if os.path.exists(folder):
        if os.path.exists(os.path.join(folder, ".manual")):
            print("Manual override detected ('.manual' file present). Skipping download.")
            return True
        existing_images = [
            f for f in os.listdir(folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ]
        if os.path.exists(os.path.join(folder, ".actual_focus")) and len(existing_images) == 4:
            print(f"Product images folder already has {len(existing_images)} focused images. Skipping download.")
            return True
            
    os.makedirs(folder, exist_ok=True)
    print(f"Downloading product photos for '{product_name}' to '{folder}'...")
    
    downloaded_count = 0
    actual_images = []
    
    # 1. Try to extract ASIN and download actual product photos from Amazon
    asin = None
    match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', affiliate_link)
    if match:
        asin = match.group(1)
        
    if asin:
        print(f"Attempting to download actual product photos from Amazon (ASIN: {asin})...")
        suffixes = [
            "LZZZZZZZ",  # Main image
            "PT01.LZZZZZZZ",
            "PT02.LZZZZZZZ",
            "PT03.LZZZZZZZ",
            "PT04.LZZZZZZZ",
            "PT05.LZZZZZZZ",
            "PT06.LZZZZZZZ"
        ]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        for suffix in suffixes:
            amazon_img_url = f"https://images.amazon.com/images/P/{asin}.01.{suffix}.jpg"
            try:
                r = requests.get(amazon_img_url, headers=headers, timeout=10)
                if r.status_code == 200 and len(r.content) > 1000:
                    actual_images.append(r.content)
                    print(f"  Successfully fetched actual Amazon product image with suffix: {suffix}")
                    if len(actual_images) >= 4:
                        break
            except Exception as e:
                print(f"  Warning: Error fetching suffix {suffix}: {e}")
                
    # 2. Try Bing Images search if Amazon returned no images (for Flipkart or unindexed Amazon products)
    if not actual_images:
        actual_images = download_from_bing(product_name, folder)
        
    # 3. If actual images were retrieved (Amazon or Bing), distribute to slides
    if actual_images:
        # Clean folder first to avoid leftover images
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
                    
        # Distribute images to create exactly 1.jpg, 2.jpg, 3.jpg, 4.jpg
        num_fetched = len(actual_images)
        for slide_idx in range(1, 5):
            img_content = actual_images[(slide_idx - 1) % num_fetched]
            out_path = os.path.join(folder, f"{slide_idx}.jpg")
            with open(out_path, "wb") as f:
                f.write(img_content)
            print(f"  Saved slide {slide_idx}: {out_path}")
            downloaded_count += 1
            
        # Create the .actual_focus marker file
        with open(os.path.join(folder, ".actual_focus"), "w") as f:
            f.write("actual_focus")
            
    # 4. Fallback: If Amazon and Bing both failed, try to get general photos from Pexels
    if downloaded_count == 0:
        pexels_key = os.environ.get("PEXELS_API_KEY")
        if pexels_key:
            print(f"Fallback: Querying Pexels Photo API for category: '{category}'...")
            try:
                r = requests.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": pexels_key},
                    params={"query": category, "orientation": "portrait", "per_page": 8},
                    timeout=10
                )
                if r.status_code == 200:
                    data = r.json()
                    photos = data.get("photos", [])
                    
                    # Clean folder first
                    for f in os.listdir(folder):
                        file_path = os.path.join(folder, f)
                        if os.path.isfile(file_path):
                            try:
                                os.remove(file_path)
                            except Exception:
                                pass
                                
                    slide_idx = 1
                    for p in photos:
                        if slide_idx > 4:
                            break
                        img_url = p.get("src", {}).get("large")
                        if not img_url:
                            continue
                        try:
                            r_img = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                            if r_img.status_code == 200:
                                out_path = os.path.join(folder, f"{slide_idx}.jpg")
                                with open(out_path, "wb") as f:
                                    f.write(r_img.content)
                                print(f"  Downloaded fallback slide {slide_idx}: {out_path}")
                                downloaded_count += 1
                                slide_idx += 1
                        except Exception:
                            pass
                else:
                    print(f"Pexels search failed (Status Code {r.status_code})")
            except Exception as e:
                print(f"Warning: Could not fetch Pexels photos: {e}")
                
    print(f"Download process finished. Total images in folder: {downloaded_count}")
    return downloaded_count > 0


def generate_script(api_key, topic=None, product=None):
    """Call Gemini 2.5 Flash to generate a structured coding tip or product review script in JSON format."""
    print("Connecting to Google Gemini API...")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    if product:
        # Build prompt for a product review / recommendation
        points_str = "\n".join([f"- {p}" for p in product.get("selling_points", [])])
        prompt = (
            f"Write a highly engaging 30-second product recommendation review script suitable for an Instagram Reel. "
            f"The product name is: '{product['name']}'.\n"
            f"Key features and selling points to highlight:\n{points_str}\n\n"
            "The script must start with an attention-grabbing hook, highlight 2 key benefits of the product, "
            "and end with a verbal call-to-action: 'Link in bio to check it out!' "
            "The voiceover text (script_text) must be natural, fast-paced, and easy to read aloud under 30 seconds (about 60-80 words maximum). "
            "Do not include any sound effects, placeholders, or scene descriptions in the script_text—only the exact words that should be spoken. "
            "Provide a short, catchy title. "
            "Provide an Instagram caption directing viewers to click the link in our bio to buy, with hashtags."
        )
    else:
        # Generic fallback prompt
        if topic:
            topic_clause = f"The video should focus on the topic: '{topic}'."
        else:
            topic_clause = "The video should focus on a random useful programming tip, language feature, clean coding trick, or software engineering concept."
            
        prompt = (
            f"Write a highly engaging 30-second coding tip, trick, or concept overview suitable for an Instagram Reel. "
            f"{topic_clause} "
            "The voiceover text (script_text) must be natural, fast-paced, and easy to read aloud under 30 seconds (about 60-80 words maximum). "
            "Do not include any sound effects, placeholders, or scene descriptions in the script_text—only the exact words that should be spoken. "
            "Provide an attention-grabbing title. "
            "Provide a compelling Instagram caption complete with relevant tech and coding hashtags."
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
                "type": "OBJECT",
                "properties": {
                    "title": {
                        "type": "STRING", 
                        "description": "Short, catchy title for the coding tip or product."
                    },
                    "script_text": {
                        "type": "STRING", 
                        "description": "The exact voiceover script to be spoken, with no markdown, parenthetical instructions, or tags. Max 80 words."
                    },
                    "caption": {
                        "type": "STRING", 
                        "description": "Instagram post description text with hashtags."
                    }
                },
                "required": ["title", "script_text", "caption"]
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            print(f"Error calling Gemini API (Status Code {response.status_code}):")
            print(response.text)
            return None
            
        data = response.json()
        
        candidates = data.get("candidates", [])
        if not candidates:
            print("No response candidate returned from Gemini.")
            return None
            
        text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text")
        if not text_content:
            print("Failed to extract text content from response.")
            return None
            
        script_data = json.loads(text_content.strip())
        return script_data
        
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse model's JSON response: {e}")
        print("Raw text returned:")
        print(text_content)
        return None

def main():
    print("=== ReelFlow Script Generator ===")
    
    # 1. Load configuration
    if not load_env():
        print("Error: '.env' file not found. Please set up your .env file first.")
        sys.exit(1)
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or "your_copied_gemini_key" in api_key:
        print("Error: GEMINI_API_KEY is not configured in your '.env' file.")
        sys.exit(1)
        
    # 2. Parse arguments & select product
    topic = None
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
        print(f"Custom topic/product input: '{topic}'")
        
    # Try selecting a product from products.json
    product = select_product(topic)
    
    # 3. Download images and call the generator
    if product:
        download_product_images(product)
        script_data = generate_script(api_key, product=product)
    else:
        script_data = generate_script(api_key, topic=topic)
        
    if not script_data:
        print("Script generation failed.")
        sys.exit(1)
        
    # 4. Inject product metadata into the output script dictionary if applicable
    if product:
        script_data["product_name"] = product["name"]
        script_data["product_category"] = product["category"]
        
        aff_link = product["affiliate_link"]
        associate_tag = os.environ.get("AMAZON_ASSOCIATE_TAG")
        if associate_tag and associate_tag.strip():
            aff_link = re.sub(r'tag=[^&]+', f'tag={associate_tag.strip()}', aff_link)
            
        flipkart_tag = os.environ.get("FLIPKART_AFFILIATE_ID")
        if flipkart_tag and flipkart_tag.strip():
            aff_link = re.sub(r'affid=[^&]+', f'affid={flipkart_tag.strip()}', aff_link)
            
        script_data["affiliate_link"] = aff_link
        # Customize the caption to append the specific affiliate link CTA
        cta_text = f"\n\n👉 Get it here: {aff_link}\n(Link also in bio!)"
        script_data["caption"] = script_data.get("caption", "") + cta_text
    else:
        script_data["product_name"] = None
        script_data["product_category"] = "coding"
        script_data["affiliate_link"] = None
        
    # 5. Print verification info
    print("\n--- Generated Content ---")
    print(f"Title:   {script_data.get('title')}")
    print(f"Script:  {script_data.get('script_text')}")
    print(f"Caption: {script_data.get('caption')}")
    if product:
        print(f"Product: {script_data.get('product_name')} ({script_data.get('product_category')})")
    print("-------------------------\n")
    
    # 6. Save to script.json
    output_file = "script.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully saved generated script to: {output_file}")

if __name__ == "__main__":
    main()
