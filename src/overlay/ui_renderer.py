"""
Moduł odpowiedzialny za renderowanie UI overlay - Glassmorphism Design
"""
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtCore import Qt, QRectF


# Definicje kolorów dla glassmorphism
BG_COLOR = QColor(23, 28, 40, 180)  # Semi-transparent background
BORDER_TOP_COLOR = QColor(255, 255, 255, 50)  # Lighter top border
BORDER_COLOR = QColor(255, 255, 255, 25)  # Subtle border
RESIZE_HANDLE_COLOR = QColor(100, 110, 130, 200)


def paint_overlay(widget, painter):
    """Główna funkcja rysująca overlay z efektem glassmorphism"""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = widget.rect()
    
    # --- Glassmorphism background ---
    # rgba(23, 28, 40, 0.5) -> alpha ~128 (using 180 as in test.py for better visibility without blur)
    bg_color = QColor(23, 28, 40, 180)
    
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect), 20, 20)  # Radius 20px
    painter.fillPath(path, bg_color)
    
    # --- Top border highlight (glassmorphism effect) ---
    # Top border: rgba(255, 255, 255, 0.2) -> ~50 alpha
    pen_top = QPen(QColor(255, 255, 255, 50), 1)
    painter.setPen(pen_top)
    # Draw top arc (Left top corner)
    painter.drawArc(rect.left(), rect.top(), 40, 40, 1440, 1440) 
    # Top line
    painter.drawLine(20, 0, rect.width() - 20, 0)
    
    # --- Subtle border around the rest ---
    # Rest border: rgba(255, 255, 255, 0.1) -> ~25 alpha
    pen_rest = QPen(QColor(255, 255, 255, 25), 1)
    painter.setPen(pen_rest)
    painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 20, 20)
    
    # --- Uchwyt do resize (TYLKO jeśli skalowanie włączone) ---
    if widget.scaling_enabled:
        _draw_resize_handle(widget, painter, rect)


def _draw_resize_handle(widget, painter, rect):
    """Rysuje uchwyt do resize w lewym dolnym rogu"""
    handle_size = int(20 * widget.scale_factor)
    radius = 20  # Match the border radius from paint_overlay
    
    # Definiujemy obszar interaktywny (Lewy dolny róg)
    widget.resize_handle_rect = QRectF(
        0,
        rect.height() - handle_size,
        handle_size,
        handle_size
    )
    
    # Rysujemy trójkątny uchwyt
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(RESIZE_HANDLE_COLOR)
    
    path = QPainterPath()
    # Start at bottom-left corner (0, height)
    path.moveTo(0, rect.height())
    # Line to (handle_size, height)
    path.lineTo(handle_size, rect.height())
    # Line to (0, height - handle_size)
    path.lineTo(0, rect.height() - handle_size)
    # Close back to (0, height)
    path.closeSubpath()
    
    painter.fillPath(path, RESIZE_HANDLE_COLOR)
