import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QCheckBox, QPushButton,
    QSpacerItem, QSizePolicy, QHBoxLayout, QButtonGroup, QRadioButton, QMessageBox
)
from PyQt6.QtCore import Qt


class SettingsWindow(QWidget):
    def __init__(self, overlay=None, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.setWindowTitle("⚙️ Ustawienia nakładki")
        self.setFixedWidth(420)
        
        self.setWindowFlags(Qt.WindowType.Window)

        # Ścieżka ustawień
        if os.name == "nt":
            base_dir = os.getenv("APPDATA")
            self.config_dir = os.path.join(base_dir, "OverlayApp")
        else:
            base_dir = os.path.expanduser("~/.config")
            self.config_dir = os.path.join(base_dir, "overlay")

        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, "settings.json")

        # === Layout ===
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)

        # ====== Nagłówek ======
        header = QLabel("⚙️ Ustawienia nakładki")
        header.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(header)

        # ====== Przezroczystość ======
        label = QLabel("Przezroczystość nakładki:")
        label.setStyleSheet("color: white; font-size: 13px;")
        layout.addWidget(label)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.on_opacity_change)
        self.opacity_slider.setStyleSheet(self._slider_style())
        layout.addWidget(self.opacity_slider)

        # ====== Skalowanie ======
        self.scaling_checkbox = QCheckBox("Włącz skalowanie nakładki (przeciągnij za róg aby skalować)")
        self.scaling_checkbox.setStyleSheet("""
            QCheckBox { color: white; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #3CB371; background-color: transparent; }
            QCheckBox::indicator:checked { background-color: #3CB371; border: 2px solid #2E8B57; }
        """)
        self.scaling_checkbox.stateChanged.connect(self.on_scaling_change)
        layout.addWidget(self.scaling_checkbox)

        # ====== Click-through ======
        self.clickthrough_checkbox = QCheckBox("Pozwól klikać przez nakładkę")
        self.clickthrough_checkbox.setStyleSheet("""
            QCheckBox { color: white; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #3CB371; background-color: transparent; }
            QCheckBox::indicator:checked { background-color: #3CB371; border: 2px solid #2E8B57; }
        """)
        self.clickthrough_checkbox.stateChanged.connect(self.on_clickthrough_change)
        layout.addWidget(self.clickthrough_checkbox)

        # ====== Dragging ======
        self.drag_checkbox = QCheckBox("Pozwól przenosić nakładkę")
        self.drag_checkbox.setStyleSheet("""
            QCheckBox { color: white; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #3CB371; background-color: transparent; }
            QCheckBox::indicator:checked { background-color: #3CB371; border: 2px solid #2E8B57; }
        """)
        self.drag_checkbox.stateChanged.connect(self.on_drag_change)
        layout.addWidget(self.drag_checkbox)

        # ====== Grupy zajęciowe ======
        layout.addSpacerItem(QSpacerItem(10, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        layout.addWidget(QLabel("Grupa C:"))
        self.group_c = self.create_group(["11K1", "11K2"], layout)

        layout.addWidget(QLabel("Grupa L:"))
        self.group_l = self.create_group(["L01", "L02", "L03", "L04", "L05"], layout)

        layout.addWidget(QLabel("Grupa K:"))
        self.group_k = self.create_group(["K01", "K02", "K03", "K04"], layout)

        # ====== Przyciski ======
        layout.addSpacerItem(QSpacerItem(10, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        save_button = QPushButton("💾 Zapisz ustawienia")
        save_button.clicked.connect(self.save_settings)
        save_button.setStyleSheet("""
            QPushButton { background-color: #2E8B57; color: white; border: none; padding: 8px 12px;
                          border-radius: 10px; font-size: 13px; }
            QPushButton:hover { background-color: #3CB371; }
        """)
        layout.addWidget(save_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Przycisk zamknięcia programu
        close_button = QPushButton("❌ Zamknij program")
        close_button.clicked.connect(self.confirm_close_app)
        close_button.setStyleSheet("""
            QPushButton { background-color: #8B0000; color: white; border: none; padding: 8px 12px; border-radius: 10px; font-size: 13px; }
            QPushButton:hover { background-color: #B22222; }
        """)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.load_settings()
        self.setStyleSheet("background-color: #1F232B; color: white;")

    def _slider_style(self):
        return """
        QSlider::groove:horizontal { height: 8px; background: #2E8B57; border-radius: 4px; }
        QSlider::handle:horizontal { background: #2E8B57; border: 2px solid white; width: 16px; height: 16px; margin: -4px 0; border-radius: 8px; }
        QSlider::sub-page:horizontal { background: #2E8B57; border-radius: 4px; }
        QSlider::add-page:horizontal { background: #555; border-radius: 4px; }
        """

    # ========================== GRUPY ==========================
    def create_group(self, labels, layout):
        group = QButtonGroup(self)
        group.setExclusive(True)
        group.buttonClicked.connect(self.on_group_changed)
        row = QHBoxLayout()
        row.addStretch()
        for text in labels:
            btn = QRadioButton(text)
            btn.setStyleSheet("""
                QRadioButton { color: white; font-size: 13px; spacing: 8px; }
                QRadioButton::indicator { width: 18px; height: 18px;
                border-radius: 9px; border: 2px solid #3CB371; background-color: transparent; }
                QRadioButton::indicator:checked { background-color: #3CB371; border: 2px solid #2E8B57; }
            """)
            group.addButton(btn)
            row.addWidget(btn)
        row.addStretch()
        layout.addLayout(row)
        return group

    def on_group_changed(self, button):
        """Automatycznie zapisuj gdy zmieniona zostanie grupa"""
        self.save_settings()

    # ========================== HANDLERY ==========================
    def on_opacity_change(self, value):
        if self.overlay:
            try:
                self.overlay.setWindowOpacity(value / 100.0)
                self.save_settings()
            except Exception as e:
                print("Błąd przy zmianie przezroczystości:", e)

    def on_scaling_change(self, state):
        if self.overlay:
            self.overlay.scaling_enabled = self.scaling_checkbox.isChecked()
            self.overlay.update()
            self.save_settings()

    def on_clickthrough_change(self, state):
        if self.overlay:
            if self.clickthrough_checkbox.isChecked():
                self.overlay.enable_clickthrough()
            else:
                self.overlay.disable_clickthrough()
            self.save_settings()

    def on_drag_change(self, state):
        if self.overlay:
            self.overlay.drag_enabled = self.drag_checkbox.isChecked()
            self.save_settings()

    # ========================== USTAWIENIA ==========================
    def load_settings(self):
        """Wczytuje ustawienia z pliku JSON - POPRAWIONE"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # Domyślne ustawienia
                data = {
                    "opacity": 1.0,
                    "clickthrough": True,
                    "drag_enabled": True,
                    "scaling_enabled": False,
                    "group_c": None,
                    "group_l": None,
                    "group_k": None
                }

            # Ustawienia podstawowe - TERAZ POPRAWNIE WCZYTYWANE
            opacity = data.get("opacity", 1.0)
            clickthrough = data.get("clickthrough", True)
            drag_enabled = data.get("drag_enabled", True)
            scaling_enabled = data.get("scaling_enabled", False)

            self.opacity_slider.setValue(int(opacity * 100))
            self.clickthrough_checkbox.setChecked(clickthrough)
            self.drag_checkbox.setChecked(drag_enabled)
            self.scaling_checkbox.setChecked(scaling_enabled)

            # Grupy zajęciowe
            group_c = data.get("group_c")
            group_l = data.get("group_l")
            group_k = data.get("group_k")
                        
            # Ustaw zaznaczone przyciski
            self.set_checked_label(self.group_c, group_c)
            self.set_checked_label(self.group_l, group_l)
            self.set_checked_label(self.group_k, group_k)

            # Zastosuj ustawienia do overlay jeśli istnieje
            self.apply_settings_to_overlay(data)

        except Exception as e:
            print(f"Błąd wczytywania ustawień: {e}")

    def apply_settings_to_overlay(self, data):
        """Zastosowuje ustawienia do overlay - POPRAWIONE"""
        try:
            if not self.overlay:
                return
                
            # Przezroczystość
            opacity = data.get("opacity", 1.0)
            self.overlay.setWindowOpacity(opacity)
            
            # Click-through
            clickthrough = data.get("clickthrough")
            if clickthrough:
                self.overlay.enable_clickthrough()
            else:
                self.overlay.disable_clickthrough()
            
            # Dragging
            if hasattr(self.overlay, 'drag_enabled'):
                self.overlay.drag_enabled = data.get("drag_enabled", True)
            
            # Skalowanie
            if hasattr(self.overlay, 'scaling_enabled'):
                self.overlay.scaling_enabled = data.get("scaling_enabled", False)
                        
        except Exception as e:
            print(f"Błąd aplikowania ustawień do overlay: {e}")

    def set_checked_label(self, button_group, label):
        """Ustawia zaznaczony przycisk w grupie"""
        # Odznacz wszystkie przyciski w grupie
        for btn in button_group.buttons():
            btn.setChecked(False)
        
        # Jeśli podano label, zaznacz odpowiedni przycisk
        if label:
            for btn in button_group.buttons():
                if btn.text() == label:
                    btn.setChecked(True)
                    break

    def get_checked_label(self, button_group):
        """Zwraca tekst zaznaczonego przycisku lub None jeśli nic nie jest zaznaczone"""
        checked = button_group.checkedButton()
        return checked.text() if checked else None

    def save_settings(self):
        """Zapisuje ustawienia do pliku JSON - POPRAWIONE"""
        try:
            # Przygotuj ustawienia do zapisania
            settings_to_save = {
                "opacity": round(self.opacity_slider.value() / 100.0, 2),
                "clickthrough": self.clickthrough_checkbox.isChecked(),
                "drag_enabled": self.drag_checkbox.isChecked(),
                "scaling_enabled": self.scaling_checkbox.isChecked(),
                "group_c": self.get_checked_label(self.group_c),
                "group_l": self.get_checked_label(self.group_l),
                "group_k": self.get_checked_label(self.group_k)
            }

            # Zapisz do pliku
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings_to_save, f, ensure_ascii=False, indent=2)

            # Zastosuj ustawienia do overlay
            self.apply_settings_to_overlay(settings_to_save)

        except Exception as e:
            print(f"Błąd zapisywania ustawień: {e}")

    def confirm_close_app(self):
        reply = QMessageBox.question(
            self,
            "Zamknij program",
            "Czy na pewno chcesz zamknąć program?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.save_settings()
            self.close_settings()
            if self.overlay:
                self.overlay.confirm_close()

    def close_settings(self):
        self.hide()
        if self.overlay and hasattr(self.overlay, '_clickthrough_enabled') and self.overlay._clickthrough_enabled:
            self.overlay.enable_clickthrough()

    def closeEvent(self, event):
        self.close_settings()
        event.accept()