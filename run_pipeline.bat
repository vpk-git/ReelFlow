@echo off
echo ===================================================
echo   ReelFlow: Automated Instagram Reels Pipeline
echo   Started at: %date% %time%
echo ===================================================

cd /d "%~dp0"

:: Clean up old files to ensure a fresh run
if exist script.json del script.json
if exist background.mp4 del background.mp4
if exist voiceover.wav del voiceover.wav
if exist subtitles.srt del subtitles.srt
if exist final_reel.mp4 del final_reel.mp4

echo [1/4] Generating script and caption...
.venv\Scripts\python script_generator.py %*
if errorlevel 1 (
    echo Error: Script generation failed. Exiting.
    exit /b 1
)

echo [2/4] Downloading vertical background video...
.venv\Scripts\python video_downloader.py %*
if errorlevel 1 (
    echo Error: Background download failed. Exiting.
    exit /b 1
)

echo [2.5/4] Enhancing product images with AI background removal and branding...
.venv\Scripts\python image_enhancer.py
if errorlevel 1 (
    echo Warning: Image enhancement failed. Continuing with raw images.
)

echo [3/4] Synthesizing voiceover and compiling video...
.venv\Scripts\python assemble_video.py
if errorlevel 1 (
    echo Error: Video assembly failed. Exiting.
    exit /b 1
)

echo [4/4] Publishing Reel to Instagram...
.venv\Scripts\python publish_reel.py
if errorlevel 1 (
    echo Error: Reel publishing failed. Exiting.
    exit /b 1
)

echo [5/5] Updating Link-in-Bio landing page...
.venv\Scripts\python generate_link_in_bio.py
if errorlevel 1 (
    echo Warning: Link-in-Bio generation failed.
)

if exist .git (
    echo [6/5] Git repository detected. Committing and pushing updates to GitHub...
    git add index.html products.json history.json product_images
    git commit -m "Update Link-in-Bio: Auto-generated product update"
    git push
)

echo ===================================================
echo   🎉 Pipeline completed successfully!
echo ===================================================


