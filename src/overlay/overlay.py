

import os
import sys
import keyboard
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, pyqtProperty, QPropertyAnimation, QEasingCurve, QTimer, QSize

from src.overlay.ui_renderer import paint_overlay
from src.overlay.mouse_handler import MouseHandler
from src.overlay.settings_manager import SettingsManager
from src.overlay.update_manager import UpdateManager
from src.overlay.modern_progress_bar import ModernProgressBar
from src.overlay.toggle_button import ToggleButton
from src.tray import Tray
from src.settings.settings_window import SettingsWindow

class OverlayWidget(QWidget):
    def __init__(self, title, left_text, right_text, room_text="-", progress=0.0):
        super().__init__()

        # Ścieżka pliku ustawień
        if os.name == "nt":
            base_dir = os.getenv("APPDATA")
            config_dir = os.path.join(base_dir, "OverlayApp")
        else:
            base_dir = os.path.expanduser("~/.config")
            config_dir = os.path.join(base_dir, "overlay")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "settings.json")

        # Inicjalizacja menedżerów
        # Inicjalizacja menedżerów
        self.settings_manager = SettingsManager(config_path)
        self.update_manager = UpdateManager(self)
        self.mouse_handler = MouseHandler(self)

        # Teksty (kept for backward compatibility, but will use QLabel widgets)
        self.title = title
        self.left_text = left_text
        self.right_text = right_text
        self.room_text = room_text

        # Styl
        self.radius = 20  # Increased for glassmorphism

        # Zezwól na zmianę rozmiaru
        self.setMinimumSize(200, 48)
        self.setMaximumSize(800, 190)

        # Stan overlay
        self._progress = progress
        self._clickthrough_enabled = True  # Domyślnie włączone
        self.drag_enabled = True
        self.scaling_enabled = True  # Domyślnie WŁĄCZONE skalowanie

        # Rozmiar początkowy
        self.original_width = 420
        self.original_height = 110  # Changed to match new design
        self.base_width = 420 # Reference width for scaling
        self.scale_factor = 1.0
        self.is_small = False  # Track size state for toggle

        # Inicjalizacja komponentów UI (Tray, Settings)
        self.tray = Tray(QApplication.instance(), self)
        self.settings_window = SettingsWindow(self)

        # Initialize UI components BEFORE resizing
        self._setup_ui_layout()
        
        self.load_settings() # Wczytaj ustawienia i zastosuj rozmiar/pozycję

        # Okno
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)  # Prevent system background painting
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # Animacje
        self.anim = QPropertyAnimation(self, b"progress")
        self.anim.setDuration(1200)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Size toggle animation
        self.anim_size = QPropertyAnimation(self, b"size", self)
        self.anim_size.setDuration(500)
        self.anim_size.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # Skrót klawiszowy
        try:
            keyboard.remove_hotkey("ctrl+q")
        except Exception:
            pass
        keyboard.add_hotkey("ctrl+q", self.toggle_overlay)

        keyboard.add_hotkey("ctrl+q", self.toggle_overlay)

    def open_settings(self):
        """Otwiera okno ustawień"""
        if self.settings_window:
            self.settings_window.show()
            self.settings_window.raise_()
            self.settings_window.activateWindow()

    def closeEvent(self, event):
        self.settings_manager.stop_timers()
        if hasattr(self, 'cursor_timer') and self.cursor_timer.isActive():
            self.cursor_timer.stop()
        
        if self.settings_window:
            self.settings_window.close()
            
        event.accept()

    def _setup_ui_layout(self):
        """Setup modern UI layout with QVBoxLayout and widgets"""
        # 1. Toggle Button (positioned absolutely in resizeEvent)
        self.btn = ToggleButton(self)
        self.btn.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 2. Header Container (Title + Room)
        self.header_container = QWidget(self)
        self.header_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.header_container.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(self.header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # Title Label
        self.lbl_name = QLabel(self.title, self.header_container)
        self.lbl_name.setStyleSheet("color: white; font-weight: 600; font-size: 19px; background: transparent;")
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_name.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        header_layout.addWidget(self.lbl_name)
        # header_layout.addWidget(self.lbl_room) # REMOVED: User requested removal
        header_layout.addStretch()

        # 3. Modern Progress Bar
        self.progress_bar = ModernProgressBar(self)
        self.progress_bar.set_progress(self._progress)
        self.progress_bar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 4. Info Container (Time + Place)
        self.info_container = QWidget(self)
        self.info_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.info_container.setStyleSheet("background: transparent;")
        info_layout = QHBoxLayout(self.info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Time label
        self.lbl_time = QLabel(self.left_text, self.info_container)
        self.lbl_time.setStyleSheet("color: rgba(255,255,255,230); font-size: 13px; background: transparent;")
        self.lbl_time.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Spacer
        info_layout.addWidget(self.lbl_time)
        info_layout.addStretch()
        
        # Place label (pill-shaped)
        self.lbl_place = QLabel(self.right_text, self.info_container)
        self.lbl_place.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_place.setStyleSheet("""
            background: rgba(255, 255, 255, 25);
            border: 1px solid rgba(255, 255, 255, 25);
            border-radius: 12px;
            padding: 0px 10px;
            min-width: 40px;
            max-height: 24px;
            min-height: 24px;
            color: white;
            font-size: 12px;
            font-weight: 500;
            margin: 0px;
        """)
        info_layout.addWidget(self.lbl_place)
        
        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 10, 35, 10)  # Reduced vertical padding
        self.layout.setSpacing(5)
        
        self.layout.addWidget(self.header_container)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.info_container)
        
        # Animation for button rotation
        self.anim_rotate = QPropertyAnimation(self.btn, b"angle", self)
        self.anim_rotate.setDuration(500)
        self.anim_rotate.setEasingCurve(QEasingCurve.Type.InOutCubic)
    
    def move_to_top_right(self):
        """Position overlay at top-right corner of screen"""
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - self.width() - 30  # 30px margin
        y = 30  # 30px margin
        self.move(x, y)
    
    def toggle_size(self):
        """Toggle between large and small overlay states"""
        # Calculate current scale relative to the state we are LEAVING
        # If we are currently small (before toggle), base was 260. If large, base was 420.
        # Note: self.is_small is the CURRENT state before toggle
        if self.is_small:
            current_base = 260
        else:
            current_base = 420
            
        # Avoid division by zero
        if current_base > 0:
            current_scale = self.width() / current_base
        else:
            current_scale = 1.0
            
        self.is_small = not self.is_small
        
        current_geo = self.geometry()
        current_right = current_geo.right()
        current_y = current_geo.y()
        
        if self.is_small:
            # Small state: 260x60 base
            self.base_width = 260
            base_w, base_h = 260, 60
            
            # Apply scale
            end_w = int(base_w * current_scale)
            end_h = int(base_h * current_scale)
            
            # Clamp to limits to prevent right-edge drift
            end_w = max(self.minimumWidth(), min(end_w, self.maximumWidth()))
            end_h = max(self.minimumHeight(), min(end_h, self.maximumHeight()))
            
            self.info_container.hide()
            
            # Rotate button 180 degrees
            self.anim_rotate.setStartValue(0)
            self.anim_rotate.setEndValue(180)
        else:
            # Large state: 420x110 base
            self.base_width = 420
            base_w, base_h = 420, 110
            
            # Apply scale
            end_w = int(base_w * current_scale)
            end_h = int(base_h * current_scale)
            
            # Clamp to limits to prevent right-edge drift
            end_w = max(self.minimumWidth(), min(end_w, self.maximumWidth()))
            end_h = max(self.minimumHeight(), min(end_h, self.maximumHeight()))
            
            self.info_container.show()
            
            # Rotate button back to 0 (via 360 for smooth animation)
            self.anim_rotate.setStartValue(180)
            self.anim_rotate.setEndValue(360)
        
        self.anim_rotate.start()
        
        # Calculate new geometry (anchored to right)
        # Use x + width to get the true right edge coordinate (exclusive)
        current_right_edge = current_geo.x() + current_geo.width()
        end_x = current_right_edge - end_w
        
        from PyQt6.QtCore import QRect
        end_geo = QRect(end_x, current_y, end_w, end_h)
        
        self.anim_geo = QPropertyAnimation(self, b"geometry", self)
        self.anim_geo.setDuration(500)
        self.anim_geo.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        self.anim_geo.setStartValue(current_geo)
        self.anim_geo.setEndValue(end_geo)
        self.anim_geo.start()

    def _apply_scaling(self):
        """Apply scaling to fonts and elements based on current width"""
        if self.base_width <= 0: return
        
        scale = self.width() / self.base_width
        self.scale_factor = scale # Update public property
        
        if self.is_small:
            # Base values for Small state
            font_title = 16 * scale
            font_time = 10 * scale # Not visible but calculated
            font_place = 10 * scale
            h_progress = max(2, int(6 * scale))
            
            margin_v = int(16 * scale)
            margin_h_left = int(20 * scale)
            margin_h_right = int(35 * scale)
            spacing = int(2 * scale)
            
            place_radius = int(6 * scale)
            place_padding = int(6 * scale)
            place_min_h = int(14 * scale)
            
            # Apply styles
            self.lbl_name.setStyleSheet(f"color: white; font-weight: 600; font-size: {font_title}px; background: transparent;")
            self.progress_bar.setFixedHeight(h_progress)
            self.layout.setContentsMargins(margin_h_left, margin_v, margin_h_right, margin_v)
            self.layout.setSpacing(spacing)
            
            # Place label style (even if hidden/unused in small state, good to have)
            self.lbl_place.setStyleSheet(f"""
                background: rgba(255, 255, 255, 25);
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: {place_radius}px;
                padding: 0px {place_padding}px;
                min-width: {30*scale}px;
                max-height: {place_min_h}px;
                min-height: {place_min_h}px;
                color: white;
                font-size: {font_place}px;
                font-weight: 500;
                margin: 0px;
            """)
            
        else:
            # Base values for Large state
            font_title = 19 * scale
            font_time = 13 * scale
            font_place = 12 * scale
            h_progress = max(4, int(8 * scale))
            
            margin_v = int(10 * scale)
            margin_h_left = int(25 * scale)
            margin_h_right = int(35 * scale)
            spacing = int(5 * scale)
            
            place_radius = int(12 * scale)
            place_padding = int(10 * scale)
            place_min_h = int(24 * scale)
            
            # Apply styles
            self.lbl_name.setStyleSheet(f"color: white; font-weight: 600; font-size: {font_title}px; background: transparent;")
            self.lbl_time.setStyleSheet(f"color: rgba(255,255,255,230); font-size: {font_time}px; background: transparent;")
            self.progress_bar.setFixedHeight(h_progress)
            self.layout.setContentsMargins(margin_h_left, margin_v, margin_h_right, margin_v)
            self.layout.setSpacing(spacing)
            
            self.lbl_place.setStyleSheet(f"""
                background: rgba(255, 255, 255, 25);
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: {place_radius}px;
                padding: 0px {place_padding}px;
                min-width: {40*scale}px;
                max-height: {place_min_h}px;
                min-height: {place_min_h}px;
                color: white;
                font-size: {font_place}px;
                font-weight: 500;
                margin: 0px;
            """)


    # ===== Metody dostępu do ustawień (delegacja do SettingsManager) =====
    def get_current_settings(self):
        """Zwraca aktualne ustawienia z cache"""
        return self.settings_manager.get_current_settings()

    def get_group_settings(self):
        """Pobiera aktualne ustawienia grup z cache"""
        return self.settings_manager.get_group_settings()

    def update_settings(self, new_settings):
        """Aktualizuje ustawienia w cache i zapisuje do pliku"""
        self.settings_manager.update_settings(new_settings)
        # Aktualizuj stan widgetu na podstawie nowych ustawień
        self._apply_ui_settings(new_settings)

    def update_group_settings(self, group_settings):
        """Aktualizuje ustawienia grup w cache"""
        self.settings_manager.update_group_settings(group_settings)

    def save_settings(self):
        """Zapisuje ustawienia z opóźnieniem"""
        # Najpierw zaktualizuj cache z aktualnymi wartościami widgetu
        settings_to_save = {
            "opacity": round(self.windowOpacity(), 2),
            "scale": round(self.width() / self.original_width, 2),
            "clickthrough": self._clickthrough_enabled,
            "drag_enabled": self.drag_enabled,
            "scaling_enabled": self.scaling_enabled,
            "position": [self.x(), self.y()],
            "width": self.width(),
            "height": self.height()
        }
        self.settings_manager.update_settings(settings_to_save)

    def save_settings_immediately(self):
        """Zapisuje ustawienia natychmiast (dla SettingsWindow)"""
        # Najpierw zaktualizuj cache
        self.save_settings()
        # Potem zapisz natychmiast
        self.settings_manager.save_settings_immediately()

    def _apply_ui_settings(self, settings):
        """Stosuje ustawienia UI bez wywoływania save_settings (zapobiega pętli)"""
        if "opacity" in settings:
            self.setWindowOpacity(settings["opacity"])
        if "clickthrough" in settings:
            self._clickthrough_enabled = settings["clickthrough"]
            self.apply_clickthrough_state()
        if "drag_enabled" in settings:
            self.drag_enabled = settings["drag_enabled"]
        if "scaling_enabled" in settings:
            self.scaling_enabled = settings["scaling_enabled"]
            self.update()

    # ===== Clickthrough =====
    def enable_clickthrough(self):
        """Włącza clickthrough - okno staje się przezroczyste dla myszy"""
        self._clickthrough_enabled = True
        if self.isVisible():
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
                | Qt.WindowType.WindowTransparentForInput
            )
            self.show()
        
        self.update_ui_states()
        self.settings_manager.request_save_settings()

    def disable_clickthrough(self):
        """Wyłącza clickthrough - okno reaguje na mysz"""
        self._clickthrough_enabled = False
        if self.isVisible():
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.show()
        
        self.update_ui_states()
        self.settings_manager.request_save_settings()

    def toggle_clickthrough_option(self, state):
        """Przełączanie clickthrough z aktualizacją UI"""
        if state == Qt.CheckState.Checked.value:
            self.enable_clickthrough()
        else:
            self.disable_clickthrough()
        self.update_ui_states()

    # @property
    # def is_resize_allowed(self):
    #     """Check if resizing is allowed (either scaling enabled OR interactive mode)"""
    #     return self.scaling_enabled or not self._clickthrough_enabled

    def apply_clickthrough_state(self):
        """Stosuje aktualny stan clickthrough bez zmiany flagi"""
        # Hide first to avoid flickering and errors during flag change
        was_visible = self.isVisible()
        if was_visible:
            self.hide()

        if self._clickthrough_enabled:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
                | Qt.WindowType.WindowTransparentForInput
            )
        else:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
        
        # CRITICAL FIX: Re-apply translucency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        if was_visible:
            self.show()
            self.update()

    # ===== Drag =====
    def set_drag_enabled(self, enabled):
        """Ustawia stan drag i aktualizuje UI"""
        self.drag_enabled = enabled
        self.update_ui_states()
        self.settings_manager.request_save_settings()

    def toggle_drag_option(self, state):
        """Przełączanie drag z aktualizacją UI"""
        self.drag_enabled = (state == Qt.CheckState.Checked.value)
        self.update_ui_states()
        self.settings_manager.request_save_settings()

    # ===== Scaling =====
    def set_scaling_enabled(self, enabled):
        """Ustawia stan scaling i aktualizuje UI"""
        self.scaling_enabled = enabled
        self.update_ui_states()
        self.settings_manager.request_save_settings()
        self.update()  # Odśwież aby pokazać/ukryć uchwyt resize

    def toggle_scaling_option(self, state):
        """Przełączanie scaling z aktualizacją UI"""
        self.scaling_enabled = (state == Qt.CheckState.Checked.value)
        self.update_ui_states()
        self.settings_manager.request_save_settings()
        self.update()  # Odśwież aby pokazać/ukryć uchwyt resize

    # ===== Toggle widoczności =====
    def toggle_overlay(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            # Zastosuj aktualny stan clickthrough
            self.apply_clickthrough_state()

    # ===== Opacity / Progress =====
    def update_opacity(self, value):
        """Zmiana przezroczystości"""
        opacity = max(0.1, min(value / 100.0, 1.0))
        self.setWindowOpacity(opacity)
        self.settings_manager.request_save_settings()

    def getProgress(self):
        return self._progress

    def setProgress(self, value: float):
        self._progress = max(0.0, min(1.0, value))
        # Update the modern progress bar widget
        if hasattr(self, 'progress_bar'):
            self.progress_bar.set_progress(self._progress)
        self.update()

    progress = pyqtProperty(float, fget=getProgress, fset=setProgress)

    def animateProgressTo(self, target_value: float):
        self.anim.stop()
        self.anim.setStartValue(self._progress)
        self.anim.setEndValue(max(0.0, min(1.0, target_value)))
        self.anim.start()
    
    def update_text_labels(self):
        """Update QLabel widgets when text properties change"""
        if hasattr(self, 'lbl_name'):
            self.lbl_name.setText(self.title)
        if hasattr(self, 'lbl_time'):
            self.lbl_time.setText(self.left_text)
        if hasattr(self, 'lbl_place'):
            self.lbl_place.setText(self.right_text)
        if hasattr(self, 'lbl_room'):
            self.lbl_room.setText(self.room_text)

    # ===== Malowanie (delegacja do ui_renderer) =====
    def paintEvent(self, event):
        painter = QPainter(self)
        paint_overlay(self, painter)
    
    def resizeEvent(self, event):
        """Handle resize events - position toggle button"""
        if hasattr(self, 'btn'):
            self.btn.move(self.width() - 32, 8)
        
        # Apply scaling to content
        self._apply_scaling()
            
        # Update position to maintain right-edge anchoring
        # self.move_to_top_right()  # REMOVED: Let user position it
        super().resizeEvent(event)

    # ===== Obsługa myszy (delegacja do mouse_handler) =====
    def mousePressEvent(self, event):
        if not self.mouse_handler.handle_mouse_press(event):
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.mouse_handler.handle_mouse_move(event):
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.mouse_handler.handle_mouse_release(event):
            super().mouseReleaseEvent(event)

    # ===== Wczytywanie ustawień =====
    def load_settings(self):
        """Wczytaj ustawienia do cache i zastosuj je"""
        settings = self.settings_manager.load_settings()
        self.apply_settings_from_cache(settings)

    def apply_settings_from_cache(self, settings):
        """Stosuje ustawienia z cache bez wywoływania metod zmieniających flagi"""
        # Wczytaj rozmiar i pozycję
        saved_width = settings.get("width", self.original_width)
        saved_height = settings.get("height", self.original_height)
        
        self.resize(saved_width, saved_height)
        self.scale_factor = saved_width / self.original_width
        
        # Wczytaj ustawienia z cache BEZ wywoływania metod enable/disable
        self.drag_enabled = settings.get("drag_enabled", True)
        self.scaling_enabled = settings.get("scaling_enabled", False)
        self.setWindowOpacity(settings.get("opacity", 1.0))
        
        # Ustaw flagę clickthrough bez wywoływania metod
        self._clickthrough_enabled = settings.get("clickthrough", True)
        
        # Zastosuj stan clickthrough
        self.apply_clickthrough_state()
        
        # Wczytaj pozycję
        pos = settings.get("position")
        if pos and len(pos) == 2:
            self.move(pos[0], pos[1])

    # ===== API (delegacja do update_manager) =====
    def start_minute_updates(self):
        """Rozpoczyna okresowe aktualizacje"""
        self.update_manager.start_updates()

    def are_groups_set(self):
        """Sprawdza czy wszystkie wymagane grupy są ustawione"""
        return self.update_manager.are_groups_set()

    # ===== Aktualizacja UI =====
    def update_ui_states(self):
        """Aktualizuje UI w settings i tray dla wszystkich stanów"""
        # Aktualizuj settings window
        if hasattr(self, 'settings_window') and self.settings_window:
            self.settings_window.clickthrough_checkbox.setChecked(self._clickthrough_enabled)
            self.settings_window.drag_checkbox.setChecked(self.drag_enabled)
            self.settings_window.scaling_checkbox.setChecked(self.scaling_enabled)
        
        # Aktualizuj tray
        if hasattr(self, 'tray') and self.tray:
            self.tray.update_all_states()

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
            # Zatrzymaj wszystkie timery i zapisz ustawienia
            self.settings_manager.stop_timers()
            self.update_manager.stop_timers()
            
            if hasattr(self, 'cursor_timer') and self.cursor_timer.isActive():
                self.cursor_timer.stop()
            
            keyboard.unhook_all_hotkeys()
            QApplication.quit()
