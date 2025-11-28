from src.overlay import OverlayWidget
from src.tray import Tray

from PyQt6.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    overlay_widget = OverlayWidget(
        title="Lekcja",
        left_text="czas → następna",
        right_text="sala",
        progress=0.0
    )

    overlay_widget.show()

    # Uruchom aktualizacje (upewnij się, że te metody istnieją!)
    if hasattr(overlay_widget, "start_minute_updates"):
        overlay_widget.start_minute_updates()
    else:
        print("Brak metody start_minute_updates w OverlayWidget")

    if hasattr(overlay_widget, "animateProgressTo"):
        overlay_widget.animateProgressTo(0.25)
    else:
        print("Brak metody animateProgressTo w OverlayWidget")

    sys.exit(app.exec())