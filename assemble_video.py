import os
import sys
import json
import wave
import subprocess
import re

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

def get_updated_env():
    """Returns a copy of the environment with the updated system PATH from the registry and eSpeak config."""
    env = os.environ.copy()
    
    # Configure eSpeak path locally for Windows
    espeak_dir = r"C:\Program Files\eSpeak NG"
    espeak_dll = os.path.join(espeak_dir, "libespeak-ng.dll")
    if os.path.exists(espeak_dir):
        env["PHONEMIZER_ESPEAK_LIBRARY"] = espeak_dll
        env["PHONEMIZER_ESPEAK_PATH"] = espeak_dir
        
    if sys.platform.startswith('win'):
        try:
            import winreg
            # Read User PATH
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                user_path = winreg.QueryValueEx(key, "Path")[0]
            # Read Machine PATH
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
                system_path = winreg.QueryValueEx(key, "Path")[0]
            
            # Combine paths and ensure espeak_dir is included in PATH
            all_paths = [user_path, system_path]
            if os.path.exists(espeak_dir):
                all_paths.append(espeak_dir)
            env["PATH"] = os.path.expandvars(";".join(all_paths))
        except Exception as e:
            print(f"Warning: Could not read registry PATH, using default: {e}")
            if os.path.exists(espeak_dir):
                env["PATH"] = env.get("PATH", "") + ";" + espeak_dir
            env["PATH"] = os.path.expandvars(env.get("PATH", ""))
    return env

def find_ffmpeg():
    """Finds the absolute path to the ffmpeg executable."""
    env = get_updated_env()
    path_dirs = env.get("PATH", "").split(";")
    for d in path_dirs:
        d = d.strip()
        if not d:
            continue
        for name in ["ffmpeg.exe", "ffmpeg"]:
            full_path = os.path.join(d, name)
            if os.path.isfile(full_path):
                return full_path
    
    # Fallbacks
    fallbacks = [
        r"C:\Users\Girish\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for fb in fallbacks:
        if os.path.isfile(fb):
            return fb
            
    return "ffmpeg.exe"

def get_audio_duration(filepath):
    """Calculates the duration of a WAV audio file in seconds."""
    with wave.open(filepath, "rb") as f:
        frames = f.getnframes()
        rate = f.getframerate()
        duration = frames / float(rate)
    return duration

def format_srt_time(seconds):
    """Converts a float number of seconds to the standard SRT timestamp format: HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def split_text_into_chunks(text, max_words=6):
    """Splits text into small chunks of words for high-visibility subtitles."""
    words = text.split()
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        # End chunk if max words limit is reached or if word ends in punctuation
        if len(current_chunk) >= max_words or word.endswith(('.', '!', '?')):
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

def generate_srt(text, audio_duration, output_filepath="subtitles.srt"):
    """Creates a subtitles.srt file with evenly distributed timestamps based on audio duration."""
    chunks = split_text_into_chunks(text)
    if not chunks:
        return False
        
    chunk_duration = audio_duration / len(chunks)
    
    print(f"Generating subtitles ({len(chunks)} chunks)...")
    with open(output_filepath, "w", encoding="utf-8") as f:
        for idx, chunk in enumerate(chunks):
            start_time = idx * chunk_duration
            end_time = (idx + 1) * chunk_duration
            
            f.write(f"{idx + 1}\n")
            f.write(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}\n")
            f.write(f"{chunk}\n\n")
            
    print(f"Saved subtitles to: {output_filepath}")
    return True

def main():
    print("=== ReelFlow Video Assembler ===")
    
    # 1. Load script.json
    script_file = "script.json"
    if not os.path.exists(script_file):
        print(f"Error: {script_file} not found. Please run script_generator.py first.")
        sys.exit(1)
        
    with open(script_file, "r", encoding="utf-8") as f:
        script_data = json.load(f)
        
    script_text = script_data.get("script_text")
    if not script_text:
        print("Error: script_text is missing from script.json.")
        sys.exit(1)
        
    print(f"Loaded Script: \"{script_text[:60]}...\"")
    
    # 2. Synthesize Voiceover Audio using Coqui TTS
    voiceover_wav = "voiceover.wav"
    
    print("Synthesizing voiceover with local Coqui TTS...")
    
    tts_cmd = [
        ".venv\\Scripts\\tts",
        "--text", script_text,
        "--model_name", "tts_models/en/jenny/jenny",
        "--out_path", voiceover_wav
    ]
    
    try:
        subprocess.run(tts_cmd, env=get_updated_env(), check=True)
        print("Voiceover synthesized successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running Coqui TTS command: {e}")
        sys.exit(1)
        
    if not os.path.exists(voiceover_wav):
        print("Error: voiceover.wav was not created.")
        sys.exit(1)
        
    # 3. Calculate Durations & Generate Subtitles
    audio_duration = get_audio_duration(voiceover_wav)
    print(f"Voiceover duration: {audio_duration:.2f} seconds")
    
    srt_file = "subtitles.srt"
    generate_srt(script_text, audio_duration, srt_file)
    
    # 4. Compile final video using FFmpeg
    final_output = "final_reel.mp4"
    print("Compiling final video using FFmpeg...")
    
    subtitle_style = (
        "force_style='"
        "Alignment=2,"
        "Fontname=Trebuchet MS,"
        "Bold=1,"
        "FontSize=24,"
        "PrimaryColour=&H00FFFF&," # Yellow text
        "OutlineColour=&H000000&," # Black outline
        "Outline=2.5,"
        "BorderStyle=1,"
        "MarginV=35'"
    )
    
    ffmpeg_exe = find_ffmpeg()
    print(f"Using FFmpeg executable at: {ffmpeg_exe}")
    
    # Check if this is a product run and if images exist
    product_name = script_data.get("product_name")
    images = []
    if product_name:
        slug = slugify(product_name)
        image_folder = os.path.join("product_images", slug)
        if os.path.exists(image_folder):
            images = [
                os.path.join(image_folder, f) 
                for f in os.listdir(image_folder) 
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
            ]
            images.sort()
            
    # Detect branding assets
    has_music = os.path.exists("music.mp3")
    has_logo = os.path.exists("logo.png")
    
    if images:
        print(f"Found {len(images)} product images in '{image_folder}'.")
        print("Compiling high-end product slideshow Reel...")
        
        # Calculate duration per image
        t = audio_duration / len(images)
        
        # Build FFmpeg command inputs
        ffmpeg_cmd = [ffmpeg_exe, "-y"]
        for img in images:
            ffmpeg_cmd.extend(["-loop", "1", "-t", f"{t:.2f}", "-i", img])
            
        # Add the voiceover audio as input index N (equal to len(images))
        ffmpeg_cmd.extend(["-i", voiceover_wav])
        
        # Manage additional inputs indices
        next_idx = len(images) + 1
        music_idx = None
        if has_music:
            ffmpeg_cmd.extend(["-stream_loop", "-1", "-i", "music.mp3"])
            music_idx = next_idx
            next_idx += 1
            
        logo_idx = None
        if has_logo:
            ffmpeg_cmd.extend(["-i", "logo.png"])
            logo_idx = next_idx
            next_idx += 1
            
        # Build the complex filter graph
        filter_parts = []
        for i in range(len(images)):
            filter_parts.append(
                f"[{i}:v]fps=25,format=yuv420p[v{i}]"
            )
            
        # Concat part
        concat_inputs = "".join([f"[v{i}]" for i in range(len(images))])
        filter_parts.append(f"{concat_inputs}concat=n={len(images)}:v=1:a=0[v_slideshow]")
        
        # Subtitle part
        filter_parts.append(f"[v_slideshow]subtitles={srt_file}:{subtitle_style}[v_subbed]")
        
        # Watermark logo part
        if logo_idx is not None:
            filter_parts.append(f"[{logo_idx}:v]scale=120:-1[watermark]")
            filter_parts.append(f"[v_subbed][watermark]overlay=W-w-40:40[v]")
            video_map = "[v]"
        else:
            video_map = "[v_subbed]"
            
        # Audio mixing part
        if music_idx is not None:
            filter_parts.append(f"[{music_idx}:a]volume=0.08[bg_music]")
            filter_parts.append(f"[{len(images)}:a][bg_music]amix=inputs=2:duration=first:dropout_transition=0[a]")
            audio_map = "[a]"
        else:
            audio_map = f"{len(images)}:a"
            
        filter_complex_str = "; ".join(filter_parts)
        
        ffmpeg_cmd.extend([
            "-filter_complex", filter_complex_str,
            "-map", video_map,
            "-map", audio_map,
            "-t", f"{audio_duration:.2f}",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            final_output
        ])
    else:
        print("No product images found. Falling back to stock video...")
        background_video = "background.mp4"
        if not os.path.exists(background_video):
            print(f"Error: {background_video} not found. Please run video_downloader.py first.")
            sys.exit(1)
            
        ffmpeg_cmd = [ffmpeg_exe, "-y"]
        # Input 0: Background video
        ffmpeg_cmd.extend(["-stream_loop", "-1", "-i", background_video])
        # Input 1: Voiceover
        ffmpeg_cmd.extend(["-i", voiceover_wav])
        
        # Manage indices
        next_idx = 2
        music_idx = None
        if has_music:
            ffmpeg_cmd.extend(["-stream_loop", "-1", "-i", "music.mp3"])
            music_idx = next_idx
            next_idx += 1
            
        logo_idx = None
        if has_logo:
            ffmpeg_cmd.extend(["-i", "logo.png"])
            logo_idx = next_idx
            next_idx += 1
            
        filter_parts = []
        # Scale background and add subtitles
        filter_parts.append(f"[0:v]scale=1080:1920,subtitles={srt_file}:{subtitle_style}[v_subbed]")
        
        # Watermark logo
        if logo_idx is not None:
            filter_parts.append(f"[{logo_idx}:v]scale=120:-1[watermark]")
            filter_parts.append(f"[v_subbed][watermark]overlay=W-w-40:40[v]")
            video_map = "[v]"
        else:
            video_map = "[v_subbed]"
            
        # Audio mixing
        if music_idx is not None:
            filter_parts.append(f"[{music_idx}:a]volume=0.08[bg_music]")
            filter_parts.append(f"[1:a][bg_music]amix=inputs=2:duration=first:dropout_transition=0[a]")
            audio_map = "[a]"
        else:
            audio_map = "1:a"
            
        filter_complex_str = "; ".join(filter_parts)
        
        ffmpeg_cmd.extend([
            "-filter_complex", filter_complex_str,
            "-map", video_map,
            "-map", audio_map,
            "-t", f"{audio_duration:.2f}",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            final_output
        ])
        
    try:
        subprocess.run(ffmpeg_cmd, env=get_updated_env(), check=True)
        print(f"\nReel compiled successfully! Output file: {final_output}")
        print("Verification complete. You can play final_reel.mp4 to review it.")
    except subprocess.CalledProcessError as e:
        print(f"Error running FFmpeg command: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
