from src.settings_window import SettingsWindow
from src import api
from src import api2
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont, QMouseEvent, QCursor, QLinearGradient
from PyQt6.QtCore import Qt, QRectF, pyqtProperty, QPropertyAnimation, QEasingCurve, QTimer, QMutex
from PyQt6.QtGui import QGuiApplication
import keyboard
import json, os
from datetime import datetime

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

        # Styl - NOWA PALETA KOLORÓW
        self.bg_color = QColor(23, 28, 40, 240)  # Ciemniejszy, bardziej nowoczesny
        self.progress_gradient_start = QColor(74, 144, 226)  # Niebieski
        self.progress_gradient_end = QColor(103, 230, 220)   # Cyjan
        self.text_color = QColor(240, 244, 255, 255)  # Bardziej czytelny biały
        self.shadow_color = QColor(10, 15, 25, 120)   # Lżejszy cień
        self.progress_track_color = QColor(45, 55, 75, 180)  # Kolor tła paska
        self.radius = 12  # Mniejsze zaokrąglenie

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

        # Timer kursora - ZOPTYMALIZOWANY
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self.check_cursor_position)
        self.cursor_timer.start(500)  # 500ms zamiast 200ms
        
        # Śledzenie poprzedniej pozycji kursora
        self._last_cursor_over_gear = False
        self._last_cursor_over_resize = False

        # Cache ustawień w pamięci
        self._settings_cache = {}
        
        # Mutex dla bezpiecznego dostępu do cache
        self._settings_mutex = QMutex()
        
        # Timer do opóźnionego zapisu ustawień
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._delayed_save_settings)
        self._save_pending = False
        
        # Wczytaj ustawienia do cache
        self.load_settings()

        # Okno ustawień
        self.settings_window = SettingsWindow(self)
        self.settings_window.hide()

        # Referencja do tray
        self.tray = None

        # Timery dla aktualizacji - ZOPTYMALIZOWANE
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.minute_update)
        
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.fast_progress_update)
        
        # Flaga zapobiegająca równoczesnym aktualizacjom API
        self._api_update_in_progress = False

    # ===== Optymalizowane zapisywanie ustawień =====
    def request_save_settings(self):
        """Żąda zapisu ustawień z opóźnieniem (debouncing)"""
        if not self._save_pending:
            self._save_pending = True
            self._save_timer.start(1000)  # Zapisz po 1 sekundzie bez zmian

    def _delayed_save_settings(self):
        """Wykonuje opóźniony zapis ustawień"""
        if self._save_pending:
            self._save_settings_impl()
            self._save_pending = False

    def _save_settings_impl(self):
        """Faktyczna implementacja zapisu ustawień"""
        try:
            self._settings_mutex.lock()
            
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
            
            # Aktualizuj tylko zmienione ustawienia
            self._settings_cache.update(settings_to_save)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._settings_cache, f, indent=4)
                            
        except Exception as e:
            print("Błąd zapisu ustawień:", e)
        finally:
            self._settings_mutex.unlock()

    def save_settings(self):
        """Zachowaj kompatybilność - użyj opóźnionego zapisu"""
        self.request_save_settings()

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
        self.request_save_settings()

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
        
        # Aktualizuj UI
        self.update_ui_states()
        self.request_save_settings()

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
        self.request_save_settings()

    def toggle_drag_option(self, state):
        """Przełączanie drag z aktualizacją UI"""
        self.drag_enabled = (state == Qt.CheckState.Checked.value)
        self.update_ui_states()
        self.request_save_settings()

    # ===== Scaling =====
    def set_scaling_enabled(self, enabled):
        """Ustawia stan scaling i aktualizuje UI"""
        self.scaling_enabled = enabled
        self.update_ui_states()
        self.request_save_settings()
        self.update()  # Odśwież aby pokazać/ukryć uchwyt resize

    def toggle_scaling_option(self, state):
        """Przełączanie scaling z aktualizacją UI"""
        self.scaling_enabled = (state == Qt.CheckState.Checked.value)
        self.update_ui_states()
        self.request_save_settings()
        self.update()  # Odśwież aby pokazać/ukryć uchwyt resize

    def check_cursor_position(self):
        """Optymalizowane sprawdzanie pozycji kursora"""
        try:
            global_pos = QCursor.pos()
            local_pos = self.mapFromGlobal(global_pos)
            
            # Sprawdź tylko uchwyt resize (zębatka usunięta)
            current_over_resize = (self.scaling_enabled and hasattr(self, "resize_handle_rect") 
                                  and self.resize_handle_rect is not None
                                  and self.resize_handle_rect.contains(local_pos.toPointF()))
            
            # Sprawdź zmiany stanu
            resize_just_left = self._last_cursor_over_resize and not current_over_resize
            
            # Aktualizuj poprzedni stan
            self._last_cursor_over_resize = current_over_resize
            
            # Ustaw kursor
            if current_over_resize:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                if self._clickthrough_enabled:
                    self.disable_clickthrough()
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
                # PRZYWRÓĆ CLICKTHROUGH GDY KURSOR OPUSZCZA OBSZAR INTERAKTYWNY
                if resize_just_left and self._clickthrough_enabled:
                    self.enable_clickthrough()
        except Exception as e:
            print("Błąd w check_cursor_position:", e)

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
        self.request_save_settings()

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

    # ===== Malowanie - POPRAWIONA WERSJA (BEZ ZĘBATKI) =====
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # --- Tło z lekkim gradientem ---
        bg_gradient = QLinearGradient(0, 0, 0, rect.height())
        bg_gradient.setColorAt(0, QColor(28, 33, 45, 240))
        bg_gradient.setColorAt(1, QColor(23, 28, 40, 240))
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self.radius, self.radius)
        painter.fillPath(path, bg_gradient)

        # --- Cień wewnętrzny dla głębi ---
        painter.setPen(QColor(255, 255, 255, 15))
        painter.drawRoundedRect(QRectF(rect.x() + 0.5, rect.y() + 0.5, rect.width() - 1, rect.height() - 1), 
                              self.radius, self.radius)

        # --- Pasek postępu - NOWY WYGLĄD ---
        bar_height = int(10 * self.scale_factor)  # Nieco cieńszy pasek
        bar_margin_top = int(50 * self.scale_factor)  # Pozycja paska
        radius_scaled = int(6 * self.scale_factor)  # Mniejsze zaokrąglenie dla paska

        # Tło paska (track)
        track_rect = QRectF(
            rect.x() + 15 * self.scale_factor,
            rect.y() + bar_margin_top,
            rect.width() - 30 * self.scale_factor,
            bar_height
        )
        
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, radius_scaled, radius_scaled)
        painter.fillPath(track_path, self.progress_track_color)

        # Zielony pasek postępu z gradientem
        progress_width = int(track_rect.width() * max(0.0, min(1.0, self._progress)))
        if progress_width > 0:
            progress_rect = QRectF(
                track_rect.x(),
                track_rect.y(),
                progress_width,
                bar_height
            )
            
            progress_path = QPainterPath()
            progress_path.addRoundedRect(progress_rect, radius_scaled, radius_scaled)
            
            # Gradient dla paska postępu
            progress_gradient = QLinearGradient(
                progress_rect.x(), progress_rect.y(),
                progress_rect.x(), progress_rect.y() + progress_rect.height()
            )
            progress_gradient.setColorAt(0, self.progress_gradient_start)
            progress_gradient.setColorAt(1, self.progress_gradient_end)
            
            painter.fillPath(progress_path, progress_gradient)

            # Efekt świetlny na górze paska
            highlight_gradient = QLinearGradient(
                progress_rect.x(), progress_rect.y(),
                progress_rect.x(), progress_rect.y() + progress_rect.height() * 0.4
            )
            highlight_gradient.setColorAt(0, QColor(255, 255, 255, 60))
            highlight_gradient.setColorAt(1, QColor(255, 255, 255, 0))
            
            highlight_path = QPainterPath()
            highlight_path.addRoundedRect(progress_rect, radius_scaled, radius_scaled)
            painter.fillPath(highlight_path, highlight_gradient)

        # --- Teksty ---
        # Tytuł
        painter.setFont(QFont("Segoe UI", int(18 * self.scale_factor), QFont.Weight.Bold))
        painter.setPen(self.shadow_color)
        painter.drawText(rect.adjusted(1, int(28 * self.scale_factor), 1, 0), 
                        Qt.AlignmentFlag.AlignHCenter, self.title)
        painter.setPen(self.text_color)
        painter.drawText(rect.adjusted(0, int(25 * self.scale_factor), 0, 0), 
                        Qt.AlignmentFlag.AlignHCenter, self.title)

        # Tekst dolny
        painter.setFont(QFont("Segoe UI", int(11 * self.scale_factor)))
        painter.setPen(self.shadow_color)
        painter.drawText(rect.adjusted(int(27 * self.scale_factor), int(72 * self.scale_factor), 2, 0), 
                        Qt.AlignmentFlag.AlignLeft, self.left_text)
        painter.drawText(rect.adjusted(-int(23 * self.scale_factor), int(72 * self.scale_factor), -int(18 * self.scale_factor), 0), 
                        Qt.AlignmentFlag.AlignRight, self.right_text)
        painter.setPen(self.text_color)
        painter.drawText(rect.adjusted(int(25 * self.scale_factor), int(70 * self.scale_factor), 0, 0), 
                        Qt.AlignmentFlag.AlignLeft, self.left_text)
        painter.drawText(rect.adjusted(-int(25 * self.scale_factor), int(70 * self.scale_factor), -int(20 * self.scale_factor), 0), 
                        Qt.AlignmentFlag.AlignRight, self.right_text)

        # --- Uchwyt do resize w prawym dolnym rogu (TYLKO jeśli skalowanie włączone) ---
        if self.scaling_enabled:
            handle_size = int(25 * self.scale_factor)
            self.resize_handle_rect = QRectF(
                rect.width() - handle_size - 4 * self.scale_factor,
                rect.height() - handle_size - 4 * self.scale_factor,
                handle_size,
                handle_size
            )
            
            # Nowy styl uchwytu resize
            resize_path = QPainterPath()
            resize_path.moveTo(self.resize_handle_rect.right(), self.resize_handle_rect.bottom())
            resize_path.lineTo(self.resize_handle_rect.right(), self.resize_handle_rect.top() + handle_size * 0.6)
            resize_path.lineTo(self.resize_handle_rect.left() + handle_size * 0.6, self.resize_handle_rect.bottom())
            resize_path.closeSubpath()
            
            painter.fillPath(resize_path, QColor(100, 110, 130, 200))

    # ===== Drag & Drop =====
    def mousePressEvent(self, event: QMouseEvent):
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
            self.radius = int(12 * self.scale_factor)  # Zaktualizuj radius
            
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
                
            self.request_save_settings()
            event.accept()
            return
            
        if self._drag_active and event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = False
            self._drag_position = None
            if self._was_clickthrough:
                self.enable_clickthrough()
            self.request_save_settings()
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
            
            # Użyj opóźnionego zapisu
            self.request_save_settings()
                            
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
        # Timer dla aktualizacji danych co 30 sekund (zamiast 20)
        self.update_timer.start(30000)
        
        # Timer dla płynnego odświeżania progress bara co 10 sekund (zamiast 5)
        self.progress_timer.start(10000)
        
        # Od razu wykonaj pierwszą aktualizację
        self.minute_update()

    def minute_update(self):
        """Aktualizuje wszystkie dane co minutę"""
        if self._api_update_in_progress:
            return  # Pomijaj jeśli aktualizacja już trwa
            
        try:
            self._api_update_in_progress = True
            
            # UŻYJ USTAWIEN Z CACHE zamiast wczytywać z pliku        
            currentLesson = api2.get_current_segment() or {
                "syllabus": "Brak zajęć", 
                "remaining_time": 0, 
                "total_duration": 0, 
                "is_break": False, 
                "time_elapsed": 0
            }
            
            # Pobierz następną lekcję
            nextLesson = api2.get_next_segment() or {
                "syllabus": "Brak dalszych zajęć",
                "hall": "-",
            }

            self.title = currentLesson.get("syllabus", "Brak zajęć")
            
            # ZAPISZ DANE JAKO ATRYBUTY DLA SZYBKIEGO ODŚWIEŻANIA
            self.currentLesson = currentLesson
            self.nextLesson = nextLesson
            
            # Zaktualizuj progress bar od razu
            self.update_progress()
            
        except Exception as e:
            print("Błąd podczas aktualizacji danych:", e)
        finally:
            self._api_update_in_progress = False

    def fast_progress_update(self):
        """Szybka aktualizacja tylko progress bara"""
        if hasattr(self, 'currentLesson') and not self._api_update_in_progress:
            self.update_progress()

    def update_progress(self):
        """Aktualizuje progress bar - teraz proste obliczenia"""
        if not hasattr(self, 'currentLesson'):
            return
            
        try:
            # Pobierz czasy z aktualnej lekcji
            start_time_str = self.currentLesson.get("start")
            end_time_str = self.currentLesson.get("end")
            
            if not start_time_str or not end_time_str:
                self.setProgress(0.0)
                return
                
            # Pobierz aktualną datę
            today = datetime.now().date()
            
            # Połącz aktualną datę z czasem rozpoczęcia i zakończenia
            start_datetime = datetime.combine(today, datetime.strptime(start_time_str, '%H:%M').time())
            end_datetime = datetime.combine(today, datetime.strptime(end_time_str, '%H:%M').time())
            
            current_time = datetime.now()
            
            # Jeśli lekcja kończy się po północy, dodaj jeden dzień do czasu zakończenia
            if end_datetime < start_datetime:
                end_datetime = end_datetime.replace(day=end_datetime.day + 1)
            
            # Oblicz całkowity czas trwania i czas pozostały
            total_duration = (end_datetime - start_datetime).total_seconds() / 60  # w minutach
            elapsed_time = (current_time - start_datetime).total_seconds() / 60  # w minutach
            remaining_time = (end_datetime - current_time).total_seconds() / 60  # w minutach

            self.left_text = f"{round(remaining_time)}min → {self.nextLesson.get('syllabus', '-')}"
            self.right_text = self.nextLesson.get("hall", "-")

            # Oblicz postęp (0.0 - 1.0)
            if total_duration > 0:
                progress = min(max(elapsed_time / total_duration, 0.0), 1.0)
            else:
                progress = 0.0
                
            self.setProgress(progress)
            
        except Exception as e:
            print(f"Błąd podczas aktualizacji postępu: {e}")
            self.setProgress(0.0)

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
            # Zapisz natychmiast przy zamknięciu
            self._save_timer.stop()
            if self._save_pending:
                self._delayed_save_settings()
                
            if hasattr(self, 'cursor_timer') and self.cursor_timer.isActive():
                self.cursor_timer.stop()
            if hasattr(self, 'update_timer') and self.update_timer.isActive():
                self.update_timer.stop()
            if hasattr(self, 'progress_timer') and self.progress_timer.isActive():
                self.progress_timer.stop()
            keyboard.unhook_all_hotkeys()
            QApplication.quit()