"""
Modern Progress Bar with animated shine effect
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient
from PyQt6.QtCore import Qt, QTimer


class ModernProgressBar(QWidget):
    """Custom progress bar with shimmer/shine animation effect"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)  # Default height
        self.percentage = 0.0  # Progress value (0.0 to 1.0)
        self._shine_pos = 0.0  # Shine position (0.0 to 1.0)
        
        # Timer for shine animation (~60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_shine)
        self.timer.start(100)  # ~10 FPS (Further reduced to save CPU)
    
    def update_shine(self):
        """Update shine position for animation"""
        self._shine_pos += 0.01
        if self._shine_pos > 2.0:  # Goes off screen and wraps
            self._shine_pos = -0.5
        self.update()
    
    def set_progress(self, value: float):
        """Set progress value (0.0 to 1.0)"""
        self.percentage = max(0.0, min(1.0, value))
        self.update()
    
    def paintEvent(self, event):
        """Draw the progress bar with shine effect"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        w = rect.width()
        h = rect.height()
        
        # 1. Track background - rgba(255, 255, 255, 0.1)
        bg_path = QPainterPath()
        bg_path.addRoundedRect(0, 0, w, h, h/2, h/2)
        painter.fillPath(bg_path, QColor(255, 255, 255, 25))
        
        # 2. Fill gradient - #3cb354 → #5ee07a
        fill_w = w * self.percentage
        if fill_w > 0:
            fill_path = QPainterPath()
            fill_path.addRoundedRect(0, 0, fill_w, h, h/2, h/2)
            
            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0, QColor("#3cb354"))
            grad.setColorAt(1, QColor("#5ee07a"))
            painter.fillPath(fill_path, grad)
            
            # 3. Shine effect (animated gradient overlay)
            shine_w = w  # Shine width
            x_pos = (self._shine_pos * w) - shine_w
            
            shine_grad = QLinearGradient(x_pos, 0, x_pos + shine_w, 0)
            shine_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
            shine_grad.setColorAt(0.5, QColor(255, 255, 255, 50))  # 0.2 alpha
            shine_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
            painter.fillPath(fill_path, shine_grad)
