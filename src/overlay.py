import requests
from PyQt6.QtWidgets import QWidget, QSlider, QPushButton, QLabel, QVBoxLayout, QCheckBox, QSpacerItem, QSizePolicy, QMessageBox, QApplication
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont, QMouseEvent, QCursor
from PyQt6.QtCore import Qt, QRectF, pyqtProperty, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QGuiApplication
import keyboard
import json, os

class OverlayWidget(QWidget):
    def __init__(self, title, left_text, right_text, progress=0.0):
        super().__init__()

        # Ścieżka pliku ustawień
        if os.name == "nt":
            base_dir = os.getenv("APPDATA")
            self.config_dir = os.path.join(base_dir, "OverlayApp")
        else:
            base_dir = os.path.expanduser("~/.config")
            self.config_dir = os.path.join(base_dir, "overlay")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, "settings.json")

        # Teksty
        self.title = title
        self.left_text = left_text
        self.right_text = right_text

        # Styl
        self.bg_color = QColor(31, 35, 43)
        self.progress_color = QColor(46, 139, 87)
        self.text_color = QColor(255, 255, 255)
        self.shadow_color = QColor(0, 0, 0, 100)
        self.radius = 15

        # Stan overlay
        self._progress = progress
        self._settings_mode = False
        self._clickthrough_enabled = True

        # Rozmiar początkowy
        self.original_width = 420
        self.original_height = 100
        self.scale_factor = 1.0
        self.resize(self.original_width, self.original_height)

        # Okno
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # Animacja paska
        self.anim = QPropertyAnimation(self, b"progress")
        self.anim.setDuration(1200)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Skrót klawiszowy
        keyboard.add_hotkey("ctrl+q", self.toggle_overlay)

        # === Panel ustawień ===
        self.settings_panel = QWidget(self)
        r, g, b, a = self.bg_color.getRgb()
        self.settings_panel.setStyleSheet(
            f"background-color: rgba({r}, {g}, {b}, 255); border-radius: {self.radius}px;"
        )

        layout = QVBoxLayout(self.settings_panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)

        header = QLabel("⚙️ Ustawienia nakładki")
        header.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(header)

        # Suwak przezroczystości
        label = QLabel("Przezroczystość nakładki:")
        label.setStyleSheet("color: white; font-size: 13px;")
        layout.addWidget(label)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setMinimum(30)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.update_opacity)
        self.opacity_slider.setStyleSheet(self._slider_style())
        layout.addWidget(self.opacity_slider)

        # Suwak skalowania
        scale_label = QLabel("Skalowanie nakładki (40–100%):")
        scale_label.setStyleSheet("color: white; font-size: 13px;")
        layout.addWidget(scale_label)
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setMinimum(40)
        self.scale_slider.setMaximum(100)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self.update_scale)
        self.scale_slider.setStyleSheet(self._slider_style())
        layout.addWidget(self.scale_slider)

        # Checkbox click-through
        self.clickthrough_checkbox = QCheckBox("Pozwól klikać przez nakładkę")
        self.clickthrough_checkbox.setChecked(True)
        self.clickthrough_checkbox.setStyleSheet("""
            QCheckBox { color: white; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #3CB371; background-color: transparent; }
            QCheckBox::indicator:checked { background-color: #3CB371; border: 2px solid #2E8B57; }
        """)
        self.clickthrough_checkbox.stateChanged.connect(self.toggle_clickthrough_option)
        layout.addWidget(self.clickthrough_checkbox)

        layout.addSpacerItem(QSpacerItem(10, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.back_button = QPushButton("← Powrót")
        self.back_button.clicked.connect(self.toggle_settings)
        self.back_button.setStyleSheet("""
            QPushButton { background-color: #2E8B57; color: white; border: none; padding: 8px 12px; border-radius: 10px; font-size: 13px; }
            QPushButton:hover { background-color: #3CB371; }
        """)
        layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Przyciski zamknięcia
        self.close_button = QPushButton("❌ Zamknij program")
        self.close_button.clicked.connect(self.confirm_close)
        self.close_button.setStyleSheet("""
            QPushButton { background-color: #8B0000; color: white; border: none; padding: 8px 12px; border-radius: 10px; font-size: 13px; }
            QPushButton:hover { background-color: #B22222; }
        """)
        layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.settings_panel.hide()

        # Timer kursora
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self.check_cursor_position)
        self.cursor_timer.start(200)

        # Wczytaj ustawienia
        self.load_settings()

    # ===== Styl slidera =====
    def _slider_style(self):
        return """
        QSlider::groove:horizontal { height: 8px; background: #2E8B57; border-radius: 4px; }
        QSlider::handle:horizontal { background: #2E8B57; border: 2px solid white; width: 16px; height: 16px; margin: -4px 0; border-radius: 8px; }
        QSlider::sub-page:horizontal { background: #2E8B57; border-radius: 4px; }
        QSlider::add-page:horizontal { background: #555; border-radius: 4px; }
        """

    # ===== Clickthrough =====
    def enable_clickthrough(self):
        self._clickthrough_enabled = True
        if self.isVisible():
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
                | Qt.WindowType.WindowTransparentForInput
            )
            self.show()

    def disable_clickthrough(self):
        self._clickthrough_enabled = False
        if self.isVisible():
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.show()

    def toggle_clickthrough_option(self, state):
        if self._settings_mode:
            return
        if state == Qt.CheckState.Checked.value:
            self.enable_clickthrough()
        else:
            self.disable_clickthrough()
        self.save_settings()

    def check_cursor_position(self):
        if self._settings_mode:
            return
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        if hasattr(self, "gear_rect") and self.gear_rect.contains(local_pos.toPointF()):
            self.disable_clickthrough()
        else:
            if self.clickthrough_checkbox.isChecked():
                self.enable_clickthrough()
            else:
                self.disable_clickthrough()

    # ===== Panel ustawień =====
    def toggle_settings(self):
        self._settings_mode = not self._settings_mode
        if self._settings_mode:
            self.disable_clickthrough()
            self.settings_panel.adjustSize()
            new_height = self.settings_panel.sizeHint().height() + 20
            self.setFixedHeight(new_height)
            self.setFixedWidth(self.settings_panel.sizeHint().width())
            panel_width = self.settings_panel.width()
            self.settings_panel.move(max(0, self.width() - panel_width), 0)
            self.settings_panel.show()
        else:
            self.settings_panel.hide()
            self.setFixedHeight(int(self.original_height * self.scale_factor))
            self.setFixedWidth(int(self.original_width * self.scale_factor))
            self.reposition()
            if self.clickthrough_checkbox.isChecked():
                self.enable_clickthrough()
            else:
                self.disable_clickthrough()
        self.update()

    # ===== Toggle widoczności =====
    def toggle_overlay(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            if self.clickthrough_checkbox.isChecked():
                self.enable_clickthrough()
            else:
                self.disable_clickthrough()

    # ===== Opacity / Scale / Progress =====
    def update_opacity(self, value):
        self.setWindowOpacity(value / 100.0)
        self.save_settings()

    def update_scale(self, value):
        self.scale_factor = value / 100.0
        self.resize(int(self.original_width * self.scale_factor), int(self.original_height * self.scale_factor))
        self.radius = int(15 * self.scale_factor)
        if self._settings_mode:
            self.settings_panel.adjustSize()
        self.update()
        self.save_settings()

    def getProgress(self):
        return self._progress

    def setProgress(self, value: float):
        self._progress = max(0.0, min(1.0, value))
        self.update()

    progress = pyqtProperty(float, fget=getProgress, fset=setProgress)

    def animateProgressTo(self, target_value: float):
        self.anim.stop()
        self.anim.setStartValue(self._progress)
        self.anim.setEndValue(max(0.0, min(1.0, target_value)))
        self.anim.start()

    # ===== Malowanie =====
    def paintEvent(self, event):
        if self._settings_mode:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # --- Tło ---
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self.radius, self.radius)
        painter.fillPath(path, self.bg_color)

        # --- Szara prowadnica ---
        bar_height = int(8 * self.scale_factor)
        radius_scaled = int(self.radius * self.scale_factor)
        guide_path = QPainterPath()
        guide_path.moveTo(rect.x(), rect.y() + bar_height)
        guide_path.lineTo(rect.x(), rect.y() + radius_scaled)
        guide_path.quadTo(rect.x(), rect.y(), rect.x() + radius_scaled, rect.y())
        guide_path.lineTo(rect.x() + rect.width() - radius_scaled, rect.y())
        guide_path.quadTo(rect.x() + rect.width(), rect.y(), rect.x() + rect.width(), rect.y() + radius_scaled)
        guide_path.lineTo(rect.x() + rect.width(), rect.y() + bar_height)
        guide_path.closeSubpath()
        painter.fillPath(guide_path, QColor(100, 100, 100))

        # --- Zielony pasek postępu ---
        progress_width = rect.width() * self._progress
        if self._progress > 0:
            progress_path = QPainterPath()
            progress_path.moveTo(rect.x(), rect.y() + bar_height)
            progress_path.lineTo(rect.x(), rect.y() + radius_scaled)
            progress_path.quadTo(rect.x(), rect.y(), rect.x() + radius_scaled, rect.y())
            if progress_width >= rect.width() - radius_scaled:
                progress_path.lineTo(rect.x() + progress_width - radius_scaled, rect.y())
                progress_path.quadTo(rect.x() + progress_width, rect.y(), rect.x() + progress_width, rect.y() + radius_scaled)
            else:
                progress_path.lineTo(rect.x() + progress_width, rect.y())
            progress_path.lineTo(rect.x() + progress_width, rect.y() + bar_height)
            progress_path.closeSubpath()
            painter.fillPath(progress_path, self.progress_color)

        # --- Teksty ---
        painter.setFont(QFont("Segoe UI", int(20 * self.scale_factor), QFont.Weight.Medium))
        painter.setPen(self.shadow_color)
        painter.drawText(rect.adjusted(2, int(22 * self.scale_factor), 2, 0), Qt.AlignmentFlag.AlignHCenter, self.title)
        painter.setPen(self.text_color)
        painter.drawText(rect.adjusted(0, int(20 * self.scale_factor), 0, 0), Qt.AlignmentFlag.AlignHCenter, self.title)

        painter.setFont(QFont("Segoe UI", int(12 * self.scale_factor)))
        painter.setPen(self.shadow_color)
        painter.drawText(rect.adjusted(int(27 * self.scale_factor), int(62 * self.scale_factor), 2, 0), Qt.AlignmentFlag.AlignLeft, self.left_text)
        painter.drawText(rect.adjusted(-int(23 * self.scale_factor), int(62 * self.scale_factor), -int(18 * self.scale_factor), 0), Qt.AlignmentFlag.AlignRight, self.right_text)
        painter.setPen(self.text_color)
        painter.drawText(rect.adjusted(int(25 * self.scale_factor), int(60 * self.scale_factor), 0, 0), Qt.AlignmentFlag.AlignLeft, self.left_text)
        painter.drawText(rect.adjusted(-int(25 * self.scale_factor), int(60 * self.scale_factor), -int(20 * self.scale_factor), 0), Qt.AlignmentFlag.AlignRight, self.right_text)

        # --- Zębatka ---
        gear_size = int(20 * self.scale_factor)
        self.gear_rect = QRectF(rect.width() - gear_size - 12, gear_size - 10, gear_size, gear_size)
        painter.setFont(QFont("Segoe UI Symbol", int(16 * self.scale_factor)))
        painter.drawText(self.gear_rect, Qt.AlignmentFlag.AlignCenter, "⚙️")

    def mousePressEvent(self, event: QMouseEvent):
        if hasattr(self, "gear_rect") and self.gear_rect.contains(event.position()):
            self.toggle_settings()

    # ===== Zapis / Odczyt =====
    def load_settings(self):
        try:
            if not os.path.exists(self.config_path):
                return
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            opacity = data.get("opacity", 1.0)
            scale = data.get("scale", 1.0)
            clickthrough = data.get("clickthrough", True)

            self.setWindowOpacity(opacity)
            self.scale_factor = scale
            self._clickthrough_enabled = clickthrough

            if hasattr(self, "opacity_slider"):
                self.opacity_slider.setValue(int(opacity * 100))
            if hasattr(self, "scale_slider"):
                self.scale_slider.blockSignals(True)
                self.scale_slider.setValue(int(scale * 100))
                self.scale_slider.blockSignals(False)
                self.update_scale(int(scale * 100))
            if hasattr(self, "clickthrough_checkbox"):
                self.clickthrough_checkbox.setChecked(clickthrough)

        except Exception as e:
            print("Błąd podczas wczytywania ustawień:", e)

    def save_settings(self):
        data = {
            "opacity": self.windowOpacity(),
            "scale": self.scale_factor,
            "clickthrough": self.clickthrough_checkbox.isChecked()
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Błąd zapisu ustawień:", e)

    # ===== Zamknięcie programu =====
    def confirm_close(self):
        reply = QMessageBox.question(
            self,
            "Zamknij program",
            "Czy na pewno chcesz zamknąć program?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Zatrzymanie timera kursora
            if hasattr(self, 'cursor_timer') and self.cursor_timer.isActive():
                self.cursor_timer.stop()
            
            # Zatrzymanie timera aktualizacji API, jeśli istnieje
            if hasattr(self, 'update_timer') and self.update_timer.isActive():
                self.update_timer.stop()
            
            # Usunięcie wszystkich hotkeyów keyboard
            keyboard.unhook_all_hotkeys()
            
            # Zamknięcie całej aplikacji
            QApplication.quit()

    # ===== API =====
    def start_minute_updates(self, api_url):
        self.api_url = api_url
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.minute_update)
        self.update_timer.start(60 * 1000)
        self.minute_update()

    def minute_update(self):
        try:
            response = requests.get(self.api_url, timeout=10)
            data = response.json()
        except Exception as e:
            print("Błąd pobierania danych z API:", e)
            return
        self.title = data.get("name", self.title)
        self.left_text = data.get("username", self.left_text) + " → |"
        self.right_text = data.get("email", self.right_text)
        progress = float(data.get("address", {}).get("geo", {}).get("lng", 0)) / 100
        self.animateProgressTo(progress)
        self.update()

    # ===== Reposition =====
    def reposition(self, margin_x=30, margin_y=30):
        screen_geo = QGuiApplication.primaryScreen().availableGeometry()
        new_x = screen_geo.width() - self.width() - margin_x
        new_y = margin_y
        self.move(new_x, new_y)
