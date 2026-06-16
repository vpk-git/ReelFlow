import os
import sys
import json
import time
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

def main():
    print("=== ReelFlow Instagram Reel Publisher ===")
    
    # 1. Load Environment Variables
    if not load_env():
        print("Error: .env file not found. Please create one.")
        sys.exit(1)
        
    access_token = os.environ.get("META_ACCESS_TOKEN")
    ig_user_id = os.environ.get("IG_USER_ID")
    
    if not access_token or not ig_user_id:
        print("Error: META_ACCESS_TOKEN and IG_USER_ID must be set in .env.")
        sys.exit(1)
        
    # 2. Check Assets
    video_path = "final_reel.mp4"
    if not os.path.exists(video_path):
        print(f"Error: {video_path} not found. Please compile the video first.")
        sys.exit(1)
        
    script_path = "script.json"
    caption = "Coding tip from ReelFlow! 🚀"
    if os.path.exists(script_path):
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                script_data = json.load(f)
                caption = script_data.get("caption", caption)
        except Exception as e:
            print(f"Warning: Could not read caption from script.json: {e}")
            
    print(f"Loaded Caption: \"{caption[:60]}...\"")
    
    # Step 1: Initialize Resumable Upload Session (Create Container)
    print("\n[Step 1/4] Initializing Resumable Upload Session with Instagram Graph API...")
    init_url = f"https://graph.facebook.com/v20.0/{ig_user_id}/media"
    init_params = {
        "access_token": access_token,
        "upload_type": "resumable",
        "media_type": "REELS",
        "caption": caption
    }
    
    try:
        response = requests.post(init_url, params=init_params)
        res_data = response.json()
        if response.status_code != 200:
            print(f"Initialization Failed: {res_data}")
            sys.exit(1)
            
        container_id = res_data.get("id")
        upload_uri = res_data.get("uri")
        if not container_id or not upload_uri:
            print(f"Initialization response missing container ID or upload URI: {res_data}")
            sys.exit(1)
            
        print(f"Session initialized successfully.")
        print(f"Container ID: {container_id}")
    except Exception as e:
        print(f"Error initializing upload session: {e}")
        sys.exit(1)
        
    # Step 2: Upload Video Binary to Meta Servers
    print("\n[Step 2/4] Uploading video binary data directly to Meta...")
    file_size = os.path.getsize(video_path)
    
    try:
        with open(video_path, "rb") as f:
            headers = {
                "Authorization": f"OAuth {access_token}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream"
            }
            # Stream the binary video data to the returned upload URI
            upload_response = requests.post(upload_uri, headers=headers, data=f)
            upload_data = upload_response.json()
            
            if upload_response.status_code != 200:
                print(f"Binary Upload Failed: {upload_data}")
                sys.exit(1)
                
            print("Video binary uploaded successfully.")
    except Exception as e:
        print(f"Error uploading video binary: {e}")
        sys.exit(1)
        
    # Step 3: Poll Container Processing Status
    print("\n[Step 3/4] Waiting for Instagram to process the video (polling status)...")
    status_url = f"https://graph.facebook.com/v20.0/{container_id}"
    status_params = {
        "fields": "status_code",
        "access_token": access_token
    }
    
    max_attempts = 30
    poll_interval = 10
    processed = False
    
    for attempt in range(1, max_attempts + 1):
        try:
            status_response = requests.get(status_url, params=status_params)
            status_data = status_response.json()
            
            if status_response.status_code != 200:
                print(f"Failed to check status: {status_data}")
                time.sleep(poll_interval)
                continue
                
            status_code = status_data.get("status_code")
            print(f"Attempt {attempt}/{max_attempts}: Status is '{status_code}'")
            
            if status_code == "FINISHED":
                processed = True
                break
            elif status_code == "ERROR":
                print(f"Error processing video: {status_data}")
                sys.exit(1)
            # If status_code is 'IN_PROGRESS', keep polling
            
        except Exception as e:
            print(f"Error polling status: {e}")
            
        time.sleep(poll_interval)
        
    if not processed:
        print("Error: Video processing timed out. Please try publishing manually later.")
        sys.exit(1)
        
    print("Video processing finished and ready for publishing.")
    
    # Step 4: Publish the Media Container
    print("\n[Step 4/4] Publishing the Reel to your Instagram Feed...")
    publish_url = f"https://graph.facebook.com/v20.0/{ig_user_id}/media_publish"
    publish_params = {
        "creation_id": container_id,
        "access_token": access_token
    }
    
    try:
        publish_response = requests.post(publish_url, params=publish_params)
        publish_data = publish_response.json()
        
        if publish_response.status_code != 200:
            print(f"Publishing Failed: {publish_data}")
            sys.exit(1)
            
        published_id = publish_data.get("id")
        print("\n==============================================")
        print("🎉 REEL PUBLISHED SUCCESSFULLY!")
        print(f"Published Reel ID: {published_id}")
        print("==============================================")
        
        # Update history.json upon successful publication
        if os.path.exists(script_path):
            try:
                with open(script_path, "r", encoding="utf-8") as f:
                    script_data = json.load(f)
                prod_name = script_data.get("product_name")
                if prod_name:
                    history_file = "history.json"
                    history = []
                    if os.path.exists(history_file):
                        try:
                            with open(history_file, "r", encoding="utf-8") as f:
                                history = json.load(f)
                        except Exception:
                            pass
                    if prod_name not in history:
                        history.append(prod_name)
                        with open(history_file, "w", encoding="utf-8") as f:
                            json.dump(history, f, indent=4, ensure_ascii=False)
                        print(f"Successfully added '{prod_name}' to history.json.")
            except Exception as he:
                print(f"Warning: Could not update history.json: {he}")
    except Exception as e:
        print(f"Error publishing Reel: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
