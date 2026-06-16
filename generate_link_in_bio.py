import os
import json
import re
import urllib.parse

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

def sanitize_link(link):
    """Dynamically replaces Amazon tags and Flipkart ids with the correct ones from .env."""
    if not link:
        return link
    
    # Check for Amazon
    if "amazon" in link.lower():
        associate_tag = os.environ.get("AMAZON_ASSOCIATE_TAG")
        if associate_tag and associate_tag.strip():
            if "tag=" in link:
                link = re.sub(r'tag=[^&]*', f'tag={associate_tag.strip()}', link)
            else:
                connector = "&" if "?" in link else "?"
                link = f"{link}{connector}tag={associate_tag.strip()}"
                
    # Check for Flipkart
    elif "flipkart" in link.lower():
        flipkart_tag = os.environ.get("FLIPKART_AFFILIATE_ID")
        if flipkart_tag and flipkart_tag.strip():
            if "affid=" in link:
                link = re.sub(r'affid=[^&]*', f'affid={flipkart_tag.strip()}', link)
            else:
                connector = "&" if "?" in link else "?"
                link = f"{link}{connector}affid={flipkart_tag.strip()}"
            
    return link

def slugify(text):
    """Converts product name into a standard lowercase directory name."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')

def load_data():
    db_file = "products.json"
    history_file = "history.json"
    
    products = []
    if os.path.exists(db_file):
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                products = json.load(f)
        except Exception as e:
            print(f"Error loading products database: {e}")
            
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
            
    return products, history

def main():
    print("=== Generating Link-in-Bio Landing Page ===")
    load_env()
    products, history = load_data()
    
    if not products:
        print("No products available to generate page.")
        return
        
    # Map products by name for easy lookup
    prod_map = {p["name"]: p for p in products}
    
    # Identify featured product based on history (most recent)
    featured = None
    reversed_history = list(reversed(history))
    active_history = [name for name in reversed_history if name in prod_map]
    
    if active_history:
        featured_name = active_history[0]
        featured = prod_map[featured_name].copy()
        featured["affiliate_link"] = sanitize_link(featured["affiliate_link"])
    else:
        # Fallback to the first product if history is empty
        featured = products[0].copy()
        featured["affiliate_link"] = sanitize_link(featured["affiliate_link"])

    # Prepare categories and their display names / description / first image
    categories_data = {}
    for p in products:
        cat = p["category"]
        p_slug = slugify(p["name"])
        
        # Check if local image exists, otherwise fallback
        img_path = f"product_images/{p_slug}/1.jpg"
        if not os.path.exists(img_path):
            if os.path.exists(f"product_images/{p_slug}/1.png"):
                img_path = f"product_images/{p_slug}/1.png"
            else:
                img_path = "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=150"
                
        if cat not in categories_data:
            display_name = cat.title()
            categories_data[cat] = {
                "name": display_name,
                "desc": f"Compare and buy best {cat.lower()} online",
                "image": img_path
            }

    # Format products array for JavaScript client-side filtering
    js_products = []
    for p in products:
        p_copy = p.copy()
        p_copy["affiliate_link"] = sanitize_link(p_copy["affiliate_link"])
        p_slug = slugify(p_copy["name"])
        
        # Resolve image path
        img_path = f"product_images/{p_slug}/1.jpg"
        if not os.path.exists(img_path):
            if os.path.exists(f"product_images/{p_slug}/1.png"):
                img_path = f"product_images/{p_slug}/1.png"
            else:
                img_path = "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=500"
                
        price = p_copy.get("price", 999)
        orig_price = p_copy.get("original_price", 1999)
        discount_pct = round((1 - price / orig_price) * 100)
        
        # Formulate WhatsApp Message
        whatsapp_msg = f"🔥 Check out this amazing deal on the {p_copy['name']}! Only ₹{price:,} ({discount_pct}% OFF) 👉 {p_copy['affiliate_link']}"
        whatsapp_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(whatsapp_msg)}"
        
        js_products.append({
            "name": p_copy["name"],
            "category": p_copy["category"],
            "affiliate_link": p_copy["affiliate_link"],
            "price": price,
            "original_price": orig_price,
            "image": img_path,
            "whatsapp_url": whatsapp_url,
            "selling_points": p_copy.get("selling_points", [])
        })

    # Generate Category Select Options HTML
    category_options_html = ""
    for cat_slug, cat_info in categories_data.items():
        category_options_html += f'<option value="{cat_slug}">{cat_info["name"]}</option>\n'

    # Generate Category Grid HTML
    category_grid_html = ""
    for cat_slug, cat_info in categories_data.items():
        category_grid_html += f"""
        <div class="category-card" data-category="{cat_slug}" onclick="selectCategory('{cat_slug}')">
            <div class="category-info">
                <h3>{cat_info['name']}</h3>
                <p>{cat_info['desc']}</p>
                <span class="show-prices">Show me Prices</span>
            </div>
            <div class="category-img">
                <img src="{cat_info['image']}" alt="{cat_info['name']}" />
            </div>
        </div>
        """

    # Grab images for the top 3 products in products.json to display in the hero banner
    hero_images = []
    for p in products[:3]:
        p_slug = slugify(p["name"])
        img_path = f"product_images/{p_slug}/1.jpg"
        if not os.path.exists(img_path):
            if os.path.exists(f"product_images/{p_slug}/1.png"):
                img_path = f"product_images/{p_slug}/1.png"
            else:
                img_path = "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=150"
        hero_images.append(img_path)
    
    # Pad if less than 3
    while len(hero_images) < 3:
        hero_images.append("https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=150")

    # Generate Featured Card HTML
    featured_slug = slugify(featured["name"])
    featured_img = f"product_images/{featured_slug}/1.jpg"
    if not os.path.exists(featured_img):
        if os.path.exists(f"product_images/{featured_slug}/1.png"):
            featured_img = f"product_images/{featured_slug}/1.png"
        else:
            featured_img = "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=500"
            
    featured_cta = "Shop on Flipkart" if "flipkart" in featured["affiliate_link"] else "Shop on Amazon"
    f_price = featured.get("price", 999)
    f_orig = featured.get("original_price", 1999)
    f_discount = round((1 - f_price / f_orig) * 100)
    
    f_whatsapp_msg = f"🔥 Check out this amazing deal on the {featured['name']}! Only ₹{f_price:,} ({f_discount}% OFF) 👉 {featured['affiliate_link']}"
    f_whatsapp_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(f_whatsapp_msg)}"
    
    selling_points_html = "".join([f"<li>{sp}</li>" for sp in featured.get("selling_points", [])])

    featured_html = f"""
    <div class="featured-section">
        <h2 class="featured-heading">⚡ Deal of the Day</h2>
        <div class="featured-card">
            <span class="featured-badge">Featured Deal</span>
            <div class="featured-img-wrapper">
                <img src="{featured_img}" alt="{featured['name']}" />
            </div>
            <div class="featured-details">
                <span class="featured-category">{featured['category'].upper()}</span>
                <h3 class="featured-title">{featured['name']}</h3>
                
                <div class="price-container">
                    <span class="current-price">₹{f_price:,}</span>
                    <span class="original-price">₹{f_orig:,}</span>
                    <span class="discount-badge">{f_discount}% OFF</span>
                </div>

                <div class="countdown-container">
                    <span class="countdown-label">Deal resets in:</span>
                    <div id="countdown-timer" class="countdown-timer">--:--:--</div>
                </div>

                <ul class="featured-bullets">
                    {selling_points_html}
                </ul>

                <div class="btn-group">
                    <a href="{featured['affiliate_link']}" target="_blank" class="cta-btn">{featured_cta}</a>
                    <a href="{f_whatsapp_url}" target="_blank" class="share-btn">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style="vertical-align: middle; margin-right: 6px;"><path d="M12.012 2c-5.506 0-9.989 4.478-9.99 9.984a9.96 9.96 0 0 0 1.333 4.982L2 22l5.233-1.371a9.994 9.994 0 0 0 4.779 1.207h.004c5.505 0 9.988-4.478 9.99-9.984a9.988 9.988 0 0 0-2.927-7.062A9.957 9.957 0 0 0 12.012 2zm5.726 14.184c-.314.88-1.547 1.62-2.126 1.716-.52.087-1.196.115-1.928-.118a10.038 10.038 0 0 1-4.08-2.616 10.835 10.835 0 0 1-2.336-3.876c-.47-.798-.79-1.688-.813-2.618-.027-1.12.55-1.668.783-1.89.232-.224.51-.285.68-.285.17 0 .34.007.49.015.158.007.37-.06.577.447.21.517.72 1.76.783 1.894.064.133.106.29.015.474-.092.186-.14.293-.277.458-.137.164-.287.365-.41.49-.137.137-.28.286-.12.56.16.273.71 1.173 1.523 1.896.7.625 1.29.82 1.472.91.18.093.287.077.394-.047.106-.123.46-.534.582-.717.123-.183.245-.152.41-.09.165.06 1.048.494 1.226.584.177.09.296.136.34.21.044.075.044.436-.27 1.317z"/></svg>
                        Share Deal
                    </a>
                </div>
            </div>
        </div>
    </div>
    """

    # HTML Output Construction
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ReelFlow Tech Deals - Shop and Compare</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary-red: #e31e24;
            --navy-blue: #0b3c5d;
            --dark-blue: #002244;
            --light-bg: #f4f6f9;
            --border-color: #e5e5e5;
            --text-color: #333333;
            --text-muted: #777777;
            --accent-green: #39b54a;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Outfit', sans-serif;
        }}

        body {{
            background-color: var(--light-bg);
            color: var(--text-color);
            line-height: 1.5;
        }}

        /* Header Layout */
        .site-header {{
            background: #ffffff;
            border-bottom: 1px solid var(--border-color);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }}

        .brand-section {{
            display: flex;
            align-items: center;
            gap: 8px;
            text-decoration: none;
        }}

        .brand-logo-icon {{
            font-size: 1.8rem;
            animation: rotateReel 8s infinite linear;
            display: inline-block;
        }}

        @keyframes rotateReel {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}

        .brand-name {{
            font-size: 1.6rem;
            font-weight: 800;
            color: var(--primary-red);
            letter-spacing: -0.5px;
        }}

        /* Search Bar & Categories Dropdown */
        .search-container {{
            display: flex;
            align-items: center;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: #ffffff;
            overflow: hidden;
            width: 100%;
            max-width: 550px;
            margin: 0 20px;
        }}

        .search-input {{
            border: none;
            padding: 10px 15px;
            font-size: 0.9rem;
            outline: none;
            flex-grow: 1;
            width: 100%;
        }}

        .category-select-dropdown {{
            border: none;
            border-left: 1px solid var(--border-color);
            padding: 10px;
            font-size: 0.85rem;
            outline: none;
            background: #fdfdfd;
            cursor: pointer;
            color: var(--text-color);
        }}

        .search-btn {{
            background: #111111;
            color: #ffffff;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            transition: background 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .search-btn:hover {{
            background: var(--primary-red);
        }}

        /* Header Utility Icons */
        .header-utilities {{
            display: flex;
            align-items: center;
            gap: 24px;
        }}

        .utility-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            color: var(--text-color);
            text-decoration: none;
            font-size: 0.75rem;
            font-weight: 600;
            position: relative;
            cursor: pointer;
            transition: color 0.2s ease;
        }}

        .utility-item:hover {{
            color: var(--primary-red);
        }}

        .utility-icon-box {{
            position: relative;
            margin-bottom: 2px;
        }}

        .utility-badge {{
            position: absolute;
            top: -6px;
            right: -10px;
            background: var(--primary-red);
            color: #ffffff;
            font-size: 0.65rem;
            font-weight: bold;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        /* Red Navigation Bar */
        .navigation-bar {{
            background: var(--primary-red);
            color: #ffffff;
            padding: 0 30px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 44px;
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .nav-links {{
            display: flex;
            gap: 24px;
            list-style: none;
        }}

        .nav-links a {{
            color: #ffffff;
            text-decoration: none;
            transition: opacity 0.2s ease;
        }}

        .nav-links a:hover {{
            opacity: 0.8;
        }}

        .wishlist-link-right {{
            color: #ffffff;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        /* Hero Section */
        .hero-banner {{
            background: linear-gradient(135deg, var(--navy-blue) 0%, var(--dark-blue) 100%);
            color: #ffffff;
            padding: 50px 30px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: 320px;
            overflow: hidden;
            position: relative;
        }}

        .hero-banner::after {{
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            background-image: radial-gradient(circle at 90% 50%, rgba(255, 255, 255, 0.05) 0%, transparent 60%);
            pointer-events: none;
        }}

        .hero-content {{
            max-width: 600px;
            z-index: 10;
        }}

        .hero-badge-container {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }}

        .hero-tagline {{
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 8px;
        }}

        .hero-subtitle {{
            font-size: 1.15rem;
            color: #a5d8ff;
            margin-bottom: 12px;
            font-weight: 400;
        }}

        .hero-desc {{
            font-size: 0.9rem;
            color: #ced4da;
            margin-bottom: 24px;
            line-height: 1.6;
        }}

        .hero-btn {{
            background: var(--accent-green);
            color: #ffffff;
            border: none;
            padding: 12px 28px;
            font-size: 0.95rem;
            font-weight: 700;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 4px 15px rgba(57, 181, 74, 0.4);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .hero-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(57, 181, 74, 0.6);
            filter: brightness(1.05);
        }}

        .hero-graphics {{
            display: flex;
            gap: 15px;
            align-items: center;
            position: relative;
            z-index: 5;
        }}

        .graphic-hexagon-card {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.15);
            width: 110px;
            height: 110px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 18px;
            transform: rotate(-10deg);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(4px);
            transition: all 0.3s ease;
        }}

        .graphic-hexagon-card img {{
            width: 80%;
            height: 80%;
            object-fit: contain;
            filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.2));
        }}

        .graphic-hexagon-card:hover {{
            transform: rotate(0deg) scale(1.1);
            border-color: rgba(255, 255, 255, 0.3);
        }}

        /* Grid Category Header */
        .section-header {{
            text-align: center;
            margin: 40px 0 25px 0;
            font-size: 1.6rem;
            font-weight: 800;
            color: #111111;
        }}

        /* Choose Category Grid */
        .category-container-grid {{
            max-width: 1200px;
            margin: 0 auto 30px auto;
            padding: 0 20px;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 20px;
        }}

        .category-card {{
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .category-card:hover {{
            transform: translateY(-2px);
            border-color: var(--primary-red);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.05);
        }}

        .category-card.active {{
            border-color: var(--primary-red);
            background: rgba(227, 30, 36, 0.02);
            box-shadow: 0 8px 24px rgba(227, 30, 36, 0.05);
        }}

        .category-info {{
            display: flex;
            flex-direction: column;
            gap: 4px;
            flex-grow: 1;
            padding-right: 10px;
        }}

        .category-info h3 {{
            font-size: 1.05rem;
            font-weight: 700;
            color: #111111;
        }}

        .category-info p {{
            font-size: 0.75rem;
            color: var(--text-muted);
            line-height: 1.3;
        }}

        .category-info .show-prices {{
            font-size: 0.8rem;
            font-weight: 700;
            color: #ff6600;
            margin-top: 6px;
            text-decoration: none;
            transition: color 0.2s ease;
        }}

        .category-card:hover .show-prices {{
            color: var(--primary-red);
            text-decoration: underline;
        }}

        .category-img {{
            width: 65px;
            height: 65px;
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            background: #fafafa;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .category-img img {{
            width: 90%;
            height: 90%;
            object-fit: contain;
        }}

        /* Sub-hero counter */
        .subhero-counter-container {{
            max-width: 1200px;
            margin: 20px auto;
            padding: 0 20px;
        }}

        .subhero-counter-box {{
            background: #ffffff;
            border: 1px solid var(--border-color);
            padding: 12px 20px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 1.05rem;
            color: #333333;
            display: inline-block;
        }}

        .subhero-counter-box mark {{
            background: #fff3cd;
            color: #856404;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 700;
        }}

        /* Layout Grid Container */
        .storefront-layout {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px 60px 20px;
            display: grid;
            grid-template-columns: 2.2fr 1fr;
            gap: 30px;
        }}

        /* Left Side: Product catalog */
        .catalog-container {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .product-grid-catalog {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
            gap: 20px;
            width: 100%;
        }}

        .product-card-item {{
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: all 0.2s ease;
        }}

        .product-card-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
            border-color: #d1d1d1;
        }}

        .product-card-img-wrapper {{
            width: 100%;
            height: 180px;
            padding: 10px;
            background: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            border-bottom: 1px solid var(--border-color);
            position: relative;
        }}

        .product-card-img-wrapper img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }}

        .card-disc-tag {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: var(--primary-red);
            color: #ffffff;
            font-size: 0.7rem;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(227, 30, 36, 0.25);
        }}

        .product-card-content {{
            padding: 15px;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
            gap: 8px;
        }}

        .product-card-category {{
            font-size: 0.7rem;
            font-weight: 700;
            color: var(--text-muted);
            letter-spacing: 0.5px;
        }}

        .product-card-title {{
            font-size: 0.9rem;
            font-weight: 700;
            color: #111111;
            line-height: 1.35;
            height: 38px;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }}

        .product-card-pricing {{
            display: flex;
            align-items: baseline;
            gap: 8px;
            margin: 4px 0;
        }}

        .product-card-price {{
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--primary-red);
        }}

        .product-card-original {{
            font-size: 0.85rem;
            color: var(--text-muted);
            text-decoration: line-through;
        }}

        .product-card-actions {{
            display: flex;
            gap: 8px;
            margin-top: auto;
        }}

        .product-card-btn {{
            flex-grow: 1;
            background: var(--navy-blue);
            color: #ffffff;
            text-decoration: none;
            padding: 8px 10px;
            border-radius: 4px;
            text-align: center;
            font-size: 0.8rem;
            font-weight: 700;
            transition: background 0.2s ease;
        }}

        .product-card-btn:hover {{
            background: var(--dark-blue);
        }}

        .product-card-share {{
            background: rgba(37, 211, 102, 0.1);
            color: #25d366;
            border: 1px solid rgba(37, 211, 102, 0.2);
            width: 34px;
            height: 34px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            transition: all 0.2s ease;
        }}

        .product-card-share:hover {{
            background: rgba(37, 211, 102, 0.2);
            transform: scale(1.05);
        }}

        /* Right Side: Featured Widget */
        .featured-widget-area {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .featured-section {{
            position: sticky;
            top: 90px;
        }}

        .featured-heading {{
            font-size: 1.2rem;
            font-weight: 800;
            color: #111111;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* Featured Card Aesthetics */
        .featured-card {{
            background: #ffffff;
            border: 2px solid var(--primary-red);
            border-radius: 8px;
            padding: 20px;
            position: relative;
            box-shadow: 0 8px 24px rgba(227, 30, 36, 0.05);
        }}

        .featured-badge {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: var(--primary-red);
            color: #ffffff;
            font-size: 0.65rem;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 4px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}

        .featured-img-wrapper {{
            width: 100%;
            height: 180px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #ffffff;
            margin-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }}

        .featured-img-wrapper img {{
            max-width: 90%;
            max-height: 90%;
            object-fit: contain;
        }}

        .featured-details {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .featured-category {{
            font-size: 0.7rem;
            font-weight: 800;
            color: var(--primary-red);
            letter-spacing: 0.5px;
        }}

        .featured-title {{
            font-size: 1.15rem;
            font-weight: 800;
            color: #111111;
            line-height: 1.3;
        }}

        .price-container {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 4px 0;
        }}

        .current-price {{
            font-size: 1.6rem;
            font-weight: 800;
            color: var(--primary-red);
        }}

        .original-price {{
            font-size: 1rem;
            color: var(--text-muted);
            text-decoration: line-through;
        }}

        .discount-badge {{
            background: #fff0f0;
            color: var(--primary-red);
            border: 1px solid rgba(227, 30, 36, 0.2);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 800;
        }}

        .countdown-container {{
            background: #fdf2f2;
            border: 1px solid rgba(227, 30, 36, 0.1);
            border-radius: 6px;
            padding: 8px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }}

        .countdown-label {{
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .countdown-timer {{
            font-family: monospace;
            font-size: 0.9rem;
            font-weight: 800;
            color: var(--primary-red);
        }}

        .featured-bullets {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin: 5px 0 15px 0;
        }}

        .featured-bullets li {{
            font-size: 0.8rem;
            color: #555555;
            padding-left: 18px;
            position: relative;
        }}

        .featured-bullets li::before {{
            content: '⚡';
            position: absolute;
            left: 0;
            color: var(--primary-red);
            font-size: 0.8rem;
        }}

        .btn-group {{
            display: flex;
            gap: 10px;
        }}

        .cta-btn {{
            flex-grow: 1;
            background: var(--primary-red);
            color: #ffffff;
            text-decoration: none;
            padding: 10px 15px;
            border-radius: 4px;
            text-align: center;
            font-size: 0.85rem;
            font-weight: 800;
            transition: background 0.2s ease;
            box-shadow: 0 4px 12px rgba(227, 30, 36, 0.2);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .cta-btn:hover {{
            background: #b81418;
        }}

        .share-btn {{
            background: rgba(37, 211, 102, 0.1);
            color: #25d366;
            border: 1px solid rgba(37, 211, 102, 0.2);
            padding: 10px 15px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 0.8rem;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }}

        .share-btn:hover {{
            background: rgba(37, 211, 102, 0.2);
        }}

        /* Empty State */
        .no-results {{
            grid-column: 1 / -1;
            text-align: center;
            padding: 40px 20px;
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-muted);
            font-weight: 600;
        }}

        /* Footer */
        .site-footer {{
            background: #ffffff;
            border-top: 1px solid var(--border-color);
            text-align: center;
            padding: 30px;
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: auto;
        }}

        .site-footer a {{
            color: var(--primary-red);
            text-decoration: none;
            font-weight: 600;
        }}

        /* Responsive Design */
        @media (max-width: 968px) {{
            .storefront-layout {{
                grid-template-columns: 1fr;
            }}
            .site-header {{
                flex-direction: column;
                gap: 15px;
                padding: 15px;
            }}
            .search-container {{
                margin: 0;
            }}
            .hero-banner {{
                flex-direction: column;
                gap: 30px;
                text-align: center;
                padding: 40px 20px;
            }}
            .hero-graphics {{
                justify-content: center;
            }}
            .featured-section {{
                position: static;
            }}
        }}

        @media (max-width: 576px) {{
            .category-container-grid {{
                grid-template-columns: 1fr;
            }}
            .product-grid-catalog {{
                grid-template-columns: 1fr;
            }}
            .header-utilities {{
                display: none;
            }}
            .navigation-bar {{
                font-size: 0.75rem;
                padding: 0 15px;
            }}
            .nav-links {{
                gap: 12px;
            }}
        }}
    </style>
</head>
<body>

    <!-- Top Sticky Header -->
    <header class="site-header">
        <a href="https://vpk-git.github.io/ReelFlow/" class="brand-section">
            <span class="brand-logo-icon">⚙️</span>
            <span class="brand-name">ReelFlow</span>
        </a>

        <!-- Search Bar with categories dropdown -->
        <div class="search-container">
            <input type="text" id="search-input" class="search-input" placeholder="Search product name, category, or features..." oninput="handleSearch()" />
            <select id="category-select" class="category-select-dropdown" onchange="handleSearch()">
                <option value="all">All Categories</option>
                {category_options_html}
            </select>
            <button class="search-btn" onclick="handleSearch()">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            </button>
        </div>

        <!-- Search Bar with categories dropdown -->
        <div class="search-container" style="max-width: 650px; margin-right: 0;">
            <input type="text" id="search-input" class="search-input" placeholder="Search product name, category, or features..." oninput="handleSearch()" />
            <select id="category-select" class="category-select-dropdown" onchange="handleSearch()">
                <option value="all">All Categories</option>
                {category_options_html}
            </select>
            <button class="search-btn" onclick="handleSearch()">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            </button>
        </div>
    </header>

    <!-- Crimson Navigation Bar -->
    <nav class="navigation-bar">
        <ul class="nav-links">
            <li><a href="#catalog-section" onclick="selectCategory('all')">All Deals</a></li>
            <li><a href="#catalog-section" onclick="scrollToCatalog()">Deals Catalog</a></li>
        </ul>
    </nav>

    <!-- Hero Banner (Rewise Style) -->
    <section class="hero-banner">
        <div class="hero-content">
            <div class="hero-badge-container">
                <span style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; letter-spacing: 1px; text-transform: uppercase;">⚡ Live Comparison Portal</span>
            </div>
            <h1 class="hero-tagline">Let's Compare</h1>
            <p class="hero-subtitle">Shop wise with verified pricing from ReelFlow</p>
            <p class="hero-desc">Check out handpicked Indian electronics deals with active discount percentages, deal countdown timers, and quick WhatsApp sharing.</p>
            <button class="hero-btn" onclick="scrollToCatalog()">Explore Deals</button>
        </div>
        <div class="hero-graphics">
            <!-- 3 actual product graphic cards -->
            <div class="graphic-hexagon-card">
                <img src="{hero_images[0]}" alt="Top Gadget 1" />
            </div>
            <div class="graphic-hexagon-card" style="transform: rotate(15deg); margin-top: 25px;">
                <img src="{hero_images[1]}" alt="Top Gadget 2" />
            </div>
            <div class="graphic-hexagon-card" style="transform: rotate(-5deg); margin-top: -20px;">
                <img src="{hero_images[2]}" alt="Top Gadget 3" />
            </div>
        </div>
    </section>

    <!-- Grid Category Section -->
    <h2 class="section-header">Choose Category</h2>
    <section class="category-container-grid">
        {category_grid_html}
    </section>

    <!-- Sub-hero counter -->
    <div class="subhero-counter-container">
        <div class="subhero-counter-box" id="subhero-counter-box">
            ReelFlow - compare prices for <mark><span id="product-count-badge">{len(products)}</span> products</mark>
        </div>
    </div>

    <!-- Main Workspace Layout -->
    <main class="storefront-layout" id="catalog-section">
        <!-- Left Column: Dynamic Catalog -->
        <section class="catalog-container">
            <div class="product-grid-catalog" id="product-grid">
                <!-- Injected via Javascript -->
            </div>
        </section>

        <!-- Right Column: Featured Widget Sticky -->
        <aside class="featured-widget-area">
            {featured_html}
        </aside>
    </main>

    <!-- Footer -->
    <footer class="site-footer">
        <p>© 2026 ReelFlow Automation. Powered by <a href="https://github.com/GoogleDeepMind" target="_blank">Advanced Agentic Coding</a></p>
    </footer>

    <!-- Client-side Search and Filtering Script -->
    <script>
        // Loaded dynamic products array
        const products = {json.dumps(js_products, ensure_ascii=False)};
        
        let activeCategory = 'all';
        let searchQuery = '';

        function renderProducts() {{
            const grid = document.getElementById('product-grid');
            
            const filtered = products.filter(p => {{
                const matchesCategory = activeCategory === 'all' || p.category === activeCategory;
                
                const searchLower = searchQuery.toLowerCase();
                const matchesSearch = searchQuery === '' || 
                                     p.name.toLowerCase().includes(searchLower) ||
                                     p.category.toLowerCase().includes(searchLower) ||
                                     p.selling_points.some(sp => sp.toLowerCase().includes(searchLower));
                                     
                return matchesCategory && matchesSearch;
            }});

            if (filtered.length === 0) {{
                grid.innerHTML = `
                    <div class="no-results">
                        <h3>No deals found</h3>
                        <p style="margin-top: 5px; font-size: 0.85rem;">Try a different keyword or check other categories.</p>
                    </div>
                `;
                document.getElementById('product-count-badge').textContent = '0';
                return;
            }}

            grid.innerHTML = filtered.map(p => {{
                const discount = Math.round((1 - p.price / p.original_price) * 100);
                const ctaText = p.affiliate_link.includes('flipkart.com') || p.affiliate_link.includes('dl.flipkart.com') ? 'Flipkart' : 'Amazon';
                
                return `
                    <div class="product-card-item">
                        <div class="product-card-img-wrapper">
                            <img src="${{p.image}}" alt="${{p.name}}" />
                            <span class="card-disc-tag">${{discount}}% OFF</span>
                        </div>
                        <div class="product-card-content">
                            <span class="product-card-category">${{p.category.toUpperCase()}}</span>
                            <h3 class="product-card-title" title="${{p.name}}">${{p.name}}</h3>
                            <div class="product-card-pricing">
                                <span class="product-card-price">₹${{p.price.toLocaleString('en-IN')}}</span>
                                <span class="product-card-original">₹${{p.original_price.toLocaleString('en-IN')}}</span>
                            </div>
                            <div class="product-card-actions">
                                <a href="${{p.affiliate_link}}" target="_blank" class="product-card-btn">Shop on ${{ctaText}}</a>
                                <a href="${{p.whatsapp_url}}" target="_blank" class="product-card-share" title="Share Deal">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12.012 2c-5.506 0-9.989 4.478-9.99 9.984a9.96 9.96 0 0 0 1.333 4.982L2 22l5.233-1.371a9.994 9.994 0 0 0 4.779 1.207h.004c5.505 0 9.988-4.478 9.99-9.984a9.988 9.988 0 0 0-2.927-7.062A9.957 9.957 0 0 0 12.012 2zm5.726 14.184c-.314.88-1.547 1.62-2.126 1.716-.52.087-1.196.115-1.928-.118a10.038 10.038 0 0 1-4.08-2.616 10.835 10.835 0 0 1-2.336-3.876c-.47-.798-.79-1.688-.813-2.618-.027-1.12.55-1.668.783-1.89.232-.224.51-.285.68-.285.17 0 .34.007.49.015.158.007.37-.06.577.447.21.517.72 1.76.783 1.894.064.133.106.29.015.474-.092.186-.14.293-.277.458-.137.164-.287.365-.41.49-.137.137-.28.286-.12.56.16.273.71 1.173 1.523 1.896.7.625 1.29.82 1.472.91.18.093.287.077.394-.047.106-.123.46-.534.582-.717.123-.183.245-.152.41-.09.165.06 1.048.494 1.226.584.177.09.296.136.34.21.044.075.044.436-.27 1.317z"/></svg>
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            }}).join('');

            document.getElementById('product-count-badge').textContent = filtered.length;
        }}

        function selectCategory(cat) {{
            activeCategory = cat;
            document.getElementById('category-select').value = cat;
            
            // Highlight active grid card
            document.querySelectorAll('.category-card').forEach(card => {{
                if (card.dataset.category === cat) {{
                    card.classList.add('active');
                }} else {{
                    card.classList.remove('active');
                }}
            }});

            renderProducts();
            scrollToCatalog();
        }}

        function handleSearch() {{
            searchQuery = document.getElementById('search-input').value;
            activeCategory = document.getElementById('category-select').value;
            
            // Sync active grid card highlight
            document.querySelectorAll('.category-card').forEach(card => {{
                if (card.dataset.category === activeCategory) {{
                    card.classList.add('active');
                }} else {{
                    card.classList.remove('active');
                }}
            }});

            renderProducts();
        }}

        function scrollToCatalog() {{
            document.getElementById('catalog-section').scrollIntoView({{ behavior: 'smooth' }});
        }}

        // Countdown Timer Logic
        function updateCountdown() {{
            const now = new Date();
            const tomorrow = new Date();
            tomorrow.setHours(24, 0, 0, 0); // Next midnight
            const diff = tomorrow - now;
            
            const hrs = Math.floor(diff / 3600000);
            const mins = Math.floor((diff % 3600000) / 60000);
            const secs = Math.floor((diff % 60000) / 1000);
            
            const timerEl = document.getElementById('countdown-timer');
            if (timerEl) {{
                timerEl.textContent = 
                    `${{hrs.toString().padStart(2, '0')}}h ${{mins.toString().padStart(2, '0')}}m ${{secs.toString().padStart(2, '0')}}s`;
            }}
        }}

        // Initialization
        window.addEventListener('DOMContentLoaded', () => {{
            renderProducts();
            setInterval(updateCountdown, 1000);
            updateCountdown();
        }});
    </script>
</body>
</html>
"""

    output_html_file = "index.html"
    with open(output_html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Successfully generated static Link-in-Bio landing page: {output_html_file}")

if __name__ == "__main__":
    main()
