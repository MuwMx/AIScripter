from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QGroupBox, QPlainTextEdit, QProgressBar, 
    QDoubleSpinBox, QSpinBox, QFileDialog, QCheckBox, QSlider
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Нативное чтение имени видеокарты из системы без использования Torch
        gpu_name = "Graphics Card"
        try:
            import subprocess
            cmd = 'powershell "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
            out = subprocess.check_output(cmd, shell=True, text=True)
            gpus = [line.strip() for line in out.splitlines() if line.strip()]
            if gpus:
                gpu_name = gpus[0]
                # Если в системе есть встроенное графическое ядро, приоритезируем дискретную карту
                for g in gpus:
                    if any(x in g.upper() for x in ["NVIDIA", "AMD", "GEFORCE", "RADEON"]):
                        gpu_name = g
                        break
        except:
            pass

        self.setWindowTitle(f"Resolve Scripter ({gpu_name})")
        self.setFixedSize(330, 480)

        # Главный виджет
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 4, 12, 12) # Срезали верхний отступ окна до 4px

        # Инструкция с четкими границами и переносом
        instruction = QLabel("⚠️ Place the playhead over the target clip on the active track")
        instruction.setWordWrap(True) # Жестко лочит текст внутри 330px, заставляя переноситься
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setStyleSheet("""
            QLabel {
                color: #ffb4ab; 
                font-weight: bold; 
                font-size: 11px;
                background-color: #251819; /* Мягкий темный красно-бордовый фон */
                border: 1px solid #422324;   /* Четкая граница блока */
                border-radius: 6px; 
                padding: 6px 8px;            /* Внутренние отступы, чтобы текст не лип к рамке */
            }
        """)
        layout.addWidget(instruction)

        # Выбор рабочей директории (Срезанная высота карточки)
        dir_group = QGroupBox("Workspace")
        dir_layout = QHBoxLayout(dir_group)
        dir_layout.setContentsMargins(5, 2, 5, 6) # Сильно зажали отступы по вертикали
        dir_layout.setSpacing(8)

        self.dir_label = QLabel("Not selected (will use plugin folder)")
        self.dir_label.setStyleSheet("color: #8e9199;")
        self.dir_btn = QPushButton("Browse")
        self.dir_btn.setFixedWidth(85)
        self.dir_btn.setFixedHeight(24) # Жесткий компактный размер для Browse
        self.dir_btn.clicked.connect(self.select_working_dir)

        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(self.dir_btn)
        layout.addWidget(dir_group)

       # Настройки пайплайна (Вложенная структура параметров)
        settings_group = QGroupBox("Pipeline Modules")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(6)

        # Модуль CLEAN и его ползунок под ним
        self.chk_clean = QCheckBox("Smart Clean (Dedup)")
        settings_layout.addWidget(self.chk_clean)

        self.clean_widget = QWidget()
        self.clean_widget.setMaximumHeight(0)
        clean_layout = QHBoxLayout(self.clean_widget)
        clean_layout.setContentsMargins(16, 0, 0, 0) # Сдвиг вправо под текст чекбокса
        
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

        # Модуль RIFE и его выпадающий список под ним
        self.chk_rife = QCheckBox("RIFE Interpolation")
        settings_layout.addWidget(self.chk_rife)

        self.rife_widget = QWidget()
        self.rife_widget.setMaximumHeight(0)
        rife_layout = QHBoxLayout(self.rife_widget)
        rife_layout.setContentsMargins(16, 0, 0, 0) # Сдвиг вправо под текст чекбокса
        
        rife_lbl = QLabel("Scale Factor:")
        self.rife_scale = QComboBox()
        self.rife_scale.addItems(["2x", "4x", "8x", "16x"])
        self.rife_scale.setCurrentText("4x")
        
        rife_layout.addWidget(rife_lbl)
        rife_layout.addWidget(self.rife_scale)
        settings_layout.addWidget(self.rife_widget)

        layout.addWidget(settings_group)
        # Кнопка запуска
        self.run_btn = QPushButton("Run Pipeline")
        self.run_btn.setObjectName("RunButton")
        self.run_btn.setFixedHeight(38)
        layout.addWidget(self.run_btn)

        # Прогресс-бар с жестким ограничением физической высоты
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)

        # Терминал логов (Фиксированная высота)
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(85) # Полностью убирает сплющивание
        layout.addWidget(self.log_console)

        # Инициализация плавных анимаций выезда панелей настроек
        self.clean_anim = QPropertyAnimation(self.clean_widget, b"maximumHeight")
        self.clean_anim.setDuration(200)
        self.clean_anim.setEasingCurve(QEasingCurve.InOutQuad)

        self.rife_anim = QPropertyAnimation(self.rife_widget, b"maximumHeight")
        self.rife_anim.setDuration(200)
        self.rife_anim.setEasingCurve(QEasingCurve.InOutQuad)

        # Анимация для плавного движения прогресс-бара
        self.bar_anim = QPropertyAnimation(self.progress_bar, b"value")
        self.bar_anim.setDuration(250) # Время сглаживания рывка в мс
        self.bar_anim.setEasingCurve(QEasingCurve.OutQuad)

        # Подключаем сигналы переключения чекбоксов
        self.chk_clean.toggled.connect(self.update_params_visibility)
        self.chk_rife.toggled.connect(self.update_params_visibility)
        

        # СТИЛИЗАЦИЯ: Полная зачистка нативного UI Windows
        self.setStyleSheet("""
            QMainWindow {
                background-color: #16161a;
            }
            QGroupBox {
                border: 1px solid #2c2c35;
                border-radius: 8px;
                margin-top: 4px;
                font-weight: bold;
                color: #d0bcf0;
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
                color: #e1e1e6;
            }
            QCheckBox {
                color: #e1e1e6;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox:hover {
                color: #d0bcf0;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #16161a;
                color: #e1e1e6;
                border: 1px solid #2c2c35;
                border-radius: 4px;
                padding: 3px 6px;
            }
            QPlainTextEdit {
                background-color: #0f0f12;
                border: 1px solid #2c2c35;
                border-radius: 8px;
                color: #a5a5b2;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
            QProgressBar {
                border: none;
                background-color: #23232a;
                height: 2px; /* Уменьшили толщину до минимума */
                border-radius: 1px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #d0bcf0;
                border-radius: 1px;
            }
            QPushButton {
                background-color: #2c2c35;
                color: #e1e1e6;
                border: 1px solid #3d3d49;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #353540;
                color: #d0bcf0; 
                border: 1px solid #524669;
            }
            QPushButton:pressed {
                background-color: #1c1c22;
                padding-top: 6px;    
                padding-bottom: 2px;  
            }
            QPushButton#RunButton {
                background-color: #d0bcf0;
                color: #16161a;
                font-weight: bold;
                border: none;
            }
            QPushButton#RunButton:hover {
                background-color: #bfaee3;
            }
            QPushButton#RunButton:pressed {
                background-color: #a393c8;
                padding-top: 8px;
                padding-bottom: 4px;
            }
            QPushButton#RunButton:disabled {
                background-color: #23232a;
                color: #4d4d56;
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
            self.dir_label.setStyleSheet("color: #e2e2e9;")

    def toggle_panel_anim(self, widget, animation, show, target_h=30):
        """Универсальная функция анимации выезда без сплющивания контента."""
        animation.setStartValue(widget.maximumHeight())
        animation.setEndValue(target_h if show else 0)
        animation.start()

    def update_params_visibility(self):
        show_clean = self.chk_clean.isChecked()
        show_rife = self.chk_rife.isChecked()
        
        # Плавно открываем настройки строго под активными чекбоксами
        self.toggle_panel_anim(self.clean_widget, self.clean_anim, show_clean)
        self.toggle_panel_anim(self.rife_widget, self.rife_anim, show_rife)

    def update_thresh_label(self, val):
        """Обновляет текст рядом со слайдером, переводя int обратно в формат 0.xxx"""
        self.clean_lbl_val.setText(f"0.{val}")

    def append_log(self, text):
        self.log_console.appendPlainText(text)
        # Автоскролл вниз
        scrollbar = self.log_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def set_work_dir(self, folder):
        """Устанавливает рабочую папку в интерфейс (вызывается при загрузке настроек)."""
        import os
        self.selected_dir = folder
        folder_name = os.path.basename(folder) or folder
        self.dir_label.setText(f"📁 RS_Cache Target: {folder_name}")
        self.dir_label.setStyleSheet("color: #e2e2e9;")

    def set_progress_smooth(self, value):
        """Плавное изменение прогресса без дерганий."""
        self.bar_anim.stop()
        self.bar_anim.setStartValue(self.progress_bar.value())
        self.bar_anim.setEndValue(value)
        self.bar_anim.start()