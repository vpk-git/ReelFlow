import os
import sys
import json
import re
import subprocess
import urllib.parse
from http.server import SimpleHTTPRequestHandler
import socketserver
import requests

# Reconfigure stdout to use UTF-8
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

def read_live_env(filepath=".env"):
    """Reads the current .env file directly from disk and returns key-value mappings."""
    env_vars = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        env_vars[key.strip()] = val.strip().strip("'").strip('"')
        except Exception:
            pass
    return env_vars

# Ensure env variables are loaded
load_env()

def get_updated_env():
    """Returns a copy of the environment with the updated system PATH from the registry."""
    env = os.environ.copy()
    if sys.platform.startswith('win'):
        try:
            import winreg
            # Read User PATH
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                user_path = winreg.QueryValueEx(key, "Path")[0]
            # Read Machine PATH
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
                system_path = winreg.QueryValueEx(key, "Path")[0]
            
            # Combine paths
            env["PATH"] = os.path.expandvars(";".join([user_path, system_path]))
        except Exception:
            pass
    return env

def find_ffmpeg():
    """Finds if FFmpeg is configured or present on the system."""
    env = get_updated_env()
    path_dirs = env.get("PATH", "").split(";")
    for d in path_dirs:
        d = d.strip()
        if not d:
            continue
        for name in ["ffmpeg.exe", "ffmpeg"]:
            full_path = os.path.join(d, name)
            if os.path.isfile(full_path):
                return True
                
    fallbacks = [
        r"C:\Users\Girish\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for fb in fallbacks:
        if os.path.isfile(fb):
            return True
            
    return False

def check_scheduler():
    """Checks if the ReelFlow_Automation Windows Task Scheduler task is registered."""
    if not sys.platform.startswith('win'):
        return {"status": "SKIPPED", "details": "Not running on Windows"}
        
    try:
        # Query task scheduler
        result = subprocess.run(
            ["schtasks", "/query", "/tn", "ReelFlow_Automation", "/fo", "csv"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                # Task details found
                return {"status": "ONLINE", "details": "Task registered and active"}
        return {"status": "OFFLINE", "details": "Task 'ReelFlow_Automation' not found in Scheduler"}
    except Exception as e:
        return {"status": "OFFLINE", "details": f"Error querying scheduler: {e}"}

class DashboardAPIHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress printing verbose server logs to console
        pass

    def do_GET(self):
        # Serve API Status Endpoint
        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            status_data = self.run_diagnostics()
            self.wfile.write(json.dumps(status_data, indent=4).encode('utf-8'))
            return
            
        # Serve API History Endpoint
        elif self.path == "/api/history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            history_data = []
            log_file = "history_log.json"
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        history_data = json.load(f)
                except Exception:
                    pass
            self.wfile.write(json.dumps(history_data, indent=4).encode('utf-8'))
            return

        # Serve static dashboard.html at root "/" or "/dashboard"
        elif self.path == "/" or self.path == "/dashboard":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            
            html_file = "dashboard.html"
            if os.path.exists(html_file):
                with open(html_file, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                self.wfile.write(b"<h1>Error: dashboard.html not found!</h1>")
            return
            
        # Return 404 Not Found for other requests to prevent serving landing page or images on localhost
        else:
            self.send_error(404, "File Not Found")

    def run_diagnostics(self):
        diagnostics = {}
        current_env = read_live_env()
        
        # 1. Check Gemini API
        gemini_key = current_env.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in current_env else os.environ.get("GEMINI_API_KEY")
        if not gemini_key or "your_" in gemini_key:
            diagnostics["gemini"] = {"status": "OFFLINE", "details": "Key not configured in .env", "latency": "-"}
        else:
            # Run quick probe
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash?key={gemini_key}"
            try:
                import time
                start = time.time()
                r = requests.get(url, timeout=5)
                latency = int((time.time() - start) * 1000)
                if r.status_code == 200:
                    diagnostics["gemini"] = {"status": "ONLINE", "details": "Connection successful (Permanent Key)", "latency": f"{latency}ms"}
                else:
                    diagnostics["gemini"] = {"status": "OFFLINE", "details": f"API error (Status {r.status_code})", "latency": "-"}
            except Exception as e:
                diagnostics["gemini"] = {"status": "OFFLINE", "details": f"Connection failed: {e}", "latency": "-"}
                
        # 2. Check Pexels API
        pexels_key = current_env.get("PEXELS_API_KEY") if "PEXELS_API_KEY" in current_env else os.environ.get("PEXELS_API_KEY")
        if not pexels_key or "your_" in pexels_key:
            diagnostics["pexels"] = {"status": "OFFLINE", "details": "Key not configured in .env", "latency": "-"}
        else:
            url = "https://api.pexels.com/videos/search?query=test&per_page=1"
            headers = {"Authorization": pexels_key}
            try:
                import time
                start = time.time()
                r = requests.get(url, headers=headers, timeout=5)
                latency = int((time.time() - start) * 1000)
                if r.status_code == 200:
                    diagnostics["pexels"] = {"status": "ONLINE", "details": "Connection successful (Permanent Key)", "latency": f"{latency}ms"}
                else:
                    diagnostics["pexels"] = {"status": "OFFLINE", "details": f"API error (Status {r.status_code})", "latency": "-"}
            except Exception as e:
                diagnostics["pexels"] = {"status": "OFFLINE", "details": f"Connection failed: {e}", "latency": "-"}

        # 3. Check Flipkart Scraper
        try:
            import time
            start = time.time()
            # Simple status check on search endpoint
            r = requests.get("https://www.flipkart.com/search?q=test", headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            latency = int((time.time() - start) * 1000)
            if r.status_code == 200:
                diagnostics["flipkart"] = {"status": "ONLINE", "details": "Search catalog active (No Expiry)", "latency": f"{latency}ms"}
            else:
                diagnostics["flipkart"] = {"status": "OFFLINE", "details": f"HTTP status {r.status_code}", "latency": "-"}
        except Exception as e:
            diagnostics["flipkart"] = {"status": "OFFLINE", "details": f"Ping failed: {e}", "latency": "-"}

        # 4. Check Meta/Instagram Graph API
        ig_user_id = current_env.get("IG_USER_ID") if "IG_USER_ID" in current_env else os.environ.get("IG_USER_ID")
        access_token = current_env.get("META_ACCESS_TOKEN") if "META_ACCESS_TOKEN" in current_env else os.environ.get("META_ACCESS_TOKEN")
        if not ig_user_id or not access_token or "your_" in access_token:
            diagnostics["instagram"] = {"status": "OFFLINE", "details": "Credentials not set in .env", "latency": "-"}
        else:
            url = f"https://graph.facebook.com/v20.0/{ig_user_id}"
            params = {"fields": "name,username", "access_token": access_token}
            try:
                import time
                start = time.time()
                r = requests.get(url, params=params, timeout=5)
                latency = int((time.time() - start) * 1000)
                if r.status_code == 200:
                    data = r.json()
                    username = data.get('username', 'ReelFlow')
                    
                    # Fetch Token Expiry details via Meta's debug_token endpoint
                    meta_expiry = "Unknown Expiry"
                    app_id = current_env.get("META_APP_ID") or os.environ.get("META_APP_ID")
                    app_secret = current_env.get("META_APP_SECRET") or os.environ.get("META_APP_SECRET")
                    if app_id and app_secret:
                        app_token = f"{app_id}|{app_secret}"
                        debug_url = "https://graph.facebook.com/debug_token"
                        debug_params = {
                            "input_token": access_token,
                            "access_token": app_token
                        }
                        try:
                            debug_res = requests.get(debug_url, params=debug_params, timeout=5)
                            if debug_res.status_code == 200:
                                debug_data = debug_res.json().get("data", {})
                                if debug_data.get("is_valid"):
                                    expires_at = debug_data.get("expires_at", 0)
                                    if expires_at == 0:
                                        meta_expiry = "Never Expires"
                                    else:
                                        import datetime
                                        delta = datetime.datetime.fromtimestamp(expires_at) - datetime.datetime.now()
                                        days_left = delta.days
                                        if days_left < 0:
                                            meta_expiry = "Expired"
                                        else:
                                            meta_expiry = f"Expires in {days_left} days"
                                else:
                                    meta_expiry = "Invalid Token"
                        except Exception:
                            pass
                            
                    diagnostics["instagram"] = {
                        "status": "ONLINE",
                        "details": f"Account: @{username} ({meta_expiry})",
                        "latency": f"{latency}ms"
                    }
                else:
                    diagnostics["instagram"] = {"status": "OFFLINE", "details": f"Auth failed (Status {r.status_code})", "latency": "-"}
            except Exception as e:
                diagnostics["instagram"] = {"status": "OFFLINE", "details": f"Ping failed: {e}", "latency": "-"}

        # 5. Check Local Coqui TTS
        tts_exe = os.path.join(".venv", "Scripts", "tts.exe")
        if os.path.exists(tts_exe) or os.path.exists(os.path.join(".venv", "Scripts", "tts")):
            diagnostics["coqui_tts"] = {"status": "ONLINE", "details": "Jenny model voice engine ready", "latency": "-"}
        else:
            diagnostics["coqui_tts"] = {"status": "OFFLINE", "details": "coqui-tts executable not found in .venv", "latency": "-"}

        # 6. Check FFmpeg
        if find_ffmpeg():
            diagnostics["ffmpeg"] = {"status": "ONLINE", "details": "FFmpeg visual compiler loaded", "latency": "-"}
        else:
            diagnostics["ffmpeg"] = {"status": "OFFLINE", "details": "FFmpeg not found in PATH or Gyans fallbacks", "latency": "-"}

        # 7. Check Task Scheduler
        diagnostics["scheduler"] = check_scheduler()

        return diagnostics

def main():
    PORT = 8000
    Handler = DashboardAPIHandler
    
    # TCPServer allows reusing address to prevent "Address already in use" errors on restarts
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"\n=======================================================")
        print(f"  ReelFlow Dashboard Server Active!")
        print(f"  👉 View dashboard at: http://localhost:{PORT}")
        print(f"  Press Ctrl+C to stop the server.")
        print(f"=======================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down dashboard server...")

if __name__ == "__main__":
    main()
