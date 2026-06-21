import os
import platform

"""
Global Constants Configuration

These constants should not change their values once past argumentsChecker.py.
They're defined here to avoid populating the code with excessive arguments
and to improve code readability.
"""


RUNTIME_ROOT = os.path.join(os.environ.get("APPDATA", ""), "BackendAI")


WEIGHTS_DIR = os.path.join(RUNTIME_ROOT, "weights")
FFMPEG_EXE = os.path.join(RUNTIME_ROOT, "ffmpeg_shared", "ffmpeg.exe")
FFPROBE_EXE = os.path.join(RUNTIME_ROOT, "ffmpeg_shared", "ffprobe.exe")


WHEREAMIRUNFROM: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM: str = platform.system()


FFMPEGPATH: str = FFMPEG_EXE
FFPROBEPATH: str = FFPROBE_EXE
METADATAPATH: str = os.path.join(RUNTIME_ROOT, "metadata.json")


ADOBE: bool = False
AUDIO: bool = True


CACHE_DIR = os.path.join(WEIGHTS_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
os.environ["HF_HOME"] = CACHE_DIR
os.environ["XDG_CACHE_HOME"] = CACHE_DIR