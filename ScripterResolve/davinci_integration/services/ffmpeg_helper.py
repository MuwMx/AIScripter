import os
import subprocess

def cut_video_raw(ffmpeg_exe, input_path, output_path, source_start_frame, source_fps, duration_frames, timeline_fps, log_callback):
    """
    Нарезает видео через FFmpeg с легким H.264, учитывая таймлайн-сетку кадров DaVinci.
    """
    log_callback("[FFMPEG] Starting Raw Mode extraction...")
    


    start_sec = source_start_frame / timeline_fps
    duration_sec = duration_frames / timeline_fps
    
    log_callback(f"[FFMPEG] Corrected math -> Start: {start_sec:.3f}s | Duration: {duration_sec:.3f}s | (Timeline FPS: {timeline_fps})")

    cmd = [
        ffmpeg_exe, "-y",
        "-ss", str(start_sec),
        "-i", input_path,
        "-t", str(duration_sec),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "16",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path
    ]

    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    
    stdout, _ = process.communicate()
    
    if process.returncode != 0 or not os.path.exists(output_path):
        print(f"[FFMPEG CRITICAL LOG]\n{stdout}")
        raise RuntimeError(f"FFmpeg failed to extract the video chunk. Exit code: {process.returncode}")
        
    log_callback(f"[FFMPEG] Raw chunk extracted successfully: {output_path}")
    return output_path