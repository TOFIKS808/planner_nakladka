from src import overlay
from PyQt6.QtWidgets import QApplication, QWidget
import sys



# ======== URUCHOMIENIE ========
if __name__ == "__main__":
    app = QApplication(sys.argv)

    overlay = overlay.OverlayWidget(
        title="Programowanie Proceduralne",
        left_text="30min →",
        right_text="Lab. Komputerowe",
        progress=0.0
    )

    # pozycja w prawym górnym rogu
    screen = app.primaryScreen()
    geo = screen.availableGeometry()
    overlay.show()

    # 🔄 animacja paska
    overlay.animateProgressTo(0.25)

    overlay.start_minute_updates()

    sys.exit(app.exec())
