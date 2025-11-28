"""
Komponenty UI dla okna ustawień
"""
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QLinearGradient, QColor


class FancyCloseButton(QPushButton):
    """Niestandardowy przycisk zamykania z animacją"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.setText("×")
        self._opacity = 1.0
        
        # Animacja
        self.anim = QPropertyAnimation(self, b"opacity")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def get_opacity(self):
        return self._opacity

    def set_opacity(self, value):
        self._opacity = value
        self.update()

    opacity = pyqtProperty(float, get_opacity, set_opacity)

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._opacity)
        self.anim.setEndValue(0.7)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._opacity)
        self.anim.setEndValue(1.0)
        self.anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Gradient tła
        gradient = QLinearGradient(0, 0, 0, self.height())
        base_color = QColor(220, 80, 80)
        
        if self.underMouse():
            gradient.setColorAt(0, base_color.lighter(110))
            gradient.setColorAt(1, base_color)
        else:
            gradient.setColorAt(0, base_color)
            gradient.setColorAt(1, base_color.darker(110))
        
        painter.setBrush(gradient)
        painter.setPen(QColor(0, 0, 0, 0))
        painter.drawRoundedRect(self.rect(), 4, 4)
        
        # Tekst
        painter.setPen(QColor(255, 255, 255, int(255 * self._opacity)))
        painter.setFont(self.font())
        painter.drawText(self.rect(), 0x84, self.text())  # Qt.AlignmentFlag.AlignCenter
