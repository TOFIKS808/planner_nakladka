import sys
import os
import json
import socket

# Dodaj katalog główny projektu do sys.path, aby moduł 'src' był widoczny
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from src.settings.settings_window import SettingsWindow

def main():
    app = QApplication(sys.argv)
    
    # Port komunikacyjny przekazany jako argument lub domyślny
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555
    
    # Uruchom okno w trybie standalone
    window = SettingsWindow(mode="standalone", server_port=port)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
