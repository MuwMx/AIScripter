from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QGroupBox, QPlainTextEdit, QProgressBar, 
    QDoubleSpinBox, QSpinBox, QFileDialog, QCheckBox, QSlider
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        
        gpu_name = "Graphics Card"
        try:
            import subprocess
            cmd = 'powershell "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
            out = subprocess.check_output(cmd, shell=True, text=True)
            gpus = [line.strip() for line in out.splitlines() if line.strip()]
            if gpus:
                gpu_name = gpus[0]
                
                for g in gpus:
                    if any(x in g.upper() for x in ["NVIDIA", "AMD", "GEFORCE", "RADEON"]):
                        gpu_name = g
                        break
        except:
            pass

        self.setWindowTitle(f"Resolve Scripter ({gpu_name})")
        self.setFixedSize(330, 480)

        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 4, 12, 12) 

        
        instruction = QLabel("⚠️ Place the playhead over the target clip on the active track")
        instruction.setWordWrap(True) 
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setStyleSheet("""
            QLabel {
                color: 
                font-weight: bold; 
                font-size: 11px;
                background-color: 
                border: 1px solid 
                border-radius: 6px; 
                padding: 6px 8px;            /* Внутренние отступы, чтобы текст не лип к рамке */
            }
        """)
        layout.addWidget(instruction)

        
        dir_group = QGroupBox("Workspace")
        dir_layout = QHBoxLayout(dir_group)
        dir_layout.setContentsMargins(5, 2, 5, 6) 
        dir_layout.setSpacing(8)

        self.dir_label = QLabel("Not selected (will use plugin folder)")
        self.dir_label.setStyleSheet("color: 
        self.dir_btn = QPushButton("Browse")
        self.dir_btn.setFixedWidth(85)
        self.dir_btn.setFixedHeight(24) 
        self.dir_btn.clicked.connect(self.select_working_dir)

        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(self.dir_btn)
        layout.addWidget(dir_group)

       
        settings_group = QGroupBox("Pipeline Modules")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(6)

        
        self.chk_clean = QCheckBox("Smart Clean (Dedup)")
        settings_layout.addWidget(self.chk_clean)

        self.clean_widget = QWidget()
        self.clean_widget.setMaximumHeight(0)
        clean_layout = QHBoxLayout(self.clean_widget)
        clean_layout.setContentsMargins(16, 0, 0, 0) 
        
        clean_lbl = QLabel("Threshold:")
        self.clean_slider = QSlider(Qt.Horizontal)
        self.clean_slider.setRange(900, 999)
        self.clean_slider.setValue(995)
        
        self.clean_lbl_val = QLabel("0.995")
        self.clean_lbl_val.setFixedWidth(40)
        
        self.clean_lbl_val = QLabel("0.995")
        self.clean_lbl_val.setFixedWidth(40)
        self.clean_lbl_val.setFixedHeight(26)
        self.clean_lbl_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.clean_slider.valueChanged.connect(self.update_thresh_label)
        
        clean_layout.addWidget(clean_lbl)
        clean_layout.addWidget(self.clean_slider)
        clean_layout.addWidget(self.clean_lbl_val)
        settings_layout.addWidget(self.clean_widget)

        
        self.chk_rife = QCheckBox("RIFE Interpolation")
        settings_layout.addWidget(self.chk_rife)

        self.rife_widget = QWidget()
        self.rife_widget.setMaximumHeight(0)
        rife_layout = QHBoxLayout(self.rife_widget)
        rife_layout.setContentsMargins(16, 0, 0, 0) 
        
        rife_lbl = QLabel("Scale Factor:")
        self.rife_scale = QComboBox()
        self.rife_scale.addItems(["2x", "4x", "8x", "16x"])
        self.rife_scale.setCurrentText("4x")
        
        rife_layout.addWidget(rife_lbl)
        rife_layout.addWidget(self.rife_scale)
        settings_layout.addWidget(self.rife_widget)

        layout.addWidget(settings_group)
        
        self.run_btn = QPushButton("Run Pipeline")
        self.run_btn.setObjectName("RunButton")
        self.run_btn.setFixedHeight(38)
        layout.addWidget(self.run_btn)

        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)

        
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(85) 
        layout.addWidget(self.log_console)

        
        self.clean_anim = QPropertyAnimation(self.clean_widget, b"maximumHeight")
        self.clean_anim.setDuration(200)
        self.clean_anim.setEasingCurve(QEasingCurve.InOutQuad)

        self.rife_anim = QPropertyAnimation(self.rife_widget, b"maximumHeight")
        self.rife_anim.setDuration(200)
        self.rife_anim.setEasingCurve(QEasingCurve.InOutQuad)

        
        self.bar_anim = QPropertyAnimation(self.progress_bar, b"value")
        self.bar_anim.setDuration(250) 
        self.bar_anim.setEasingCurve(QEasingCurve.OutQuad)

        
        self.chk_clean.toggled.connect(self.update_params_visibility)
        self.chk_rife.toggled.connect(self.update_params_visibility)
        

        
        self.setStyleSheet("""
            QMainWindow {
                background-color: 
            }
            QGroupBox {
                border: 1px solid 
                border-radius: 8px;
                margin-top: 4px;
                font-weight: bold;
                color: 
                padding-top: 14px;
                background-color: transparent;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                background: transparent;
                color: 
            }
            QCheckBox {
                color: 
                spacing: 8px;
                background: transparent;
            }
            QCheckBox:hover {
                color: 
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: 
                color: 
                border: 1px solid 
                border-radius: 4px;
                padding: 3px 6px;
            }
            QPlainTextEdit {
                background-color: 
                border: 1px solid 
                border-radius: 8px;
                color: 
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
            QProgressBar {
                border: none;
                background-color: 
                height: 2px; /* Уменьшили толщину до минимума */
                border-radius: 1px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: 
                border-radius: 1px;
            }
            QPushButton {
                background-color: 
                color: 
                border: 1px solid 
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: 
                color: 
                border: 1px solid 
            }
            QPushButton:pressed {
                background-color: 
                padding-top: 6px;    
                padding-bottom: 2px;  
            }
            QPushButton
                background-color: 
                color: 
                font-weight: bold;
                border: none;
            }
            QPushButton
                background-color: 
            }
            QPushButton
                background-color: 
                padding-top: 8px;
                padding-bottom: 4px;
            }
            QPushButton
                background-color: 
                color: 
                padding-top: 6px;
                padding-bottom: 6px;
            }
        """)

    def select_working_dir(self):
        """Открывает диалог выбора папки для сохранения кэша инпутов и аутпутов."""
        import os
        folder = QFileDialog.getExistingDirectory(self, "Select Working Directory", "C:/")
        if folder:
            self.selected_dir = folder
            folder_name = os.path.basename(folder) or folder
            self.dir_label.setText(f"📁 RS_Cache Target: {folder_name}")
            self.dir_label.setStyleSheet("color: 

    def toggle_panel_anim(self, widget, animation, show, target_h=30):
        """Универсальная функция анимации выезда без сплющивания контента."""
        animation.setStartValue(widget.maximumHeight())
        animation.setEndValue(target_h if show else 0)
        animation.start()

    def update_params_visibility(self):
        show_clean = self.chk_clean.isChecked()
        show_rife = self.chk_rife.isChecked()
        
        
        self.toggle_panel_anim(self.clean_widget, self.clean_anim, show_clean)
        self.toggle_panel_anim(self.rife_widget, self.rife_anim, show_rife)

    def update_thresh_label(self, val):
        """Обновляет текст рядом со слайдером, переводя int обратно в формат 0.xxx"""
        self.clean_lbl_val.setText(f"0.{val}")

    def append_log(self, text):
        self.log_console.appendPlainText(text)
        
        scrollbar = self.log_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def set_work_dir(self, folder):
        """Устанавливает рабочую папку в интерфейс (вызывается при загрузке настроек)."""
        import os
        self.selected_dir = folder
        folder_name = os.path.basename(folder) or folder
        self.dir_label.setText(f"📁 RS_Cache Target: {folder_name}")
        self.dir_label.setStyleSheet("color: 

    def set_progress_smooth(self, value):
        """Плавное изменение прогресса без дерганий."""
        self.bar_anim.stop()
        self.bar_anim.setStartValue(self.progress_bar.value())
        self.bar_anim.setEndValue(value)
        self.bar_anim.start()