import os
import sys
import json
import subprocess
import argparse
import math
import urllib.parse
import cv2
import numpy as np
import torch
import torch.nn.functional as F
from tqdm import tqdm




from src.constants import FFMPEG_EXE




def gaussian_window(window_size, sigma):
    gauss = torch.tensor([math.exp(-(x - window_size//2)**2 / float(2 * sigma**2)) for x in range(window_size)])
    return gauss / gauss.sum()

def create_window(window_size, channel):
    _1D_window = gaussian_window(window_size, 1.5).unsqueeze(1)
    _2D_window = _1D_window.mm(_1D_window.t()).float().unsqueeze(0).unsqueeze(0)
    window = _2D_window.expand(channel, 1, window_size, window_size).contiguous()
    return window

def calculate_ssim(img1, img2, window, window_size=11):
    channel = img1.size(1)
    mu1 = F.conv2d(img1, window, padding=window_size//2, groups=channel)
    mu2 = F.conv2d(img2, window, padding=window_size//2, groups=channel)
    mu1_sq, mu2_sq, mu1_mu2 = mu1.pow(2), mu2.pow(2), mu1 * mu2
    sigma1_sq = F.conv2d(img1 * img1, window, padding=window_size//2, groups=channel) - mu1_sq
    sigma2_sq = F.conv2d(img2 * img2, window, padding=window_size//2, groups=channel) - mu2_sq
    sigma12 = F.conv2d(img1 * img2, window, padding=window_size//2, groups=channel) - mu1_mu2
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    return ssim_map.mean().item()




class DedupWorker:
    def __init__(self, threshold=0.995, sample_size=224):
        self.device = torch.device("cuda")
        self.threshold = threshold
        self.sample_size = sample_size
        self.window_size = 11
        self.window = create_window(self.window_size, 3).to(self.device).half()
        

        print(f"[CLEAN] Initializing SSIM (CUDA fp16). Threshold: {self.threshold}")

    def _prepare_frame(self, frame_bytes, width, height):
        frame = np.frombuffer(frame_bytes, dtype=np.uint8).reshape((height, width, 3))
        tensor = torch.from_numpy(frame).permute(2, 0, 1).unsqueeze(0).to(self.device, non_blocking=True).half() / 255.0
        tensor_resized = F.interpolate(tensor, size=(self.sample_size, self.sample_size), mode="nearest")
        return tensor_resized, frame_bytes

    def process(self, input_path, output_video, output_json):

        input_path = urllib.parse.unquote(input_path)
        input_path = os.path.normpath(input_path)
        

        if not os.path.exists(input_path):
            print(f"[CRITICAL ERROR] Source file not found: {input_path}")
            print("Check if After Effects successfully rendered the chunk.")
            return

        print(f"[CLEAN] Normalized input path: {input_path}")


        cap = cv2.VideoCapture(input_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()


        if total_frames == 0 or width == 0:
            print(f"[CRITICAL ERROR] OpenCV failed to read the video. The file might be corrupted.")
            return


        print(f"[CLEAN] Video: {width}x{height} | Frames: {total_frames}")

        cmd_in = [
            FFMPEG_EXE, "-i", input_path,
            "-f", "image2pipe", "-pix_fmt", "rgb24", "-vcodec", "rawvideo", "-"
        ]
        cmd_out = [
            FFMPEG_EXE, "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps),
            "-i", "-",
            "-c:v", "h264_nvenc", "-preset", "p7", "-cq", "15", "-pix_fmt", "yuv420p",
            output_video
        ]

        process_in = subprocess.Popen(cmd_in, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        process_out = subprocess.Popen(cmd_out, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

        frame_size = width * height * 3
        unique_indices = []
        duplicates_count = 0

        raw_frame = process_in.stdout.read(frame_size)
        if not raw_frame: return

        prev_tensor, _ = self._prepare_frame(raw_frame, width, height)
        process_out.stdin.write(raw_frame)
        unique_indices.append(0)

        with torch.inference_mode():
            for i in tqdm(range(1, total_frames), desc="Finding duplicates"):
                raw_frame = process_in.stdout.read(frame_size)
                if not raw_frame: break
                
                curr_tensor, _ = self._prepare_frame(raw_frame, width, height)
                score = calculate_ssim(prev_tensor, curr_tensor, self.window, self.window_size)

                if score < self.threshold:
                    process_out.stdin.write(raw_frame)
                    unique_indices.append(i)
                    prev_tensor.copy_(curr_tensor, non_blocking=True)
                else:
                    duplicates_count += 1

        process_in.stdout.close()
        process_out.stdin.close()
        process_in.wait()
        process_out.wait()


        print(f"\n[CLEAN] Done! Duplicates removed: {duplicates_count}")

        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump({
                "original_fps": fps,
                "total_original_frames": total_frames,
                "unique_frames_count": len(unique_indices),
                "duplicates_removed": duplicates_count,
                "frames": unique_indices
            }, f, indent=4)

def run_clean(args_list):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--json", type=str, required=True)
    parser.add_argument("--threshold", type=float, default=0.995)
    args = parser.parse_args(args_list)
    
    worker = DedupWorker(threshold=args.threshold)
    worker.process(args.input, args.output, args.json)