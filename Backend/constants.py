import os
import sys
import platform


SRC_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SRC_DIR)


if platform.system() == "Windows":
    RUNTIME_ROOT = os.path.join(os.environ.get("APPDATA", ""), "BackendAI")
else:
    RUNTIME_ROOT = os.path.dirname(BACKEND_DIR)

os.makedirs(RUNTIME_ROOT, exist_ok=True)


FFMPEG_DIR = os.path.join(RUNTIME_ROOT, "ffmpeg_shared")
FFMPEG_EXE = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
FFPROBE_EXE = os.path.join(FFMPEG_DIR, "ffprobe.exe")


os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")


WEIGHTS_DIR = os.path.join(RUNTIME_ROOT, "weights")


CACHE_DIR = os.path.join(WEIGHTS_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
os.environ["HF_HOME"] = CACHE_DIR
os.environ["XDG_CACHE_HOME"] = CACHE_DIR

SYSTEM = platform.system()