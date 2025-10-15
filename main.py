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
    overlay.move(geo.width() - overlay.width() - 30, 30)
    overlay.show()

    # 🔄 animacja paska
    overlay.animateProgressTo(0.25)

    overlay.start_minute_updates("https://jsonplaceholder.typicode.com/users/1")

    sys.exit(app.exec())
