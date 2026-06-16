import os
import sys
import requests

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

def download_file(url, destination):
    """Downloads a file in chunks showing progress."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024  # 1MB
        downloaded = 0
        
        print(f"Downloading background video to '{destination}'...")
        with open(destination, 'wb') as f:
            for data in response.iter_content(block_size):
                f.write(data)
                downloaded += len(data)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"  Progress: {percent:.1f}% ({downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB)", end='\r')
                else:
                    print(f"  Progress: {downloaded / (1024*1024):.1f} MB downloaded", end='\r')
        print("\nDownload complete!")
        return True
    except Exception as e:
        print(f"\nFailed to download file: {e}")
        return False

def get_pexels_video(api_key, query="coding"):
    """Search Pexels for portrait-oriented tech videos and get the best vertical file link."""
    print(f"Searching Pexels for vertical stock videos matching: '{query}'...")
    
    url = "https://api.pexels.com/videos/search"
    headers = {
        "Authorization": api_key
    }
    params = {
        "query": query,
        "orientation": "portrait",
        "per_page": 10
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error calling Pexels API (Status Code {response.status_code}):")
            print(response.text)
            return None
            
        data = response.json()
        videos = data.get("videos", [])
        
        if not videos:
            print(f"No vertical videos found on Pexels matching query: '{query}'")
            if query != "coding":
                print("Falling back to search query 'coding'...")
                return get_pexels_video(api_key, "coding")
            return None
            
        print(f"Found {len(videos)} potential vertical video(s). Inspecting files...")
        
        # Iterate through search results to find a valid vertical file
        for idx, video in enumerate(videos, 1):
            video_files = video.get("video_files", [])
            
            # Look for vertical files: width < height
            vertical_files = [
                vf for vf in video_files 
                if vf.get("width") and vf.get("height") and vf.get("width") < vf.get("height")
            ]
            
            if not vertical_files:
                continue
                
            # Prefer HD quality or typical vertical resolutions (like 1080x1920 or 720x1280)
            # Sort by resolution, choosing high but standard vertical size
            vertical_files.sort(key=lambda vf: vf.get("width", 0), reverse=True)
            
            best_file = vertical_files[0]
            download_url = best_file.get("link")
            width = best_file.get("width")
            height = best_file.get("height")
            
            print(f"Selected Video #{idx}: ID {video.get('id')} ({width}x{height})")
            return download_url
            
        print("Could not find any suitable vertical video files in the results.")
        if query != "coding":
            print("Falling back to search query 'coding'...")
            return get_pexels_video(api_key, "coding")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Network error querying Pexels API: {e}")
        return None

def main():
    import json
    print("=== ReelFlow Video Downloader ===")
    
    # 1. Load configuration
    if not load_env():
        print("Error: '.env' file not found. Please set up your .env file first.")
        sys.exit(1)
        
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key or "your_copied_pexels_key" in api_key:
        print("Error: PEXELS_API_KEY is not configured in your '.env' file.")
        sys.exit(1)
        
    # 2. Determine search query
    query = "coding"
    
    # Try reading the selected product category from script.json first
    script_file = "script.json"
    if os.path.exists(script_file):
        try:
            with open(script_file, "r", encoding="utf-8") as f:
                script_data = json.load(f)
                category = script_data.get("product_category")
                if category:
                    query = category
                    print(f"Detected product category from script.json: '{query}'")
        except Exception as e:
            print(f"Warning: Could not read script.json for product category: {e}")
            
    # Command line argument overrides script.json if provided
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"Command line argument override search query: '{query}'")
        
    # 3. Search Pexels for a vertical video
    download_url = get_pexels_video(api_key, query)
    
    if not download_url:
        print("Could not retrieve a valid video URL.")
        sys.exit(1)
        
    # 4. Download the video file
    output_filename = "background.mp4"
    success = download_file(download_url, output_filename)
    
    if success:
        print(f"Background asset successfully saved as: {output_filename}")
    else:
        print("Failed to save background asset.")
        sys.exit(1)

if __name__ == "__main__":
    main()
