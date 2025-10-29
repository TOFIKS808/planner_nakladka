from src.settings_window import SettingsWindow
from src import api
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox
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
        self.bg_color = QColor(31, 35, 43, 255)
        self.progress_color = QColor(46, 139, 87, 255)
        self.text_color = QColor(255, 255, 255, 255)
        self.shadow_color = QColor(0, 0, 0, 100)
        self.radius = 15

        # Zezwól na zmianę rozmiaru
        self.setMinimumSize(200, 48)
        self.setMaximumSize(800, 190)

        # Stan overlay
        self._progress = progress
        self._clickthrough_enabled = True  # Domyślnie włączone
        self.drag_enabled = True
        self.scaling_enabled = False  # Domyślnie WYŁĄCZONE skalowanie

        # Rozmiar początkowy
        self.original_width = 420
        self.original_height = 100
        self.scale_factor = 1.0
        self.resize(self.original_width, self.original_height)

        # Przenoszenie
        self._drag_active = False
        self._drag_position = None
        self._was_clickthrough = False

        # Resize
        self._resize_active = False
        self._resize_corner = None
        self._resize_start_pos = None
        self._resize_start_size = None

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
        try:
            keyboard.remove_hotkey("ctrl+q")
        except Exception:
            pass
        keyboard.add_hotkey("ctrl+q", self.toggle_overlay)

        # Timer kursora
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self.check_cursor_position)
        self.cursor_timer.start(200)
        
        # Śledzenie poprzedniej pozycji kursora
        self._last_cursor_over_gear = False
        self._last_cursor_over_resize = False

        # Cache ustawień w pamięci
        self._settings_cache = {}
        
        # Wczytaj ustawienia do cache
        self.load_settings()

        # Okno ustawień
        self.settings_window = SettingsWindow(self)
        self.settings_window.hide()

        # Referencja do tray
        self.tray = None

        # Timery dla aktualizacji
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.minute_update)
        
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.fast_progress_update)

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
        
        # Aktualizuj UI
        self.update_ui_states()
        self.save_settings()

    def disable_clickthrough(self):
        """Wyłącza clickthrough - okno reaguje na mysz"""
        print("Disabling clickthrough")
        self._clickthrough_enabled = False
        if self.isVisible():
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.show()
        
        # Aktualizuj UI
        self.update_ui_states()
        self.save_settings()

    def toggle_clickthrough_option(self, state):
        """Przełączanie clickthrough z aktualizacją UI"""
        if state == Qt.CheckState.Checked.value:
            self.enable_clickthrough()
        else:
            self.disable_clickthrough()
        self.update_ui_states()

    def apply_clickthrough_state(self):
        """Stosuje aktualny stan clickthrough bez zmiany flagi"""
        if self._clickthrough_enabled:
            if self.isVisible():
                self.setWindowFlags(
                    Qt.WindowType.FramelessWindowHint
                    | Qt.WindowType.WindowStaysOnTopHint
                    | Qt.WindowType.Tool
                    | Qt.WindowType.WindowTransparentForInput
                )
                self.show()
        else:
            if self.isVisible():
                self.setWindowFlags(
                    Qt.WindowType.FramelessWindowHint
                    | Qt.WindowType.WindowStaysOnTopHint
                    | Qt.WindowType.Tool
                )
                self.show()

    # ===== Drag =====
    def set_drag_enabled(self, enabled):
        """Ustawia stan drag i aktualizuje UI"""
        self.drag_enabled = enabled
        self.update_ui_states()
        self.save_settings()

    def toggle_drag_option(self, state):
        """Przełączanie drag z aktualizacją UI"""
        self.drag_enabled = (state == Qt.CheckState.Checked.value)
        self.update_ui_states()
        self.save_settings()

    # ===== Scaling =====
    def set_scaling_enabled(self, enabled):
        """Ustawia stan scaling i aktualizuje UI"""
        self.scaling_enabled = enabled
        self.update_ui_states()
        self.save_settings()
        self.update()  # Odśwież aby pokazać/ukryć uchwyt resize

    def toggle_scaling_option(self, state):
        """Przełączanie scaling z aktualizacją UI"""
        self.scaling_enabled = (state == Qt.CheckState.Checked.value)
        self.update_ui_states()
        self.save_settings()
        self.update()  # Odśwież aby pokazać/ukryć uchwyt resize

    def check_cursor_position(self):
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        
        current_over_gear = hasattr(self, "gear_rect") and self.gear_rect.contains(local_pos.toPointF())
        current_over_resize = (self.scaling_enabled and hasattr(self, "resize_handle_rect") 
                              and self.resize_handle_rect is not None
                              and self.resize_handle_rect.contains(local_pos.toPointF()))
        
        # Sprawdź zmiany stanu
        gear_just_left = self._last_cursor_over_gear and not current_over_gear
        resize_just_left = self._last_cursor_over_resize and not current_over_resize
        gear_just_entered = not self._last_cursor_over_gear and current_over_gear
        resize_just_entered = not self._last_cursor_over_resize and current_over_resize
        
        # Aktualizuj poprzedni stan
        self._last_cursor_over_gear = current_over_gear
        self._last_cursor_over_resize = current_over_resize
        
        # Ustaw kursor
        if current_over_gear:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            if self._clickthrough_enabled:
                self.disable_clickthrough()
        elif current_over_resize:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            if self._clickthrough_enabled:
                self.disable_clickthrough()
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # PRZYWRÓĆ CLICKTHROUGH GDY KURSOR OPUSZCZA OBSZAR INTERAKTYWNY
            if (gear_just_left or resize_just_left) and self._clickthrough_enabled:
                self.enable_clickthrough()

    # ===== Panel ustawień =====
    def toggle_settings(self):
        if hasattr(self, "settings_window"):
            if self.settings_window.isVisible():
                self.settings_window.hide()
                # Przywróć clickthrough po zamknięciu ustawień
                if self._clickthrough_enabled:
                    self.apply_clickthrough_state()
            else:
                self.settings_window.show()
                self.settings_window.raise_()
                # Wyłącz clickthrough gdy ustawienia są otwarte
                self.disable_clickthrough()

    # ===== Toggle widoczności =====
    def toggle_overlay(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            # Zastosuj aktualny stan clickthrough
            self.apply_clickthrough_state()

    # ===== Opacity / Scale / Progress =====
    def update_opacity(self, value):
        """Zmiana przezroczystości"""
        opacity = max(0.1, min(value / 100.0, 1.0))
        self.setWindowOpacity(opacity)
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
        progress_width = int(rect.width() * max(0.0, min(1.0, self._progress)))
        if progress_width > 0:
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

        # --- Uchwyt do resize w prawym dolnym rogu (TYLKO jeśli skalowanie włączone) ---
        if self.scaling_enabled:
            handle_size = int(12 * self.scale_factor)
            self.resize_handle_rect = QRectF(
                rect.width() - handle_size - 2,
                rect.height() - handle_size - 2,
                handle_size,
                handle_size
            )
            
            painter.setBrush(QColor(100, 100, 100, 150))
            painter.setPen(Qt.PenStyle.NoPen)
            
            handle_path = QPainterPath()
            handle_path.moveTo(self.resize_handle_rect.right(), self.resize_handle_rect.bottom())
            handle_path.lineTo(self.resize_handle_rect.right(), self.resize_handle_rect.top())
            handle_path.lineTo(self.resize_handle_rect.left(), self.resize_handle_rect.bottom())
            handle_path.closeSubpath()
            
            painter.drawPath(handle_path)
        else:
            self.resize_handle_rect = None

    # ===== Drag & Drop =====
    def mousePressEvent(self, event: QMouseEvent):
        if hasattr(self, "gear_rect") and self.gear_rect.contains(event.position()):
            self.toggle_settings()
            event.accept()
            return

        # Sprawdź czy kliknięto w uchwyt resize (TYLKO jeśli skalowanie włączone i rect istnieje)
        if (self.scaling_enabled and hasattr(self, "resize_handle_rect")
            and self.resize_handle_rect is not None
            and self.resize_handle_rect.contains(event.position())):
            self._resize_active = True
            self._resize_corner = "bottom_right"
            self._resize_start_pos = event.globalPosition().toPoint()
            self._resize_start_size = self.size()
            self._was_clickthrough = self._clickthrough_enabled
            self.disable_clickthrough()
            event.accept()
            return

        # TYLKO JEŚLI DRAG JEST WŁĄCZONY
        if self.drag_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._was_clickthrough = self._clickthrough_enabled
            self.disable_clickthrough()
            event.accept()
            return
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Obsługa resize (TYLKO jeśli skalowanie włączone)
        if self._resize_active and self.scaling_enabled:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            
            if self._resize_corner == "bottom_right":
                new_width = max(self.minimumWidth(), self._resize_start_size.width() + delta.x())
                # Zachowaj proporcje 420:100 = 4.2:1
                new_height = int(new_width / 4.2)
                new_height = max(self.minimumHeight(), min(new_height, self.maximumHeight()))
                
                # Jeśli wysokość osiągnęła limit, dostosuj szerokość
                if new_height == self.maximumHeight():
                    new_width = int(new_height * 4.2)
                elif new_height == self.minimumHeight():
                    new_width = int(new_height * 4.2)
            
            self.resize(new_width, new_height)
            self.scale_factor = new_width / self.original_width
            self.radius = int(15 * self.scale_factor)
            
            event.accept()
            return
            
        # TYLKO JEŚLI DRAG JEST WŁĄCZONY
        if self._drag_active and self.drag_enabled and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return
            
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._resize_active and event.button() == Qt.MouseButton.LeftButton:
            self._resize_active = False
            self._resize_corner = None
            self._resize_start_pos = None
            self._resize_start_size = None
            
            if self._was_clickthrough:
                self.enable_clickthrough()
                
            self.save_settings()
            event.accept()
            return
            
        if self._drag_active and event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = False
            self._drag_position = None
            if self._was_clickthrough:
                self.enable_clickthrough()
            self.save_settings()
            event.accept()
            return
            
        super().mouseReleaseEvent(event)

    # ===== Zapis / Odczyt =====
    def load_settings(self):
        """Wczytaj ustawienia do cache"""
        try:
            if not os.path.exists(self.config_path):
                self._settings_cache = {
                    "opacity": 1.0,
                    "clickthrough": True,
                    "drag_enabled": True,
                    "scaling_enabled": False,
                    "group_c": None,
                    "group_l": None,
                    "group_k": None,
                    "scale": 1.0,
                    "position": [100, 100],
                    "width": 420,
                    "height": 100
                }
                # Zastosuj domyślne ustawienia
                self.apply_settings_from_cache()
                return
                    
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                
            # UPEWNIJ SIĘ ŻE WSZYSTKIE KLUCZE SĄ OBECNE
            default_settings = {
                "opacity": 1.0,
                "clickthrough": True,
                "drag_enabled": True,
                "scaling_enabled": False,
                "group_c": None,
                "group_l": None,
                "group_k": None,
                "scale": 1.0,
                "position": [100, 100],
                "width": 420,
                "height": 100
            }
            
            # Połącz załadowane dane z domyślnymi
            self._settings_cache = {**default_settings, **loaded_data}
            
            # Zastosuj ustawienia z cache
            self.apply_settings_from_cache()
                                    
        except Exception as e:
            print("Błąd podczas wczytywania ustawień:", e)
            self._settings_cache = {
                "opacity": 1.0,
                "clickthrough": True,
                "drag_enabled": True,
                "scaling_enabled": False,
                "group_c": None,
                "group_l": None,
                "group_k": None,
                "scale": 1.0,
                "position": [100, 100],
                "width": 420,
                "height": 100
            }
            self.apply_settings_from_cache()

    def apply_settings_from_cache(self):
        """Stosuje ustawienia z cache bez wywoływania metod zmieniających flagi"""
        # Wczytaj rozmiar i pozycję
        saved_width = self._settings_cache.get("width", self.original_width)
        saved_height = self._settings_cache.get("height", self.original_height)
        
        self.resize(saved_width, saved_height)
        self.scale_factor = saved_width / self.original_width
        
        # Wczytaj ustawienia z cache BEZ wywoływania metod enable/disable
        self.drag_enabled = self._settings_cache.get("drag_enabled", True)
        self.scaling_enabled = self._settings_cache.get("scaling_enabled", False)
        self.setWindowOpacity(self._settings_cache.get("opacity", 1.0))
        
        # Ustaw flagę clickthrough bez wywoływania metod
        self._clickthrough_enabled = self._settings_cache.get("clickthrough", True)
        
        # Zastosuj stan clickthrough
        self.apply_clickthrough_state()
        
        # Wczytaj pozycję
        pos = self._settings_cache.get("position")
        if pos and len(pos) == 2:
            self.move(pos[0], pos[1])

    def save_settings(self):
        """Zapisz ustawienia z cache"""
        try:
            # Aktualizuj cache przed zapisem
            self._settings_cache.update({
                "opacity": round(self.windowOpacity(), 2),
                "scale": round(self.width() / self.original_width, 2),
                "clickthrough": self._clickthrough_enabled,
                "drag_enabled": self.drag_enabled,
                "scaling_enabled": self.scaling_enabled,
                "position": [self.x(), self.y()],
                "width": self.width(),
                "height": self.height()
            })
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._settings_cache, f, indent=4)
                            
        except Exception as e:
            print("Błąd zapisu ustawień:", e)

    def get_current_settings(self):
        """Zwraca aktualne ustawienia z cache"""
        return self._settings_cache.copy()

    def update_settings(self, new_settings):
        """Aktualizuje ustawienia w cache i zapisuje do pliku - TYLKO przekazane wartości"""
        try:            
            # AKTUALIZUJ TYLKO PRZEKAZANE KLUCZE - nie usuwaj istniejących
            for key, value in new_settings.items():
                # ZAPISZ WARTOŚĆ NAWET JEŚLI JEST None - to oznacza "brak wybranej grupy"
                self._settings_cache[key] = value            
            # Zapisz do pliku
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._settings_cache, f, indent=4)
                            
        except Exception as e:
            print("Błąd aktualizacji ustawień:", e)

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

    # ===== API =====
    def start_minute_updates(self):
        """Rozpoczyna okresowe aktualizacje"""
        # Timer dla aktualizacji danych co minutę
        self.update_timer.start(20 * 1000)  # 20 sekund
        
        # Timer dla płynnego odświeżania progress bara co 5 sekund
        self.progress_timer.start(5000)  # 5 sekund
        
        # Od razu wykonaj pierwszą aktualizację
        self.minute_update()

    def minute_update(self):
        """Aktualizuje wszystkie dane co minutę"""
        # UŻYJ USTAWIEN Z CACHE zamiast wczytywać z pliku        
        current_hour_obj = api.get_current_hour()
        
        # PRZEKAŻ USTAWIENIA Z CACHE DO FUNKCJI API - użyj nowej funkcji z pełnym łączeniem
        currentLesson = api.get_current_lesson_with_full_block(self._settings_cache) or {
            "syllabus": "Brak zajęć", 
            "remaining_time": 0, 
            "total_duration": 45, 
            "is_break": False, 
            "time_elapsed": 0
        }
        
        # Pobierz następną lekcję
        nextLesson = api.get_next_lesson(current_hour_obj, self._settings_cache) or {
            "syllabus": "Brak dalszych zajęć", 
            "hall": "-"
        }

        # SPRAWDŹ CZY NASTĘPNA LEKCJA MA TĘ SAMĄ NAZWĘ CO AKTUALNA
        current_syllabus = currentLesson.get("syllabus", "")
        next_syllabus = nextLesson.get("syllabus", "")
        
        # Jeśli następna lekcja ma tę samą nazwę, znajdź prawdziwą następną lekcję
        if (current_syllabus == next_syllabus and 
            current_syllabus not in ["Brak zajęć", "Przerwa", "Brak dalszych zajęć", "Koniec zajęć"]):
            nextLesson = api.get_real_next_lesson(current_hour_obj, current_syllabus, self._settings_cache) or {
                "syllabus": "Brak dalszych zajęć", 
                "hall": "-"
            }

        self.title = currentLesson.get("syllabus", "Brak zajęć")
        
        # ZAPISZ DANE JAKO ATRYBUTY DLA SZYBKIEGO ODŚWIEŻANIA
        self.currentLesson = currentLesson
        self.nextLesson = nextLesson
        
        # Zaktualizuj progress bar od razu
        self.update_progress()

    def fast_progress_update(self):
        """Szybka aktualizacja tylko progress bara"""
        if hasattr(self, 'currentLesson'):
            self.update_progress()

    def update_progress(self):
        """Aktualizuje progress bar - teraz proste obliczenia"""
        if not hasattr(self, 'currentLesson'):
            return
            
        remaining_time = self.currentLesson.get("remaining_time", 0)
        total_duration = self.currentLesson.get("total_duration", 45)
        time_elapsed = self.currentLesson.get("time_elapsed", 0)
        is_break = self.currentLesson.get("is_break", False)

        self.left_text = f"{round(remaining_time)}min → {self.nextLesson.get('syllabus', '-')}"
        self.right_text = self.nextLesson.get("hall", "-")

        # OBLICZANIE PROGRESU
        if is_break:
            # Dla przerwy: progres = czas który minął / całkowity czas przerwy
            if total_duration > 0:
                progress = time_elapsed / total_duration
            else:
                progress = 0.0
        else:
            # Dla lekcji: progres = czas który minął / całkowity czas bloku
            if total_duration > 0:
                progress = time_elapsed / total_duration
            else:
                progress = 0.0
        
        progress = max(0.0, min(1.0, progress))
        
        self.setProgress(progress)

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
            self.save_settings()
            if hasattr(self, 'cursor_timer') and self.cursor_timer.isActive():
                self.cursor_timer.stop()
            if hasattr(self, 'update_timer') and self.update_timer.isActive():
                self.update_timer.stop()
            if hasattr(self, 'progress_timer') and self.progress_timer.isActive():
                self.progress_timer.stop()
            keyboard.unhook_all_hotkeys()
            QApplication.quit()