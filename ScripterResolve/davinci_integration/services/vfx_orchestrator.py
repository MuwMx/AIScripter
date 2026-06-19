import os
import sys
import time
import subprocess
import glob
from pathlib import Path


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))  


ROAMING_ROOT = os.path.join(os.environ['APPDATA'], "MyScripterAE")


FFMPEG_EXE = os.path.join(ROAMING_ROOT, "ffmpeg_shared", "ffmpeg.exe")
PYTHON_EXE = os.path.join(ROAMING_ROOT, "python.exe")
BACKEND_MAIN = os.path.join(ROAMING_ROOT, "backend", "main.py")

class VFXOrchestrator:
    def __init__(self, repo):
        self.repo = repo  

    def run_pipeline(self, task_type, mode, ui_settings, log_callback):
        """
        Главный метод пайплайна. Вызывается из QThread в контроллере UI.
        """
        try:
            log_callback(f"[ORCHESTRATOR] Starting pipeline. Active modules: {', '.join(task_type).upper()}")

            
            clip_data = self.repo.get_clip_metadata()
            
            
            project_name = self.repo.project.GetName()
            if project_name == "Untitled Project":
                raise RuntimeError("Save your project in DaVinci (Ctrl+S) before running the pipeline!")

            
            base_work_dir = Path(ui_settings.get("work_dir") or LOCAL_ROOT)
            cache_base_dir = base_work_dir / "RS_Cache" / project_name / "Cache"
            
            input_dir = cache_base_dir / "_Input"
            output_dir = cache_base_dir / "_Output"
            
            input_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = int(time.time())
            chunk_name = f"chunk_{timestamp}.mp4"
            input_chunk_path = str(input_dir / chunk_name)

            
            
            
            log_callback("[ORCHESTRATOR] Bake Mode: Creating Render Job in Resolve...")
            project = self.repo.project
            
           
            project.SetRenderSettings({
                "TargetDir": str(input_dir),
                "CustomName": chunk_name.replace(".mp4", ""),
                "ExportVideo": True,
                "ExportAudio": False,
                "VideoCodec": "H264",
                "VideoFormat": "mp4",
                "VideoQuality": 15000,  
                "RenderMode": 0,        
                "SelectAllFrames": False,
                "MarkIn": int(clip_data["start_frame"]),
                "MarkOut": int(clip_data["end_frame"])
            })
            
            job_id = project.AddRenderJob()
            if not job_id:
                raise RuntimeError("Failed to add Render Job to DaVinci Deliver page.")
            
            log_callback(f"[ORCHESTRATOR] Render Job {job_id} added. Starting render...")
            project.StartRendering(job_id)
            
            
            while True:
                status = project.GetRenderJobStatus(job_id)
                state = status.get("JobStatus", "")
                if state == "Complete":
                    log_callback("[ORCHESTRATOR] Render completed successfully.")
                    break
                elif state in ["Failed", "Cancelled"]:
                    project.DeleteRenderJob(job_id)
                    raise RuntimeError(f"Render Job failed or was cancelled. Status: {state}")
                time.sleep(0.5)
            
            project.DeleteRenderJob(job_id)
            log_callback("[ORCHESTRATOR] Render Job removed from Deliver queue.")

            
            actual_files = list(input_dir.glob(f"chunk_{timestamp}*"))
            if actual_files:
                input_chunk_path = str(actual_files[0])
                log_callback(f"[ORCHESTRATOR] Actual rendered file detected: {actual_files[0].name}")
            else:
                raise RuntimeError(f"Render finished, but no source file found in {input_dir}")

            
            current_processing_file = input_chunk_path
            final_output_path = None

            
            
            
            if "clean" in task_type:
                clean_out = str(output_dir / f"AIScripter_{timestamp}_clean_out.mp4")
                json_out = str(output_dir / f"frames_{timestamp}.json")
                
                log_callback("[ORCHESTRATOR] Launching AI Backend for CLEAN...")
                args = [PYTHON_EXE, "-u", BACKEND_MAIN, "clean", "--input", current_processing_file, "--output", clean_out, "--json", json_out, "--threshold", str(ui_settings.get("threshold", 0.995))]
                
                process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in process.stdout:
                    log_callback(line.strip())
                process.wait()
                
                if process.returncode != 0:
                    raise RuntimeError(f"Clean module crashed with code {process.returncode}")
                
                current_processing_file = clean_out
                final_output_path = clean_out

            
            
            
            if "rife" in task_type:
                rife_out = str(output_dir / f"AIScripter_{timestamp}_rife_out.mp4")
                
                log_callback("[ORCHESTRATOR] Launching AI Backend for RIFE...")
                args = [PYTHON_EXE, "-u", BACKEND_MAIN, "rife", "--input", current_processing_file, "--output", rife_out, "--scale", str(ui_settings.get("scale", 4))]
                
                process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in process.stdout:
                    log_callback(line.strip())
                process.wait()
                
                if process.returncode != 0:
                    raise RuntimeError(f"RIFE module crashed with code {process.returncode}")
                
                final_output_path = rife_out

            
            
            
            if final_output_path and os.path.exists(final_output_path):
                log_callback("[ORCHESTRATOR] AI Chaining complete. Importing final result to DaVinci...")
                self.repo.import_and_replace(
                    final_output_path, 
                    clip_data["clip_obj"], 
                    clip_data["start_frame"], 
                    clip_data["duration_frames"]
                )
            else:
                raise RuntimeError("Pipeline finished but no final output file was generated.")

            log_callback("\n[SUCCESS] Pipeline completed successfully!")

        except Exception as e:
            log_callback(f"\n[CRITICAL ERROR] {str(e)}")
            raise e
        finally:
            log_callback("[ORCHESTRATOR] Starting garbage cleanup...")
            
            if 'input_chunk_path' in locals() and os.path.exists(input_chunk_path):
                try: os.remove(input_chunk_path)
                except: pass
            
            
            if "clean" in task_type and "rife" in task_type:
                clean_temp = str(output_dir / f"AIScripter_{timestamp}_clean_out.mp4")
                if os.path.exists(clean_temp):
                    try: os.remove(clean_temp)
                    except: pass

            
            if "clean" in task_type:
                json_temp = str(output_dir / f"frames_{timestamp}.json")
                if os.path.exists(json_temp):
                    try: os.remove(json_temp)
                    except: pass
            
            log_callback("[ORCHESTRATOR] Temporary cache cleared successfully.")