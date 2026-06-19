import os
import sys
import builtins

# =====================================================================
# БРОНЕБОЙНАЯ ИНИЦИАЛИЗАЦИЯ API DAVINCI RESOLVE
# =====================================================================
RESOLVE_BIN_DIR = r"C:\Program Files\Blackmagic Design\DaVinci Resolve"
RESOLVE_MODULES_DIR = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"

dvr_script = None

# Если мы внутри Резалва, то встроенный объект уже есть, внешние DLL не трогаем
if not hasattr(builtins, "resolve"):
    if os.path.exists(RESOLVE_MODULES_DIR) and RESOLVE_MODULES_DIR not in sys.path:
        sys.path.append(RESOLVE_MODULES_DIR)

    try:
        import DaVinciResolveScript as dvr_script
    except ImportError:
        print("[REPO ERROR] DaVinciResolveScript.py not found.")
        sys.exit(1)

# =====================================================================
# КАСТОМНЫЕ ИСКЛЮЧЕНИЯ
# =====================================================================
class ResolveAPIError(Exception):
    """Custom exception for silent DaVinci API failures."""
    pass

# =====================================================================
# СЛОЙ ДАННЫХ: RESOLVE REPOSITORY
# =====================================================================
class ResolveRepository:
    def __init__(self):
        print("[REPO DEBUG] Initializing DaVinci Resolve API...")
        self.resolve = dvr_script.scriptapp("Resolve")
        if not self.resolve:
            raise ResolveAPIError("Failed to connect to DaVinci Resolve. Is it running?")

        self.project_manager = self.resolve.GetProjectManager()
        if not self.project_manager:
            raise ResolveAPIError("Failed to get Project Manager.")

        self.project = self.project_manager.GetCurrentProject()
        if not self.project:
            raise ResolveAPIError("Failed to get Current Project.")

        self.timeline = self.project.GetCurrentTimeline()
        if not self.timeline:
            raise ResolveAPIError("No active timeline found. Please open a timeline.")
            
        self.media_pool = self.project.GetMediaPool()
        print("[REPO DEBUG] API Initialization successful.")

    def validate_project(self):
        """Проверяет, сохранен ли проект (защита от потери данных)."""
        project_name = self.project.GetName()
        print(f"[REPO DEBUG] Validating project name: '{project_name}'")
        
        if project_name == "Untitled Project" or project_name == "":
            raise ResolveAPIError("Project is not saved! Please save your project (Ctrl+S) before running the AI Pipeline.")
        
        return project_name

    def get_clip_metadata(self):
        """Собирает данные о клипе под плейхедом."""
        print("[REPO DEBUG] Fetching clip under playhead...")
        clip = self.timeline.GetCurrentVideoItem()
        if not clip:
            raise ResolveAPIError("No clip found under the playhead. Please place the playhead over the target clip on the active track.")

        clip_name = clip.GetName()
        print(f"[REPO DEBUG] Found clip: '{clip_name}'")

        media_pool_item = clip.GetMediaPoolItem()
        if not media_pool_item:
            raise ResolveAPIError(f"Failed to get Media Pool Item for clip '{clip_name}'.")

        file_path = media_pool_item.GetClipProperty("File Path") or ""
        
        # Если это обычный файл и путь указан, но файла нет на SSD — выдаем ошибку.
        # Если путь пустой (Компаунды, Мультикамы, Текст), пропускаем — Резалв сам запечет его на рендере.
        if file_path and not os.path.exists(file_path):
            raise ResolveAPIError(f"Source file path detected but file is missing on disk for clip '{clip_name}': {file_path}")

        start_frame = clip.GetStart()
        end_frame = clip.GetEnd()
        duration_frames = end_frame - start_frame
        source_start_frame = clip.GetLeftOffset()

        # Получаем FPS таймлайна
        fps_setting = self.project.GetSetting("timelineFrameRate")
        try:
            timeline_fps = float(fps_setting)
        except (ValueError, TypeError):
            raise ResolveAPIError(f"Failed to parse timeline FPS: {fps_setting}")

        # ФИКС FPS: Получаем родной FPS самого видеофайла из медиапула
        source_fps_str = media_pool_item.GetClipProperty("FPS")
        try:
            source_fps = float(source_fps_str)
        except (ValueError, TypeError):
            source_fps = timeline_fps  # если не нашли, берем как на таймлайне

        print(f"[REPO DEBUG] Clip Metadata -> Path: {file_path} | Timeline FPS: {timeline_fps} | Source FPS: {source_fps}")

        return {
            "clip_obj": clip,
            "file_path": file_path,
            "start_frame": start_frame,
            "end_frame": end_frame,
            "source_start_frame": source_start_frame,
            "duration_frames": duration_frames,
            "fps": timeline_fps,    # сохраняем для совместимости с Bake
            "source_fps": source_fps # передаем родной фреймрейт для Raw
        }

    def import_and_replace(self, output_file_path, original_clip_obj, start_frame, duration_frames):
        """Импортирует готовый файл на новый трек и отключает оригинал."""
        print(f"[REPO DEBUG] Importing AI result into Media Pool: {output_file_path}")
        
        if not os.path.exists(output_file_path):
            raise ResolveAPIError(f"Output file does not exist: {output_file_path}")

        imported_items = self.media_pool.ImportMedia([output_file_path])
        if not imported_items or len(imported_items) == 0:
            raise ResolveAPIError("Failed to import the processed file into the Media Pool.")
        
        new_media_item = imported_items[0]
        print("[REPO DEBUG] File successfully imported to Media Pool.")

        # ФИКС РАСТЯГИВАНИЯ: Узнаем реальное количество кадров импортированного ИИ-файла
        try:
            actual_frames_str = new_media_item.GetClipProperty("Frames")
            actual_duration = int(actual_frames_str)
            print(f"[REPO DEBUG] AI file actual duration: {actual_duration} frames")
        except Exception as e:
            print(f"[REPO WARNING] Failed to get AI file frames: {e}. Falling back to original duration.")
            actual_duration = int(duration_frames)

        # УМНЫЙ ПОДБОР ТРЕКА: Ищем существующий пустой трек сверху вниз
        track_count = self.timeline.GetTrackCount("video")
        target_track_index = None
        
        for i in range(track_count, 0, -1):
            items = self.timeline.GetItemListInTrack("video", i)
            if items is not None and len(items) == 0:
                target_track_index = i
                print(f"[REPO DEBUG] Reusing empty video track #{target_track_index}")
                break
        
        # Если пустого трека не нашлось, создаем новый верхний
        if target_track_index is None:
            if not self.timeline.AddTrack("video"):
                raise ResolveAPIError("Failed to add a new video track.")
            target_track_index = self.timeline.GetTrackCount("video")
            print(f"[REPO DEBUG] Created new video track #{target_track_index}")
        timeline_start_frame = self.timeline.GetStartFrame()
        
        print(f"[REPO DEBUG] Timeline starts at frame: {timeline_start_frame}")
        print(f"[REPO DEBUG] Appending clip to track {target_track_index} at frame {start_frame}...")
        
        clip_info = {
            "mediaPoolItem": new_media_item,
            "startFrame": 0,
            "endFrame": actual_duration, 
            "trackIndex": int(target_track_index),
            "recordFrame": int(start_frame)
        }
        
        if not self.media_pool.AppendToTimeline([clip_info]):
            raise ResolveAPIError("Failed to append the new clip to the timeline.")

        print("[REPO DEBUG] Disabling original clip...")
        # ФИКС КРАША: Используем SetProperty вместо несуществующего SetSetting
        if not original_clip_obj.SetProperty("VideoDisable", True):
            print("[REPO WARNING] Failed to disable the original clip via API. You may need to hide it manually.")

        print("[REPO DEBUG] Import and replace completed successfully!")
        return True