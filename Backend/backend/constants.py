import os
import sys

# Этот файл лежит в backend/src/constants.py
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SRC_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

# Пути к FFmpeg (папка ffmpeg_shared в корне)
FFMPEG_DIR = os.path.join(ROOT_DIR, "ffmpeg_shared")
FFMPEG_EXE = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
FFPROBE_EXE = os.path.join(FFMPEG_DIR, "ffprobe.exe")

# Добавляем FFmpeg в PATH системы для текущего процесса
os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

# Пути к весам
WEIGHTS_DIR = os.path.join(BACKEND_DIR, "weights")

# Изоляция кэша HuggingFace (BiRefNet)
CACHE_DIR = os.path.join(WEIGHTS_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
os.environ["HF_HOME"] = CACHE_DIR
os.environ["XDG_CACHE_HOME"] = CACHE_DIR

# Флаг системы (как в TAS)
import platform
SYSTEM = platform.system()