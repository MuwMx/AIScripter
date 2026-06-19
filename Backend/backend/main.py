import argparse
import sys
import os
from pathlib import Path  


sys.path.append(os.path.dirname(os.path.abspath(__file__)))


import src.constants as cs

def main():
    parser = argparse.ArgumentParser(description="MyScripterAE - Portable AI Engine")
    parser.add_argument("task", choices=["rife", "clean", "depth", "bg"])
    args, remaining_args = parser.parse_known_args()

    
    
    
    
    path_sniffer = argparse.ArgumentParser(add_help=False)
    path_sniffer.add_argument("--input", type=str)
    path_sniffer.add_argument("--output", type=str)
    path_args, _ = path_sniffer.parse_known_args(remaining_args)

    if path_args.input:
        input_path = Path(path_args.input).resolve()
        
        if not input_path.exists():
            print(f"[CRITICAL ERROR] Source file not found at: {input_path}", file=sys.stderr)
            sys.exit(1)
        
        
        if "--input" in remaining_args:
            idx = remaining_args.index("--input")
            if idx + 1 < len(remaining_args):
                remaining_args[idx + 1] = str(input_path)

    if path_args.output:
        output_path = Path(path_args.output).resolve()
        
        
        if "--output" in remaining_args:
            idx = remaining_args.index("--output")
            if idx + 1 < len(remaining_args):
                remaining_args[idx + 1] = str(output_path)
    

    match args.task:
        case "rife":
            print("[MAIN] Starting RIFE module...")
            from src.rifearches.rife_worker import run_rife
            run_rife(remaining_args)
        case "clean":
            print("[MAIN] Starting SSIM Deduplication...")
            from src.dedup.clean_worker import run_clean
            run_clean(remaining_args)
        case "depth":
            print("[MAIN] Starting Depth Anything...")
            from src.depth.depth_worker import run_depth
            run_depth(remaining_args)
        case "bg":
            print("[MAIN] Starting BiRefNet...")
            from src.segment.bg_worker import run_bg
            run_bg(remaining_args)
        case _:
            print(f"[ERROR] Unknown task: {args.task}")
            sys.exit(1)

if __name__ == "__main__":
    os.environ.setdefault("FOR_DISABLE_CONSOLE_CTRL_HANDLER", "1")
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)