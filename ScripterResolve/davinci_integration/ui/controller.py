import re
from PySide6.QtCore import QObject, QThread, Signal, QSettings
from PySide6.QtWidgets import QFileDialog

class PipelineWorker(QThread):
    """Фоновый поток для выполнения тяжелых задач без фриза UI."""
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal(bool)

    def __init__(self, orchestrator, active_tasks, mode, ui_settings):
        super().__init__()
        self.orchestrator = orchestrator
        self.active_tasks = active_tasks
        self.mode = mode
        self.ui_settings = ui_settings

    def run(self):
        try:
            self.orchestrator.run_pipeline(
                self.active_tasks,
                self.mode,
                self.ui_settings,
                self.log_callback
            )
            self.finished_signal.emit(True)
        except Exception as e:
            self.log_signal.emit(f"[FATAL] Pipeline stopped due to error: {str(e)}")
            self.finished_signal.emit(False)

    def log_callback(self, msg):
        self.log_signal.emit(msg)
        match = re.search(r'(\d+)%', msg)
        if match:
            self.progress_signal.emit(int(match.group(1)))

class Controller(QObject):
    def __init__(self, view, orchestrator):
        super().__init__()
        self.view = view
        self.orchestrator = orchestrator
        self.worker = None

        
        self.settings = QSettings("MyScripter", "ResolveIntegration")
        
        
        import os
        saved_dir = self.settings.value("work_dir", "")
        if saved_dir and os.path.exists(saved_dir):
            self.view.set_work_dir(saved_dir)

        
        self.view.dir_btn.clicked.disconnect()  
        self.view.dir_btn.clicked.connect(self.change_workspace)

      
        self.view.run_btn.clicked.connect(self.start_pipeline)

    def start_pipeline(self):
        
        self.view.run_btn.setEnabled(False)
        self.view.progress_bar.setValue(0)
        self.view.log_console.clear()

        
        active_tasks = []
        if self.view.chk_clean.isChecked(): active_tasks.append("clean")
        if self.view.chk_rife.isChecked(): active_tasks.append("rife")

        
        if not active_tasks:
            self.view.append_log("[ERROR] Select at least one module (Clean or RIFE) to run pipeline!")
            self.view.run_btn.setEnabled(True)
            return

        mode = "Bake"
        work_dir = getattr(self.view, 'selected_dir', None)

        
        rife_text = self.view.rife_scale.currentText()
        scale_val = int(rife_text.replace("x", "")) 
        thresh_val = self.view.clean_slider.value() / 1000.0 

        ui_settings = {
            "work_dir": work_dir,
            "scale": scale_val,
            "threshold": thresh_val
        }

        
        self.worker = PipelineWorker(self.orchestrator, active_tasks, mode, ui_settings)
        self.worker.log_signal.connect(self.view.append_log)
        self.worker.progress_signal.connect(self.view.set_progress_smooth)
        self.worker.finished_signal.connect(self.on_pipeline_finished)
        self.worker.start()

    def on_pipeline_finished(self, success):
        self.view.run_btn.setEnabled(True)
        if success:
            self.view.progress_bar.setValue(100)

    def change_workspace(self):
        """Открывает диалог и сохраняет выбранный путь в настройки с валидацией папок."""
        folder = QFileDialog.getExistingDirectory(self.view, "Select Working Directory")
        if folder:
            
            forbidden = ["C:/", "C:/Program Files", "C:/Windows", "C:\\", "C:\\Program Files", "C:\\Windows"]
            if any(folder.startswith(f) for f in forbidden) or "AppData" in folder:
                self.view.append_log("[ERROR] Selection of root drives, system directories or AppData is forbidden!")
                return
                
            self.view.set_work_dir(folder)
            self.settings.setValue("work_dir", folder)  
    