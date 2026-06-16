# ReelFlow 🎬

ReelFlow is a fully automated daily pipeline running on Windows to generate, compile, and publish programming/tech Instagram Reels. It utilizes **Google Gemini 2.5 Flash** for content generation, **Pexels API** for vertical stock video assets, **Coqui TTS** for high-quality localized voiceover audio synthesis, **FFmpeg** for video assembly/subtitling, and the **Meta Graph API** for direct publishing.

---

## Features

- **Automated AI Content:** Generates catchy programming topics, voiceover scripts (under 80 words), and optimized Instagram captions with hashtags.
- **Stock Video Search:** Automatically downloads context-relevant vertical stock footage (aspect ratio 9:16) from Pexels, falling back to a general "coding" query if no vertical clip matches a custom search.
- **Local Audio Synthesis:** Uses a local VITS text-to-speech model (`coqui-tts` package) to run text synthesis offline, avoiding third-party audio generation subscriptions.
- **Styled Subtitles:** Burns high-contrast yellow subtitles with bold black borders directly into the video stream using FFmpeg filters.
- **Optimized Video Resolution:** Downscales all videos to standard Reel resolution (**1080x1920**) and resamples audio to standard CD format (**44.1 kHz**) for seamless processing by Instagram.
- **Resumable Meta API Upload:** Uses Meta's Resumable Upload protocol to stream binary data directly to Meta's servers (`rupload.facebook.com`), eliminating public URL hosting requirements.
- **Topic Customization:** Supports generating Reels on specific topics on-demand via command-line parameters.

---

## File Structure

- `products.json` - JSON database containing the pool of 20 trending tech gadgets in India and your affiliate links.
- `history.json` - Automatically tracks used products so the system rotates through them sequentially.
- `script_generator.py` - Selects a product from the database, and generates the script and caption via Gemini.
- `video_downloader.py` - Queries Pexels for a vertical background matching the product category.
- `assemble_video.py` - Compiles subtitles (`subtitles.srt`) and speech (`voiceover.wav`), then outputs the final subtitled video (`final_reel.mp4`).
- `publish_reel.py` - Connects to Meta Graph API, uploads the binary, and publishes the Reel.
- `run_pipeline.bat` - Orchestrator script to clean up temp files and run the generation pipeline sequentially.
- `.env` - Project environment variables holding API keys and Page IDs.

---

## Affiliate Account Configuration (Autopilot)

To link your affiliate accounts and start earning commissions, you do not need to manually generate or copy links for every product! Simply configure your tracking IDs in the `.env` file:

1. Open the [`.env`](file:///d:/reelflow/.env) file.
2. Set your Amazon Associate Tag: `AMAZON_ASSOCIATE_TAG=yourtag-21`
3. Set your Flipkart Affiliate ID (optional): `FLIPKART_AFFILIATE_ID=yourfid`
4. Save the file.

The pipeline will automatically rewrite all Amazon and Flipkart affiliate links in the video captions, metadata, and generated landing page to use your tracking IDs on the fly!

---

## Dynamic Link-in-Bio Landing Page

On every daily run, the pipeline automatically generates and updates [`index.html`](file:///d:/reelflow/index.html) (a mobile-responsive glassmorphism landing page) with the latest featured product and previous deals.

To host it for free on **GitHub Pages**:
1. Initialize a Git repository in this folder and push it to your GitHub account.
2. Enable **GitHub Pages** in your repository settings pointing to the `main` branch.
3. The pipeline will automatically commit and push the updated `index.html`, database files, and product images to GitHub on every daily run!

---


## Prerequisites & Installation

### 1. Windows Software Prerequisites
The pipeline requires **FFmpeg** and **eSpeak NG** (required for the TTS phonemizer backend on Windows) installed:
```cmd
winget install Gyan.FFmpeg
winget install eSpeak.eSpeakNG
```

### 2. Environment Configurations
Rename `.env.template` to `.env` and fill out your keys:
- `GEMINI_API_KEY`: Get your key from Google AI Studio.
- `PEXELS_API_KEY`: Get your search key from Pexels Developer Portal.
- `META_ACCESS_TOKEN`: Long-lived Meta User/Page Access Token with `instagram_basic` and `instagram_content_publishing` scopes.
- `IG_USER_ID`: The ID of your Instagram Creator/Business account (you can fetch this using `fetch_ig_id.py`).

### 3. Python Virtual Environment Setup
Ensure Python is installed, then build the virtual environment:
```cmd
python -m venv .venv
.venv\Scripts\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\pip install coqui-tts[codec] torchcodec transformers<5.0 requests
```

---

## How to Run

### Daily Automation / Default Run
Runs the complete sequence and defaults to generating a random daily coding/tech topic:
```powershell
# PowerShell:
.\run_pipeline.bat

# Command Prompt (CMD):
run_pipeline.bat
```

### Custom Topic Generation
To compile and publish a video for a specific topic, pass it as an argument:
```powershell
# PowerShell:
.\run_pipeline.bat "Python List Comprehensions"

# Command Prompt (CMD):
run_pipeline.bat "Python List Comprehensions"
```

---

## Scheduling Daily Uploads via Windows Task Scheduler

To run the pipeline fully automated every morning:
1. Open **Task Scheduler** from the Windows Start menu.
2. Click **Create Basic Task...** in the Actions pane.
3. Name the task `ReelFlow Publisher` and set the trigger to **Daily** at your preferred time.
4. Set the Action to **Start a program**.
5. Set **Program/script** to: `d:\reelflow\run_pipeline.bat`
6. Set **Start in (optional)** to: `d:\reelflow` (Required for paths to resolve correctly).
7. Under task properties, select **Run whether user is logged on or not** and **Run with highest privileges** (General tab).
8. Ensure **Wake the computer to run this task** is enabled on the Conditions tab.


cmd /c run_pipeline.bat "your custom topic here"