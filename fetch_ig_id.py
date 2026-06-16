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
                # Strip potential surrounding quotes
                val_str = val.strip().strip("'").strip('"')
                os.environ[key.strip()] = val_str
    return True

def save_ig_user_id_to_env(ig_user_id, filepath=".env"):
    """Appends or updates the IG_USER_ID in the .env file."""
    if not os.path.exists(filepath):
        print(f"Error: {filepath} file not found. Please copy .env.template to .env first.")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("IG_USER_ID="):
            new_lines.append(f"IG_USER_ID={ig_user_id}\n")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        # If not found, append it to the end
        new_lines.append(f"\n# Automatically added by fetch_ig_id.py:\nIG_USER_ID={ig_user_id}\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    
    print(f"Successfully updated {filepath} with IG_USER_ID={ig_user_id}")
    return True

def main():
    print("=== ReelFlow Instagram User ID Fetcher ===")
    
    # 1. Load .env file
    if not load_env():
        print("Error: '.env' file not found in the current directory.")
        print("Please copy '.env.template' to '.env' and fill in your META_ACCESS_TOKEN first:")
        print("  copy .env.template .env")
        sys.exit(1)
        
    access_token = os.environ.get("META_ACCESS_TOKEN")
    if not access_token or "your_long_generated_access_token" in access_token:
        print("Error: META_ACCESS_TOKEN is not set or still has the placeholder value in '.env'.")
        print("Please update your '.env' file with your actual Meta Access Token.")
        sys.exit(1)
        
    print("Meta Access Token loaded successfully.")
    print("Fetching connected Facebook Pages and Instagram Accounts...")
    
    # 2. Call Meta Graph API
    # We query /me/accounts which lists Facebook pages managed by this user,
    # requesting the linked instagram_business_account details.
    url = "https://graph.facebook.com/v20.0/me/accounts"
    params = {
        "fields": "name,instagram_business_account",
        "access_token": access_token
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if response.status_code != 200:
            print(f"\nAPI Error (Status Code {response.status_code}):")
            print(data.get("error", {}).get("message", "Unknown error occurred."))
            print("Please verify your META_ACCESS_TOKEN or check your app permissions.")
            sys.exit(1)
            
        pages = data.get("data", [])
        if not pages:
            print("\nNo Facebook Pages found associated with this user access token.")
            print("Please make sure you have created a Facebook Page and linked it to your Instagram Business account.")
            sys.exit(1)
            
        print(f"\nFound {len(pages)} Facebook Page(s):")
        ig_accounts_found = []
        
        for index, page in enumerate(pages, 1):
            page_name = page.get("name")
            ig_account = page.get("instagram_business_account")
            
            print(f"\n{index}. Facebook Page: '{page_name}'")
            if ig_account:
                ig_id = ig_account.get("id")
                print(f"   +-- Connected Instagram Business Account ID: {ig_id}")
                ig_accounts_found.append((page_name, ig_id))
            else:
                print("   +-- No connected Instagram Business Account found for this page.")
                
        if not ig_accounts_found:
            print("\nNo connected Instagram Business Accounts were found across any of your pages.")
            print("Ensure your Instagram account is set to a Creator/Business profile and linked to the Facebook Page.")
            sys.exit(1)
            
        # If we found at least one Instagram Business account
        selected_ig_id = None
        if len(ig_accounts_found) == 1:
            selected_ig_id = ig_accounts_found[0][1]
            print(f"\nUsing the only connected Instagram ID: {selected_ig_id}")
        else:
            print("\nMultiple Instagram Accounts found:")
            for idx, (p_name, ig_id) in enumerate(ig_accounts_found, 1):
                print(f"  [{idx}] {p_name} -> {ig_id}")
            
            # Since this script runs in the command line, we can ask for user input:
            try:
                choice = input("\nSelect the page number to use for your pipeline (e.g. 1): ").strip()
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(ig_accounts_found):
                    selected_ig_id = ig_accounts_found[choice_idx][1]
                else:
                    print("Invalid selection. Using the first option.")
                    selected_ig_id = ig_accounts_found[0][1]
            except Exception:
                print("Invalid input. Using the first option.")
                selected_ig_id = ig_accounts_found[0][1]
                
        # 3. Save the ID back to the .env file
        save_ig_user_id_to_env(selected_ig_id)
        print("\nAll done! You are ready to start automated publishing.")
        
    except requests.exceptions.RequestException as e:
        print(f"\nNetwork error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
