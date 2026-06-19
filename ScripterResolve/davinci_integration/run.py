import os
import sys
import ctypes

print("[DEBUG] 1. Скрипт запущен")

try:
    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    print(f"[DEBUG] 1.5. Запущено от имени Администратора: {is_admin}")
except Exception:
    print("[DEBUG] 1.5. Не удалось проверить права администратора")


RESOLVE_PATH = r"C:\Program Files\Blackmagic Design\DaVinci Resolve"
if os.path.exists(RESOLVE_PATH):
    
    os.environ["PATH"] = RESOLVE_PATH + os.pathsep + os.environ.get("PATH", "")
    
    ctypes.windll.kernel32.SetDllDirectoryW(RESOLVE_PATH)
    
    os.environ["RESOLVE_SCRIPT_API"] = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
    os.environ["RESOLVE_SCRIPT_LIB"] = os.path.join(RESOLVE_PATH, "fusionscript.dll")
    print("[DEBUG] 2. Окружение и системный PATH для DaVinci Resolve успешно настроены")


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

print("[DEBUG] 5. Пробуем импортировать модули репозитория...")
from davinci_integration.repository.resolve_repo import ResolveRepository
print("[DEBUG] 6. Репозиторий импортирован успешно")


import glob
possible_site_packages = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python*\Lib\site-packages"),
    r"C:\Program Files\Python*\Lib\site-packages"
]
for mask in possible_site_packages:
    for path in glob.glob(mask):
        if path not in sys.path:
            sys.path.append(path)

print("[DEBUG] 3. Пробуем импортировать PySide6...")
from PySide6.QtWidgets import QApplication
print("[DEBUG] 4. PySide6 импортирован успешно")

from davinci_integration.services.vfx_orchestrator import VFXOrchestrator
from davinci_integration.ui.view import MainWindow
from davinci_integration.ui.controller import Controller

def main():
    print("[DEBUG] 7. Вход в функцию main()")
    app = QApplication(sys.argv)

    qss_path = os.path.join(CURRENT_DIR, "ui", "stylesheet.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    print("[DEBUG] 8. Инициализация ResolveRepository...")
    try:
        repo = ResolveRepository()
    except Exception as e:
        print(f"[DEBUG] Ошибка репозитория (но работаем дальше): {e}")
        repo = None 

    orchestrator = VFXOrchestrator(repo)
    view = MainWindow()
    controller = Controller(view, orchestrator)

    print("[DEBUG] 9. Вызов окна интерфейса")
    view.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()