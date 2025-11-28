"""
Toggle Button with rotation animation
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor
from PyQt6.QtCore import Qt, pyqtProperty


class ToggleButton(QWidget):
    """Custom toggle button with animated arrow rotation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._angle = 0  # Rotation angle
    
    def mousePressEvent(self, e):
        """Handle click event - delegate to parent's toggle_size method"""
        if hasattr(self.parent(), 'toggle_size'):
            self.parent().toggle_size()
    
    # Property for rotation animation
    def getAngle(self):
        return self._angle
    
    def setAngle(self, v):
        self._angle = v
        self.update()
    
    angle = pyqtProperty(float, getAngle, setAngle)
    
    def paintEvent(self, event):
        """Draw the arrow with rotation"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Rotate around center
        painter.translate(12, 12)
        painter.rotate(self._angle)
        painter.translate(-12, -12)
        
        # Draw arrow path (SVG: M6 15L12 9L18 15)
        path = QPainterPath()
        path.moveTo(6, 15)
        path.lineTo(12, 9)
        path.lineTo(18, 15)
        
        pen = QPen(QColor(255, 255, 255, 200))  # rgba(255,255,255, 0.8)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
