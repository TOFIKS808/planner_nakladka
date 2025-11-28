import sys
import os

# Dodaj katalog główny projektu do sys.path, aby moduł 'src' był widoczny
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from src.tray import Tray

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Port komunikacyjny przekazany jako argument lub domyślny
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555
    
    # Uruchom tray w trybie standalone
    tray = Tray(mode="standalone", server_port=port)
    tray.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
