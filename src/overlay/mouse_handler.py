"""
Moduł obsługujący interakcje myszy (drag & drop, resize)
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor


class MouseHandler:
    """Obsługuje interakcje myszy dla overlay"""
    
    def __init__(self, widget):
        self.widget = widget
        self._drag_active = False
        self._drag_position = None
        self._was_clickthrough = False
        
        self._resize_active = False
        self._resize_corner = None
        self._resize_start_pos = None
        self._resize_start_size = None
        
        # Śledzenie poprzedniej pozycji kursora
        self._last_cursor_over_resize = False
    
    def check_cursor_position(self):
        """Optymalizowane sprawdzanie pozycji kursora"""
        try:
            global_pos = QCursor.pos()
            local_pos = self.widget.mapFromGlobal(global_pos)
            
            # Sprawdź tylko uchwyt resize
            current_over_resize = (self.widget.scaling_enabled and 
                                  hasattr(self.widget, "resize_handle_rect") and
                                  self.widget.resize_handle_rect is not None and
                                  self.widget.resize_handle_rect.contains(local_pos.toPointF()))
            
            # Sprawdź zmiany stanu
            resize_just_left = self._last_cursor_over_resize and not current_over_resize
            
            # Aktualizuj poprzedni stan
            self._last_cursor_over_resize = current_over_resize
            
            # Ustaw kursor
            if current_over_resize:
                self.widget.setCursor(Qt.CursorShape.SizeBDiagCursor)  # Backslash diagonal for bottom-left
                if self.widget._clickthrough_enabled:
                    self.widget.disable_clickthrough()
            elif self.widget.drag_enabled:
                 self.widget.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.widget.setCursor(Qt.CursorShape.ArrowCursor)
                # PRZYWRÓĆ CLICKTHROUGH GDY KURSOR OPUSZCZA OBSZAR INTERAKTYWNY
                if resize_just_left and self.widget._clickthrough_enabled:
                    self.widget.enable_clickthrough()
        except Exception as e:
            print("Błąd w check_cursor_position:", e)
    
    def handle_mouse_press(self, event):
        """Obsługuje wciśnięcie przycisku myszy"""
        # Sprawdź czy kliknięto w uchwyt resize (TYLKO jeśli skalowanie włączone i rect istnieje)
        if (self.widget.scaling_enabled and hasattr(self.widget, "resize_handle_rect") and
            self.widget.resize_handle_rect is not None and
            self.widget.resize_handle_rect.contains(event.position())):
            self._resize_active = True
            self._resize_corner = "bottom_left"
            self._resize_start_pos = event.globalPosition().toPoint()
            self._resize_start_size = self.widget.size()
            self._resize_start_geo = self.widget.geometry()  # Need geometry for position
            
            # Capture current aspect ratio
            if self.widget.height() > 0:
                self._aspect_ratio = self.widget.width() / self.widget.height()
            else:
                self._aspect_ratio = 4.2 # Fallback
                
            self._was_clickthrough = self.widget._clickthrough_enabled
            self.widget.disable_clickthrough()
            event.accept()
            return True
        
        # TYLKO JEŚLI DRAG JEST WŁĄCZONY
        if self.widget.drag_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_position = event.globalPosition().toPoint() - self.widget.frameGeometry().topLeft()
            self._was_clickthrough = self.widget._clickthrough_enabled
            self.widget.disable_clickthrough()
            event.accept()
            return True
        
        return False
    
    def handle_mouse_move(self, event):
        """Obsługuje ruch myszy"""
        # Sprawdź kursor jeśli nie ma aktywnej akcji
        if not self._resize_active and not self._drag_active:
            self.check_cursor_position()
            
        # Obsługa resize (TYLKO jeśli skalowanie włączone)
        if self._resize_active and self.widget.scaling_enabled:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            
            if self._resize_corner == "bottom_left":
                # Calculate potential width change from X movement (Left = Grow)
                width_change_from_x = -delta.x()
                
                # Calculate potential width change from Y movement (Down = Grow)
                # Width change = Height change * aspect_ratio
                width_change_from_y = delta.y() * self._aspect_ratio
                
                # Use the one with larger magnitude to drive the resize for better responsiveness
                if abs(width_change_from_x) > abs(width_change_from_y):
                    change = width_change_from_x
                else:
                    change = width_change_from_y
                
                new_width = max(self.widget.minimumWidth(), self._resize_start_size.width() + int(change))
                
                # Use captured aspect ratio
                new_height = int(new_width / self._aspect_ratio)
                new_height = max(self.widget.minimumHeight(), min(new_height, self.widget.maximumHeight()))
                
                # Jeśli wysokość osiągnęła limit, dostosuj szerokość
                if new_height == self.widget.maximumHeight():
                    new_width = int(new_height * self._aspect_ratio)
                elif new_height == self.widget.minimumHeight():
                    new_width = int(new_height * self._aspect_ratio)
                
                # Calculate new position (right edge must stay fixed relative to screen, but we are moving left edge)
                # New X = Start X + (Start Width - New Width)
                new_x = self._resize_start_geo.x() + (self._resize_start_size.width() - new_width)
                
                self.widget.setGeometry(new_x, self.widget.y(), new_width, new_height)
            
            # self.widget.scale_factor = self.widget.width() / self.widget.original_width # Moved to overlay.resizeEvent or _apply_scaling
            # self.widget.radius = int(12 * self.widget.scale_factor)  # Zaktualizuj radius
            
            event.accept()
            return True
        
        # TYLKO JEŚLI DRAG JEST WŁĄCZONY
        if self._drag_active and self.widget.drag_enabled and event.buttons() & Qt.MouseButton.LeftButton:
            self.widget.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return True
        
        return False
    
    def handle_mouse_release(self, event):
        """Obsługuje zwolnienie przycisku myszy"""
        if self._resize_active and event.button() == Qt.MouseButton.LeftButton:
            self._resize_active = False
            self._resize_corner = None
            self._resize_start_pos = None
            self._resize_start_size = None
            
            if self._was_clickthrough:
                self.widget.enable_clickthrough()
            
            self.widget.settings_manager.request_save_settings()
            event.accept()
            return True
        
        if self._drag_active and event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = False
            self._drag_position = None
            if self._was_clickthrough:
                self.widget.enable_clickthrough()
            self.widget.settings_manager.request_save_settings()
            event.accept()
            return True
        
        return False
