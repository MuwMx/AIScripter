import os
import sys
import argparse
import subprocess
import urllib.parse
import cv2
import numpy as np
import torch
import torch.nn.functional as F
from tqdm import tqdm




from src.constants import FFMPEG_EXE, WEIGHTS_DIR

RIFE_DIR = os.path.join(WEIGHTS_DIR, "rife4.6")


RIFE_WEIGHT_PATH = None
if os.path.exists(os.path.join(RIFE_DIR, "flownet.pkl")):
    RIFE_WEIGHT_PATH = os.path.join(RIFE_DIR, "flownet.pkl")
elif os.path.exists(os.path.join(RIFE_DIR, "rife46.pth")):
    RIFE_WEIGHT_PATH = os.path.join(RIFE_DIR, "rife46.pth")






device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tenGrid = {}
tenFlowDiv = {}

def warp(tenInput, tenFlow):
    k = (str(tenFlow.device), str(tenFlow.size()), str(tenFlow.dtype))
    if k not in tenGrid:
        H, W = tenFlow.shape[2], tenFlow.shape[3]
        tenHorizontal = (
            torch.linspace(-1.0, 1.0, W, device=tenFlow.device, dtype=torch.float32)
            .view(1, 1, 1, W)
            .expand(tenFlow.shape[0], -1, H, -1)
        )
        tenVertical = (
            torch.linspace(-1.0, 1.0, H, device=tenFlow.device, dtype=torch.float32)
            .view(1, 1, H, 1)
            .expand(tenFlow.shape[0], -1, -1, W)
        )
        tenGrid[k] = torch.cat([tenHorizontal, tenVertical], 1).to(tenFlow.dtype)
        tenFlowDiv[k] = torch.tensor(
            [2.0 / (W - 1), 2.0 / (H - 1)],
            dtype=tenFlow.dtype,
            device=tenFlow.device,
        ).view(1, 2, 1, 1)

    g = (tenGrid[k] + tenFlow * tenFlowDiv[k]).permute(0, 2, 3, 1)
    return torch.nn.functional.grid_sample(
        input=tenInput,
        grid=g,
        mode="bilinear",
        padding_mode="border",
        align_corners=True,
    )

import src.rifearches.IFNet_rife46 as rife_module
rife_module.warp = warp
from src.rifearches.IFNet_rife46 import IFNet




def pad_image(img_tensor, multiplier=32):
    h, w = img_tensor.shape[2], img_tensor.shape[3]
    pad_h = ((h - 1) // multiplier + 1) * multiplier - h
    pad_w = ((w - 1) // multiplier + 1) * multiplier - w
    if pad_h == 0 and pad_w == 0:
        return img_tensor, (0, 0, 0, 0)
    padding = (0, pad_w, 0, pad_h)
    return F.pad(img_tensor, padding), padding

def unpad_image(img_tensor, padding):
    if padding == (0, 0, 0, 0):
        return img_tensor
    _, pad_w, _, pad_h = padding
    h, w = img_tensor.shape[2], img_tensor.shape[3]
    return img_tensor[:, :, :h - pad_h, :w - pad_w]




class RifeWorker:
    def __init__(self):
        self.device = device
        print("[RIFE] Initializing RIFE 4.6 model (CUDA fp16)...")


        if RIFE_WEIGHT_PATH is None:
            print(f"\n[CRITICAL ERROR] Weight file not found!")
            print(f"Script looked for directory: {RIFE_DIR}")
            if os.path.exists(RIFE_DIR):
                print(f"Directory exists. Here is its content: {os.listdir(RIFE_DIR)}")
                print("Make sure the file is named strictly 'flownet.pkl' or 'rife46.pth' (without double extensions).")
            else:
                print("Directory 'rife4.6' does not exist at this path at all!")
            sys.exit(1)
            
        self.model = IFNet()
        
        state_dict = torch.load(RIFE_WEIGHT_PATH, map_location='cpu')
        if 'module' in list(state_dict.keys())[0]:
            state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
            
        self.model.load_state_dict(state_dict)
        self.model.eval().half().to(self.device)


    def _prepare_frame(self, frame_bytes, width, height):
        frame = np.frombuffer(frame_bytes, dtype=np.uint8).reshape((height, width, 3))
        tensor = torch.from_numpy(frame).permute(2, 0, 1).unsqueeze(0).to(self.device, non_blocking=True).half() / 255.0
        return pad_image(tensor)

    def process(self, input_path, output_path, scale):

        input_path = urllib.parse.unquote(input_path)
        input_path = os.path.normpath(input_path)
        

        if not os.path.exists(input_path):
            print(f"[CRITICAL ERROR] Source file not found: {input_path}")
            return

        cap = cv2.VideoCapture(input_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        if total_frames == 0 or width == 0:
            print(f"[CRITICAL ERROR] OpenCV failed to read the video.")
            return

        target_fps = fps * scale
        print(f"[RIFE] Video: {width}x{height} | Source FPS: {fps} | Target FPS: {target_fps} | Scale: {scale}x")

        cmd_in = [
            FFMPEG_EXE, "-i", input_path,
            "-f", "image2pipe", "-pix_fmt", "rgb24", "-vcodec", "rawvideo", "-"
        ]
        cmd_out = [
            FFMPEG_EXE, "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(target_fps),
            "-i", "-",
            "-c:v", "h264_nvenc", "-preset", "p6", "-cq", "18", "-pix_fmt", "yuv420p",
            output_path
        ]

        process_in = subprocess.Popen(cmd_in, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        process_out = subprocess.Popen(cmd_out, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

        frame_size = width * height * 3
        timesteps = [i / scale for i in range(1, scale)]

        raw_frame = process_in.stdout.read(frame_size)
        if not raw_frame: return

        I0, padding = self._prepare_frame(raw_frame, width, height)
        process_out.stdin.write(raw_frame)

        with torch.inference_mode():
             for _ in tqdm(range(total_frames - 1), desc="Frame interpolation"):
                raw_frame = process_in.stdout.read(frame_size)
                if not raw_frame: break
                
                I1, _ = self._prepare_frame(raw_frame, width, height)


                for t in timesteps:
                    t_tensor = torch.full((1, 1, I0.shape[2], I0.shape[3]), t, dtype=torch.float16, device=self.device)
                    

                    mid = self.model(I0, I1, t_tensor)
                    
                    mid = unpad_image(mid, padding)
                    mid_bytes = (mid[0].permute(1, 2, 0) * 255.0).byte().cpu().numpy().tobytes()
                    process_out.stdin.write(mid_bytes)


                process_out.stdin.write(raw_frame)
                I0.copy_(I1, non_blocking=True)

        process_in.stdout.close()
        process_out.stdin.close()
        process_in.wait()
        process_out.wait()
        print(f"\n[RIFE] Done! Saved to: {output_path}")




def run_rife(args_list):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--scale", type=int, default=2)
    args = parser.parse_args(args_list)
    
    worker = RifeWorker()
    worker.process(args.input, args.output, args.scale)