import os
import sys
import argparse
import subprocess
import urllib.parse
import cv2
import torch
import numpy as np
from tqdm import tqdm
from torchvision import transforms
from PIL import Image
import torch.nn.functional as F




from src.constants import FFMPEG_EXE, WEIGHTS_DIR

BG_DIR = os.path.join(WEIGHTS_DIR, "bg")


from transformers import AutoModelForImageSegmentation




class BGWorker:
    def __init__(self, weight_filename):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[BG REMOVAL] Initializing BiRefNet on {self.device.type.upper()}...")

        weight_path = os.path.join(BG_DIR, weight_filename)
        if not os.path.exists(weight_path):
            print(f"\n[CRITICAL ERROR] Weight file not found: {weight_path}")
            sys.exit(1)


        self.model = AutoModelForImageSegmentation.from_pretrained(
            'ZhengPeng7/BiRefNet', 
            trust_remote_code=True
        )


        print(f"[BG REMOVAL] Loading custom weights: {weight_filename}...")
        if weight_filename.endswith('.safetensors'):
            from safetensors.torch import load_file
            state_dict = load_file(weight_path)
        else:
            state_dict = torch.load(weight_path, map_location='cpu')
            

        if 'state_dict' in state_dict:
            state_dict = state_dict['state_dict']
        elif 'model' in state_dict:
            state_dict = state_dict['model']


        clean_state_dict = {}
        for k, v in state_dict.items():

            new_key = k.replace("module._orig_mod.", "")
            new_key = new_key.replace("module.", "")
            new_key = new_key.replace("base_model.", "")
            

            if "squeeze_0" in new_key:
                new_key = new_key.replace("squeeze_0", "squeeze_module.0")
                
            clean_state_dict[new_key] = v



        self.model.load_state_dict(clean_state_dict, strict=False)
        print("[BG REMOVAL] ToonOut weights successfully adapted and loaded into CUDA!")

        self.model = self.model.to(self.device).eval().half()


        self.transform = transforms.Compose([
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    def process(self, input_path, output_path):

        input_path = urllib.parse.unquote(input_path)
        input_path = os.path.normpath(input_path)
        

        if not os.path.exists(input_path):
            print(f"[CRITICAL ERROR] Source file not found: {input_path}")
            print("Check if After Effects successfully rendered the chunk.")
            return

        print(f"[BG REMOVAL] Normalized input path: {input_path}")

        cap = cv2.VideoCapture(input_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        

        if total_frames == 0 or width == 0:
            print(f"[CRITICAL ERROR] OpenCV failed to read the video. The file might be corrupted.")
            cap.release()
            return

        print(f"[BG REMOVAL] Video: {width}x{height} | Frames: {total_frames}")


        cmd_out = [
            FFMPEG_EXE, "-y",
            "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}", "-r", str(fps),
            "-i", "-",
            "-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-vendor", "apl0",
            output_path
        ]
        
        process_out = subprocess.Popen(cmd_out, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

        with torch.inference_mode(), torch.autocast(device_type="cuda", dtype=torch.float16):
            for _ in tqdm(range(total_frames), desc="Background removal"):
                ret, frame = cap.read()
                if not ret: break


                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                input_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)


                preds = self.model(input_tensor)[-1].sigmoid().cpu()
                pred = preds[0].squeeze()


                pred_resized = F.interpolate(
                    pred.unsqueeze(0).unsqueeze(0), 
                    size=(height, width), 
                    mode='bilinear', 
                    align_corners=False
                ).squeeze()

                mask = (pred_resized.numpy() * 255.0).astype(np.uint8)


                rgba_frame = np.zeros((height, width, 4), dtype=np.uint8)
                rgba_frame[..., :3] = frame_rgb
                rgba_frame[..., 3] = mask

                process_out.stdin.write(rgba_frame.tobytes())

        cap.release()
        process_out.stdin.close()
        process_out.wait()
        print(f"\n[BG REMOVAL] Done! Transparent video saved to: {output_path}")




def run_bg(args_list):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--weight", type=str, default="toonout.pth")
    args = parser.parse_args(args_list)
    
    worker = BGWorker(weight_filename=args.weight)
    worker.process(args.input, args.output)