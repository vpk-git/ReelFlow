import os
import json
import re

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
    
    # Identify featured and previous products based on history
    featured = None
    previous_prods = []
    
    # We want the reverse order of history (most recent first)
    reversed_history = list(reversed(history))
    
    # Find active products from history
    active_history = [name for name in reversed_history if name in prod_map]
    
    if active_history:
        featured_name = active_history[0]
        featured = prod_map[featured_name].copy()
        featured["affiliate_link"] = sanitize_link(featured["affiliate_link"])
        
        # Previous products are the rest of the history
        for name in active_history[1:]:
            p_copy = prod_map[name].copy()
            p_copy["affiliate_link"] = sanitize_link(p_copy["affiliate_link"])
            previous_prods.append(p_copy)
    else:
        # Fallback if history is empty: use first product in products.json as featured
        featured = products[0].copy()
        featured["affiliate_link"] = sanitize_link(featured["affiliate_link"])
        for p in products[1:6]:
            p_copy = p.copy()
            p_copy["affiliate_link"] = sanitize_link(p_copy["affiliate_link"])
            previous_prods.append(p_copy)
        
    # Build the HTML content
    featured_slug = slugify(featured["name"])
    # Check if a custom image exists, otherwise use fallback image path
    featured_img = f"product_images/{featured_slug}/1.jpg"
    if not os.path.exists(featured_img):
        # Check for png
        if os.path.exists(f"product_images/{featured_slug}/1.png"):
            featured_img = f"product_images/{featured_slug}/1.png"
        else:
            featured_img = "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=500" # fallback online image
            
    featured_cta = "Get it on Amazon"
    if "flipkart.com" in featured["affiliate_link"] or "dl.flipkart.com" in featured["affiliate_link"]:
        featured_cta = "Get it on Flipkart"
        
    selling_points_html = "".join([f"<li>{sp}</li>" for sp in featured.get("selling_points", [])])
    
    # Build previous products grid HTML
    prev_grid_html = ""
    for p in previous_prods:
        p_slug = slugify(p["name"])
        p_img = f"product_images/{p_slug}/1.jpg"
        if not os.path.exists(p_img):
            if os.path.exists(f"product_images/{p_slug}/1.png"):
                p_img = f"product_images/{p_slug}/1.png"
            else:
                p_img = "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=500"
                
        p_cta = "Amazon"
        if "flipkart.com" in p["affiliate_link"] or "dl.flipkart.com" in p["affiliate_link"]:
            p_cta = "Flipkart"
            
        prev_grid_html += f"""
        <div class="product-card">
            <div class="card-img-container">
                <img src="{p_img}" alt="{p['name']}" class="card-img" />
            </div>
            <div class="card-content">
                <h3 class="card-title">{p['name']}</h3>
                <p class="card-category">{p['category'].upper()}</p>
                <a href="{p['affiliate_link']}" target="_blank" class="card-btn">Shop on {p_cta}</a>
            </div>
        </div>
        """
        
    # Full page HTML template
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GoalRush Tech Deals - Link in Bio</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0d19;
            --card-bg: rgba(255, 255, 255, 0.05);
            --card-border: rgba(255, 255, 255, 0.08);
            --accent-primary: #8a2be2; /* Electric Purple */
            --accent-secondary: #00f2fe; /* Neon Teal */
            --text-main: #ffffff;
            --text-muted: #a0aec0;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Outfit', sans-serif;
        }}
        
        body {{
            background: radial-gradient(circle at 50% 0%, #1a103c 0%, var(--bg-color) 70%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }}
        
        .container {{
            max-width: 480px;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 30px;
        }}
        
        /* Profile Header */
        header {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
            text-align: center;
        }}
        
        .profile-pic {{
            width: 90px;
            height: 90px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            padding: 3px;
            box-shadow: 0 8px 32px rgba(138, 43, 226, 0.3);
        }}
        
        .profile-pic img {{
            width: 100%;
            height: 100%;
            border-radius: 50%;
            object-fit: cover;
            background: #111;
        }}
        
        .username {{
            font-size: 1.5rem;
            font-weight: 800;
            background: linear-gradient(to right, #ffffff, var(--text-muted));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .bio {{
            font-size: 0.95rem;
            color: var(--text-muted);
            max-width: 320px;
        }}
        
        /* Section Titles */
        .section-title {{
            font-size: 1.1rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 15px;
            color: var(--accent-secondary);
            border-left: 3px solid var(--accent-primary);
            padding-left: 10px;
        }}
        
        /* Featured Product Card */
        .featured-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 24px;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            gap: 20px;
            position: relative;
            overflow: hidden;
        }}
        
        .featured-card::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(0, 242, 254, 0.05) 0%, transparent 60%);
            pointer-events: none;
        }}
        
        .featured-badge {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            padding: 6px 12px;
            border-radius: 50px;
            font-size: 0.75rem;
            font-weight: 800;
            letter-spacing: 1px;
            text-transform: uppercase;
            box-shadow: 0 4px 15px rgba(0, 242, 254, 0.3);
        }}
        
        .featured-img-container {{
            width: 100%;
            height: 240px;
            border-radius: 16px;
            overflow: hidden;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.05);
        }}
        
        .featured-img-container img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            padding: 10px;
        }}
        
        .featured-info {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .featured-title {{
            font-size: 1.4rem;
            font-weight: 800;
            line-height: 1.3;
        }}
        
        .featured-category {{
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--accent-secondary);
            letter-spacing: 1.5px;
        }}
        
        .featured-desc {{
            font-size: 0.95rem;
            color: var(--text-muted);
            line-height: 1.6;
        }}
        
        .featured-points {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 5px;
        }}
        
        .featured-points li {{
            font-size: 0.9rem;
            color: var(--text-muted);
            padding-left: 20px;
            position: relative;
        }}
        
        .featured-points li::before {{
            content: '⚡';
            position: absolute;
            left: 0;
            color: var(--accent-secondary);
        }}
        
        .cta-btn {{
            display: block;
            width: 100%;
            padding: 16px 30px;
            border-radius: 16px;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: #111;
            text-align: center;
            font-weight: 800;
            font-size: 1.05rem;
            text-decoration: none;
            box-shadow: 0 10px 25px rgba(0, 242, 254, 0.25);
            transition: all 0.3s ease;
            position: relative;
            z-index: 2;
        }}
        
        .cta-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 15px 30px rgba(0, 242, 254, 0.4);
        }}
        
        /* Previous Products List */
        .product-list {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        
        .product-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 16px;
            transition: all 0.3s ease;
            text-decoration: none;
            color: inherit;
        }}
        
        .product-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.15);
            background: rgba(255, 255, 255, 0.08);
        }}
        
        .card-img-container {{
            width: 80px;
            height: 80px;
            border-radius: 12px;
            overflow: hidden;
            background: rgba(255,255,255,0.02);
            flex-shrink: 0;
        }}
        
        .card-img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            padding: 5px;
        }}
        
        .card-content {{
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            gap: 4px;
            overflow: hidden;
        }}
        
        .card-title {{
            font-size: 1rem;
            font-weight: 600;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .card-category {{
            font-size: 0.75rem;
            color: var(--accent-secondary);
            font-weight: 600;
            letter-spacing: 1px;
        }}
        
        .card-btn {{
            align-self: flex-start;
            font-size: 0.8rem;
            font-weight: 800;
            color: var(--text-main);
            text-decoration: none;
            border-bottom: 2px solid var(--accent-primary);
            padding-bottom: 2px;
            margin-top: 4px;
        }}
        
        /* Footer */
        footer {{
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 40px;
        }}
        
        footer a {{
            color: var(--accent-secondary);
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div class="profile-pic">
                <img src="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=150" alt="GoalRush" />
            </div>
            <h1 class="username">@goal2rush26</h1>
            <p class="bio">Daily curated tech deals and gadget reviews in India. Click below to shop!</p>
        </header>
        
        <!-- Featured Product -->
        <div>
            <h2 class="section-title">Today's Featured Deal</h2>
            <div class="featured-card">
                <span class="featured-badge">Featured</span>
                <div class="featured-img-container">
                    <img src="{featured_img}" alt="{featured['name']}" />
                </div>
                <div class="featured-info">
                    <span class="featured-category">{featured['category'].upper()}</span>
                    <h3 class="featured-title">{featured['name']}</h3>
                    <ul class="featured-points">
                        {selling_points_html}
                    </ul>
                </div>
                <a href="{featured['affiliate_link']}" target="_blank" class="cta-btn">{featured_cta}</a>
            </div>
        </div>
        
        <!-- Previous Products -->
        {f'<div><h2 class="section-title">Previous Recommendations</h2><div class="product-list">{prev_grid_html}</div></div>' if prev_grid_html else ''}
        
        <!-- Footer -->
        <footer>
            <p>Powered by <a href="https://github.com/GoogleDeepMind" target="_blank">ReelFlow Automation</a></p>
        </footer>
    </div>
</body>
</html>
"""
    
    output_html_file = "index.html"
    with open(output_html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Successfully generated static Link-in-Bio landing page: {output_html_file}")

if __name__ == "__main__":
    main()
