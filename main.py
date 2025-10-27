from src import overlay
from src.tray import Tray

from PyQt6.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    overlay_widget = overlay.OverlayWidget(
        title="Lekcja",
        left_text="czas \u2192 następna",
        right_text="sala",
        progress=0.0
    )

    overlay_widget.show()

    # Najpierw tray, POTEM aktualizacje
    tray = Tray(app, overlay_widget)
    overlay_widget.tray_reference = tray

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
