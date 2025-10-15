import requests  # do pobierania danych z API
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont
from PyQt6.QtCore import Qt, QRectF, pyqtProperty, QPropertyAnimation, QEasingCurve, QTimer
import keyboard  # globalne skróty klawiaturowe

class OverlayWidget(QWidget):
    def __init__(self, title, left_text, right_text, progress=0.0):
        super().__init__()
        # Teksty z zewnątrz
        self.title = title
        self.left_text = left_text
        self.right_text = right_text

        # Styl
        self.bg_color = QColor(160, 160, 160)      # tło widgetu
        self.progress_color = QColor(40, 160, 60)  # zielony pasek
        self.text_color = QColor(255, 255, 255)    # tekst
        self.shadow_color = QColor(0, 0, 0, 100)   # cień pod literami
        self.radius = 15

        self._progress = progress  # prywatna zmienna do animacji

        # Okno
        self.setFixedSize(420, 100)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # Animacja paska
        self.anim = QPropertyAnimation(self, b"progress")
        self.anim.setDuration(1200)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Globalny skrót klawiszowy (Ctrl+Q -> toggle widoczności)
        keyboard.add_hotkey("ctrl+q", self.toggle_overlay)

    # ======== TOGGLE WIDOCZNOŚCI ========
    def toggle_overlay(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    # ======== ANIMOWANA WŁAŚCIWOŚĆ ========
    def getProgress(self):
        return self._progress

    def setProgress(self, value: float):
        self._progress = max(0.0, min(1.0, value))
        self.update()

    progress = pyqtProperty(float, fget=getProgress, fset=setProgress)

    # ======== ANIMACJA POSTĘPU ========
    def animateProgressTo(self, target_value: float):
        self.anim.stop()
        self.anim.setStartValue(self._progress)
        self.anim.setEndValue(max(0.0, min(1.0, target_value)))
        self.anim.start()

    # ======== MALOWANIE ========
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # === TŁO WŁAŚCIWE ===
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self.radius, self.radius)
        painter.fillPath(path, self.bg_color)

        # === SZARA PROWADNICA PASKA POSTĘPU ===
        bar_height = 8
        guide_path = QPainterPath()
        guide_path.moveTo(rect.x(), rect.y() + bar_height)
        guide_path.lineTo(rect.x(), rect.y() + self.radius)
        guide_path.quadTo(rect.x(), rect.y(), rect.x() + self.radius, rect.y())
        guide_path.lineTo(rect.x() + rect.width() - self.radius, rect.y())
        guide_path.quadTo(rect.x() + rect.width(), rect.y(), rect.x() + rect.width(), rect.y() + self.radius)
        guide_path.lineTo(rect.x() + rect.width(), rect.y() + bar_height)
        guide_path.closeSubpath()
        painter.fillPath(guide_path, QColor(100, 100, 100))  # szara prowadnica

        # === ZIELONY PASEK POSTĘPU ===
        progress_width = rect.width() * self._progress
        if self._progress > 0:
            progress_path = QPainterPath()
            progress_path.moveTo(rect.x(), rect.y() + bar_height)
            progress_path.lineTo(rect.x(), rect.y() + self.radius)
            progress_path.quadTo(rect.x(), rect.y(), rect.x() + self.radius, rect.y())

            # Prawy górny róg zaokrąglony tylko jeśli progress zbliża się do końca prowadnicy
            if progress_width >= rect.width() - self.radius:
                progress_path.lineTo(rect.x() + progress_width - self.radius, rect.y())
                progress_path.quadTo(rect.x() + progress_width, rect.y(), rect.x() + progress_width, rect.y() + self.radius)
            else:
                # w przeciwnym razie prosty prawy górny róg
                progress_path.lineTo(rect.x() + progress_width, rect.y())

            # Dolna krawędź
            progress_path.lineTo(rect.x() + progress_width, rect.y() + bar_height)
            progress_path.closeSubpath()
            painter.fillPath(progress_path, self.progress_color)

        # === TEKSTY Z CIENIEM ===
        painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Medium))
        # cień tytułu
        painter.setPen(self.shadow_color)
        painter.drawText(rect.adjusted(2, 22, 2, 0), Qt.AlignmentFlag.AlignHCenter, self.title)
        # główny tytuł
        painter.setPen(self.text_color)
        painter.drawText(rect.adjusted(0, 20, 0, 0), Qt.AlignmentFlag.AlignHCenter, self.title)

        # dolne napisy
        painter.setFont(QFont("Segoe UI", 12))
        # cień lewego
        painter.setPen(self.shadow_color)
        painter.drawText(rect.adjusted(27, 62, 2, 0), Qt.AlignmentFlag.AlignLeft, self.left_text)
        # cień prawego
        painter.drawText(rect.adjusted(-23, 62, -18, 0), Qt.AlignmentFlag.AlignRight, self.right_text)
        # właściwe teksty
        painter.setPen(self.text_color)
        painter.drawText(rect.adjusted(25, 60, 0, 0), Qt.AlignmentFlag.AlignLeft, self.left_text)
        painter.drawText(rect.adjusted(-25, 60, -20, 0), Qt.AlignmentFlag.AlignRight, self.right_text)

    # ======== CYKLICZNA AKTUALIZACJA ========
    def start_minute_updates(self, api_url):
        """Uruchamia cykliczną aktualizację co minutę z podanego API."""
        self.api_url = api_url
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.minute_update)
        self.update_timer.start(60 * 1000)  # co 60 sekund

        # od razu wywołaj po pierwszym uruchomieniu
        self.minute_update()

    def minute_update(self):
        """Funkcja wywoływana co minutę – pobiera dane z API i aktualizuje wszystkie napisy."""
        try:
            response = requests.get(self.api_url, timeout=10)
            data = response.json()  # zakładamy, że API zwraca JSON
        except Exception as e:
            print("Błąd pobierania danych z API:", e)
            return

        # Aktualizacja wszystkich napisów
        self.title = data.get("name", self.title)
        self.left_text = data.get("username", self.left_text) + " → |"
        self.right_text = data.get("email", self.right_text)
        progress = float(data.get("address", {}).get("geo", {}).get("lng", 0)) / 100

        # Aktualizacja paska postępu i przerysowanie widgetu
        self.animateProgressTo(progress)
        self.update()
