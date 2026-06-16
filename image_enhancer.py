import os
import sys
import json
from PIL import Image, ImageDraw, ImageFont
import rembg

def create_gradient_background(width, height, color1, color2):
    base = Image.new('RGB', (width, height), color1)
    top = Image.new('RGB', (width, height), color2)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        for x in range(width):
            mask_data.append(int(255 * (y / height)))
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def slugify(text):
    import re
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')

def main():
    if not os.path.exists("script.json"):
        print("No script.json found. Skipping image enhancement.")
        return

    try:
        with open("script.json", "r", encoding="utf-8") as f:
            script_data = json.load(f)
    except Exception as e:
        print(f"Error loading script.json: {e}")
        return

    product_name = script_data.get("product_name")
    if not product_name:
        return

    slug = slugify(product_name)
    image_folder = os.path.join("product_images", slug)
    
    if not os.path.exists(image_folder):
        return

    images = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    images.sort()

    if not images:
        return

    print(f"Enhancing {len(images)} images for '{product_name}'...")

    # Create dark premium gradient background (1080x1920)
    bg_color_top = (11, 13, 25)
    bg_color_bottom = (26, 16, 60)
    
    # Load premium font
    try:
        font_large = ImageFont.truetype("Montserrat-Bold.ttf", 75)
    except:
        font_large = ImageFont.load_default()

    for img_file in images:
        img_path = os.path.join(image_folder, img_file)
        
        try:
            input_img = Image.open(img_path).convert("RGBA")
        except Exception as e:
            print(f"Error opening {img_path}: {e}")
            continue
            
        print(f"  Processing {img_file} - removing background...")
        try:
            no_bg = rembg.remove(input_img)
            # Crop to the actual product's bounding box
            bbox = no_bg.getbbox()
            if bbox:
                no_bg = no_bg.crop(bbox)
        except Exception as e:
            print(f"  Background removal failed: {e}. Using original.")
            no_bg = input_img
            
        canvas = create_gradient_background(1080, 1920, bg_color_top, bg_color_bottom)
        
        # Resize to be beautifully large on the screen
        # We want the max dimension to be around 900 wide or 1000 tall
        ratio = min(900 / no_bg.width, 1000 / no_bg.height)
        new_size = (int(no_bg.width * ratio), int(no_bg.height * ratio))
        no_bg = no_bg.resize(new_size, Image.Resampling.LANCZOS)
        
        # Center horizontally, push slightly down to make room for text
        paste_x = (1080 - no_bg.width) // 2
        paste_y = (1920 - no_bg.height) // 2 + 100
        
        canvas.paste(no_bg, (paste_x, paste_y), no_bg if no_bg.mode == 'RGBA' else None)
        
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, 0, 1080, 250], fill=(0, 242, 254, 40)) # Neon teal accent
        
        text = product_name.upper()
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            test_line = " ".join(current_line)
            if draw.textlength(test_line, font=font_large) > 950: 
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
            
        y_text = 60
        for line in lines:
            text_width = draw.textlength(line, font=font_large)
            x_text = (1080 - text_width) / 2
            # Drop shadow
            draw.text((x_text+5, y_text+5), line, font=font_large, fill=(0, 0, 0, 180))
            # Text
            draw.text((x_text, y_text), line, font=font_large, fill=(255, 255, 255))
            y_text += 95

        enhanced_path = os.path.join(image_folder, img_file)
        canvas.convert("RGB").save(enhanced_path, "JPEG", quality=95)
        print(f"  Saved enhanced {img_file}")

if __name__ == "__main__":
    main()
