import os
import sys
import argparse
import subprocess
import urllib.parse  # Добавлено для лечения путей от %20 и URL-мусора
import cv2
import torch
import numpy as np
from tqdm import tqdm

# =====================================================================
# ЖЕЛЕЗОБЕТОННАЯ МАРШРУТИЗАЦИЯ ПУТЕЙ
# =====================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # ...\src\depth
SRC_DIR = os.path.dirname(CURRENT_DIR)                   # ...\src
ROOT_DIR = os.path.dirname(SRC_DIR)                      # ...\MyScripterAE

FFMPEG_EXE = os.path.join(ROOT_DIR, "ffmpeg_shared", "ffmpeg.exe")
WEIGHTS_DIR = os.path.join(ROOT_DIR, "weights", "depth")

# Добавляем папку depth в sys.path, чтобы Питон увидел depth_anything_v2
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

try:
    # Импортируем чистую архитектуру V2
    from depth_anything_v2.dpt import DepthAnythingV2
except ImportError as e:
    print(f"\n[CRITICAL ERROR] Failed to import DepthAnythingV2.")
    print(f"Make sure the 'depth_anything_v2' folder is located here: {CURRENT_DIR}")
    print(f"Details: {e}")  
    sys.exit(1)

# =====================================================================
# КЛАСС ВОРКЕРА КАРТЫ ГЛУБИНЫ
# =====================================================================
class DepthWorker:
    def __init__(self, model_size='vits'):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[DEPTH] Initializing Depth Anything V2 ({model_size.upper()}) on {self.device.type.upper()}...")

        # Конфигурации архитектуры под разные размеры
        model_configs = {
            'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
            'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
            'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 2048]}
        }

        self.model = DepthAnythingV2(**model_configs[model_size])
        
        # Ищем файл весов в MyScripterAE/weights/depth/
        weight_path = os.path.join(WEIGHTS_DIR, f"depth_anything_v2_{model_size}.pth")
        if not os.path.exists(weight_path):
            print(f"\n[ERROR] Weight file not found: {weight_path}")
            print("Download the .pth file and place it in the weights/depth/ folder.")
            sys.exit(1)

        # Загружаем веса в VRAM
        self.model.load_state_dict(torch.load(weight_path, map_location='cpu'))
        self.model = self.model.to(self.device).eval()

    def process(self, input_path, output_path):
        # 1. ЛЕЧИМ ПУТЬ ОТ URL-МУСОРА
        input_path = urllib.parse.unquote(input_path)
        input_path = os.path.normpath(input_path)
        
        # 2. ЖЕСТКАЯ ПРОВЕРКА СУЩЕСТВОВАНИЯ
        if not os.path.exists(input_path):
            print(f"[CRITICAL ERROR] Source file not found: {input_path}")
            return

        cap = cv2.VideoCapture(input_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 3. ПРОВЕРКА НА БИТЫЙ ФАЙЛ
        if total_frames == 0 or width == 0:
            print(f"[CRITICAL ERROR] OpenCV failed to read the video.")
            cap.release()
            return

        print(f"[DEPTH] Video: {width}x{height} | Frames: {total_frames}")

        # Настройка FFmpeg: Высококачественный MP4 (H.264, CRF 18)
        cmd_out = [
            FFMPEG_EXE, "-y",
            "-f", "rawvideo", "-pix_fmt", "gray16le", "-s", f"{width}x{height}", "-r", str(fps),
            "-i", "-",
            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
            output_path
        ]
        process_out = subprocess.Popen(cmd_out, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

        with torch.inference_mode():
            for _ in tqdm(range(total_frames), desc="Rendering depth map"):
                ret, frame = cap.read()
                if not ret: break

                # V2 принимает BGR кадр напрямую, сам делает ресайз и возвращает numpy массив
                depth = self.model.infer_image(frame)

                # Нормализация глубины (растягиваем контраст от 0 до 1)
                depth_min, depth_max = depth.min(), depth.max()
                if depth_max - depth_min > 0:
                    depth_normalized = (depth - depth_min) / (depth_max - depth_min)
                else:
                    depth_normalized = depth

                # Переводим в 16-битный формат (0 - 65535)
                depth_16bit = (depth_normalized * 65535.0).astype(np.uint16)

                # Отправляем сырые байты в FFmpeg
                process_out.stdin.write(depth_16bit.tobytes())

        # Закрываем всё строго после завершения генерации
        cap.release()
        process_out.stdin.close()
        process_out.wait()
        print(f"\n[DEPTH] Done! 10-bit depth map saved to: {output_path}")

# =====================================================================
# ФУНКЦИЯ ЗАПУСКА (Вызывается из main.py)
# =====================================================================
def run_depth(args_list):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    # Выбор размера модели (vits - быстро, vitb - качественно)
    parser.add_argument("--size", type=str, default="vits", choices=["vits", "vitb", "vitl"])
    args = parser.parse_args(args_list)
    
    worker = DepthWorker(model_size=args.size)
    worker.process(args.input, args.output)