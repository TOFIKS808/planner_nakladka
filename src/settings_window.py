import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QCheckBox, QPushButton,
    QSpacerItem, QSizePolicy, QHBoxLayout, QButtonGroup, QRadioButton, QMessageBox
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QFont


class FancyCloseButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.setText("×")
        self._opacity = 1.0
        
        # Animacja
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def get_opacity(self):
        return self._opacity
        
    def set_opacity(self, value):
        self._opacity = value
        self.update()
        
    opacity = pyqtProperty(float, get_opacity, set_opacity)
    
    def enterEvent(self, event):
        self.animation.setStartValue(self._opacity)
        self.animation.setEndValue(0.8)
        self.animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.animation.setStartValue(self._opacity)
        self.animation.setEndValue(1.0)
        self.animation.start()
        super().leaveEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Tło z gradientem przy najechaniu - NOWA PALETA
        if self.underMouse():
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0.0, QColor(220, 80, 80))  # Czerwony
            gradient.setColorAt(1.0, QColor(180, 50, 50))  # Ciemniejszy czerwony
            painter.setBrush(gradient)
        else:
            painter.setBrush(QColor(0, 0, 0, 0))
            
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Zaokrąglony prostokąt
        rect = self.rect()
        painter.drawRoundedRect(rect, 8, 8)
        
        # Efekt przezroczystości
        painter.setOpacity(self._opacity)
        
        # Tekst (X) - perfekcyjnie wyśrodkowany
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Segoe UI")
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        
        # Ręczne wyśrodkowanie tekstu
        text_rect = rect.adjusted(0, -3, 0, 0)  # Korekta manualna
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.text())


class SettingsWindow(QWidget):
    def __init__(self, overlay=None, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.setWindowTitle("⚙️ Ustawienia nakładki")
        self.setFixedWidth(420)
        
        # Ustaw przezroczyste tło dla całego okna
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Usuwamy domyślny pasek tytułu i tworzymy własny
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        # Ścieżka ustawień
        if os.name == "nt":
            base_dir = os.getenv("APPDATA")
            self.config_dir = os.path.join(base_dir, "OverlayApp")
        else:
            base_dir = os.path.expanduser("~/.config")
            self.config_dir = os.path.join(base_dir, "overlay")

        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, "settings.json")

        # === Główny layout ===
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ====== WŁASNY PASEK TYTUŁU - NOWY STYL ======
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("""
            background-color: rgba(28, 33, 45, 230); 
            border-top-left-radius: 12px; 
            border-top-right-radius: 12px;
            border-bottom: 1px solid rgba(60, 70, 90, 180);
        """)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(15, 0, 15, 0)
        title_bar_layout.setSpacing(0)
        
        # Tytuł
        title_label = QLabel("⚙️ Ustawienia nakładki")
        title_label.setStyleSheet("""
            color: rgb(240, 244, 255); 
            font-size: 14px; 
            font-weight: bold;
            font-family: "Segoe UI";
            padding: 0px;
            background: transparent;
        """)
        
        # Przestrzeń pomiędzy tytułem a przyciskiem
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setStyleSheet("background: transparent;")
        
        # Fancy przycisk zamknięcia
        self.close_button = FancyCloseButton()
        self.close_button.clicked.connect(self.close_settings)
        self.close_button.setStyleSheet("""
            FancyCloseButton {
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                margin: 5px;
                background: transparent;
            }
        """)
        
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addWidget(spacer)
        title_bar_layout.addWidget(self.close_button)

        # ====== CONTENT - NOWY STYL ======
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            background-color: rgba(23, 28, 40, 230); 
            border-bottom-left-radius: 12px; 
            border-bottom-right-radius: 12px;
        """)
        layout = QVBoxLayout(content_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(18)

        # ====== Przezroczystość ======
        label = QLabel("Przezroczystość nakładki:")
        label.setStyleSheet("""
            color: rgb(240, 244, 255); 
            font-size: 13px; 
            font-family: "Segoe UI";
            background: transparent;
        """)
        layout.addWidget(label)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.on_opacity_change)
        self.opacity_slider.setStyleSheet(self._slider_style())
        layout.addWidget(self.opacity_slider)

        # ====== Skalowanie ======
        self.scaling_checkbox = QCheckBox("Włącz skalowanie nakładki (przeciągnij za róg aby skalować)")
        self.scaling_checkbox.setStyleSheet(self._checkbox_style())
        self.scaling_checkbox.stateChanged.connect(self.on_scaling_change)
        layout.addWidget(self.scaling_checkbox)

        # ====== Click-through ======
        self.clickthrough_checkbox = QCheckBox("Pozwól klikać przez nakładkę")
        self.clickthrough_checkbox.setStyleSheet(self._checkbox_style())
        self.clickthrough_checkbox.stateChanged.connect(self.on_clickthrough_change)
        layout.addWidget(self.clickthrough_checkbox)

        # ====== Dragging ======
        self.drag_checkbox = QCheckBox("Pozwól przenosić nakładkę")
        self.drag_checkbox.setStyleSheet(self._checkbox_style())
        self.drag_checkbox.stateChanged.connect(self.on_drag_change)
        layout.addWidget(self.drag_checkbox)

        # ====== Separator ======
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: rgba(60, 70, 90, 120);")
        separator.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(separator)

        # ====== Grupy zajęciowe ======
        layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Etykiety grup - NOWY STYL
        group_label_style = """
            color: rgb(240, 244, 255); 
            font-size: 13px; 
            font-weight: bold; 
            font-family: "Segoe UI";
            background: transparent; 
            padding: 5px 0px;
        """
        
        group_c_label = QLabel("Grupa C:")
        group_c_label.setStyleSheet(group_label_style)
        layout.addWidget(group_c_label)
        self.group_c = self.create_group(["11K1", "11K2"], layout)

        group_l_label = QLabel("Grupa L:")
        group_l_label.setStyleSheet(group_label_style)
        layout.addWidget(group_l_label)
        self.group_l = self.create_group(["L01", "L02", "L03", "L04", "L05"], layout)

        group_k_label = QLabel("Grupa K:")
        group_k_label.setStyleSheet(group_label_style)
        layout.addWidget(group_k_label)
        self.group_k = self.create_group(["K01", "K02", "K03", "K04"], layout)

        # ====== Separator ======
        separator2 = QWidget()
        separator2.setFixedHeight(1)
        separator2.setStyleSheet("background-color: rgba(60, 70, 90, 120);")
        separator2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(separator2)

        # ====== Przyciski ======
        layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        save_button = QPushButton("💾 Zapisz ustawienia")
        save_button.clicked.connect(self.save_settings)
        save_button.setStyleSheet(self._button_style("green"))
        layout.addWidget(save_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Przycisk zamknięcia programu
        close_button = QPushButton("❌ Zamknij program")
        close_button.clicked.connect(self.confirm_close_app)
        close_button.setStyleSheet(self._button_style("red"))
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Dodajemy wszystko do głównego layoutu
        main_layout.addWidget(title_bar)
        main_layout.addWidget(content_widget)

        # Zmienne do przeciągania okna
        self.dragging = False
        self.drag_position = None

        self.load_settings()

    def _slider_style(self):
        return """
        QSlider::groove:horizontal { 
            height: 8px; 
            background: rgba(45, 55, 75, 180); 
            border-radius: 4px; 
        }
        QSlider::handle:horizontal { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgb(74, 144, 226), 
                stop:1 rgb(103, 230, 220));
            border: 2px solid white; 
            width: 16px; 
            height: 16px; 
            margin: -4px 0; 
            border-radius: 8px; 
        }
        QSlider::sub-page:horizontal { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgb(74, 144, 226), 
                stop:1 rgb(103, 230, 220));
            border-radius: 4px; 
        }
        QSlider::add-page:horizontal { 
            background: rgba(85, 95, 115, 150); 
            border-radius: 4px; 
        }
        """

    def _checkbox_style(self):
        return """
        QCheckBox { 
            color: rgb(240, 244, 255); 
            font-size: 13px; 
            font-family: "Segoe UI";
            spacing: 8px; 
            background: transparent;
        }
        QCheckBox::indicator { 
            width: 18px; 
            height: 18px; 
            border-radius: 4px; 
            border: 2px solid rgba(74, 144, 226, 200); 
            background-color: transparent; 
        }
        QCheckBox::indicator:checked { 
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(74, 144, 226, 255), 
                stop:1 rgba(103, 230, 220, 255));
            border: 2px solid rgba(60, 130, 200, 255); 
        }
        QCheckBox:hover {
            color: rgba(103, 230, 220, 255);
        }
        """

    def _button_style(self, color_type):
        base_style = """
            QPushButton { 
                color: white; 
                border: none; 
                padding: 10px 20px;
                border-radius: 8px; 
                font-size: 13px; 
                font-family: "Segoe UI";
                font-weight: bold;
                min-width: 160px;
            }
            QPushButton:hover { 
                transform: none;
            }
            QPushButton:pressed { 
                padding: 11px 19px 9px 21px;
            }
        """
        
        if color_type == "green":
            return base_style + """
                QPushButton { 
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(74, 179, 113, 220), 
                        stop:1 rgba(46, 139, 87, 220));
                }
                QPushButton:hover { 
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(84, 199, 123, 220), 
                        stop:1 rgba(56, 159, 97, 220));
                }
            """
        else:  # red
            return base_style + """
                QPushButton { 
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(220, 80, 80, 220), 
                        stop:1 rgba(180, 50, 50, 220));
                }
                QPushButton:hover { 
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(240, 90, 90, 220), 
                        stop:1 rgba(200, 60, 60, 220));
                }
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
                QRadioButton { 
                    color: rgb(240, 244, 255); 
                    font-size: 13px; 
                    font-family: "Segoe UI";
                    spacing: 8px; 
                    background: transparent;
                }
                QRadioButton::indicator { 
                    width: 18px; 
                    height: 18px;
                    border-radius: 9px; 
                    border: 2px solid rgba(74, 144, 226, 200); 
                    background-color: transparent; 
                }
                QRadioButton::indicator:checked { 
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(74, 144, 226, 255), 
                        stop:1 rgba(103, 230, 220, 255));
                    border: 2px solid rgba(60, 130, 200, 255); 
                }
                QRadioButton:hover {
                    color: rgba(103, 230, 220, 255);
                }
            """)
            group.addButton(btn)
            row.addWidget(btn)
        row.addStretch()
        layout.addLayout(row)
        return group

    # ========================== OBSŁUGA PRZECIĄGANIA OKNA ==========================
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and self.drag_position:
            delta = event.globalPosition().toPoint() - self.drag_position
            self.move(self.pos() + delta)
            self.drag_position = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.drag_position = None
            event.accept()

    # ========================== HANDLERY ==========================
    def on_group_changed(self, button):
        """Automatycznie zapisuj gdy zmieniona zostanie grupa"""
        self.save_settings()

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
        """Wczytuje ustawienia z overlay (jeden wspólny system)"""
        try:
            if not self.overlay:
                return

            # Pobierz ustawienia z overlay
            data = self.overlay.get_current_settings()

            # Ustawienia podstawowe
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

        except Exception as e:
            print(f"Błąd wczytywania ustawień: {e}")

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
        """Zapisuje ustawienia przez overlay (jeden wspólny system)"""
        try:
            if not self.overlay:
                return
                
            # Pobierz aktualne ustawienia z overlay
            current_settings = self.overlay.get_current_settings()
                
            # Przygotuj ustawienia do zapisu - ZACHOWAJ ISTNIEJĄCE GRUPY JEŚLI NOWE SĄ None
            settings_to_save = {
                "opacity": round(self.opacity_slider.value() / 100.0, 2),
                "clickthrough": self.clickthrough_checkbox.isChecked(),
                "drag_enabled": self.drag_checkbox.isChecked(),
                "scaling_enabled": self.scaling_checkbox.isChecked(),
            }

            # Dodaj grupy tylko jeśli są wybrane (nie None)
            group_c = self.get_checked_label(self.group_c)
            group_l = self.get_checked_label(self.group_l)
            group_k = self.get_checked_label(self.group_k)
            
            if group_c is not None:
                settings_to_save["group_c"] = group_c
            if group_l is not None:
                settings_to_save["group_l"] = group_l  
            if group_k is not None:
                settings_to_save["group_k"] = group_k

            # Użyj metody z overlay do zapisu
            self.overlay.update_settings(settings_to_save)
            
            # Wymuś natychmiastowy zapis
            self.overlay.save_settings_immediately()

        except Exception as e:
            print(f"Błąd zapisywania ustawień: {e}")

    def confirm_close_app(self):
        """Zamyka całą aplikację z jednym potwierdzeniem"""
        reply = QMessageBox.question(
            self,
            "Zamknij program",
            "Czy na pewno chcesz zamknąć program?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.save_settings()
            # Zamykamy całą aplikację
            if self.overlay:
                if hasattr(self.overlay, 'close'):
                    self.overlay.close()
                elif hasattr(self.overlay, 'quit'):
                    self.overlay.quit()
            # Zamykamy również okno ustawień
            self.close()

    def close_settings(self):
        """Zamyka tylko okno ustawień (jak kliknięcie zębatki)"""
        self.hide()
        if self.overlay and hasattr(self.overlay, '_clickthrough_enabled') and self.overlay._clickthrough_enabled:
            self.overlay.enable_clickthrough()

    def closeEvent(self, event):
        """Przechwytuje zdarzenie zamknięcia okna - teraz zamyka tylko okno ustawień"""
        self.close_settings()
        event.accept()