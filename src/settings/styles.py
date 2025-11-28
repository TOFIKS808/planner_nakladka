"""
Style CSS dla elementów UI okna ustawień
"""


def get_slider_style():
    """Zwraca styl CSS dla suwaków"""
    return """
        QSlider::groove:horizontal {
            border: none;
            height: 6px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #3a4a5a, stop:1 #2a3a4a);
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #5a9fd4, stop:1 #4080c0);
            border: 1px solid #2060a0;
            width: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }
        QSlider::handle:horizontal:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6ab0e4, stop:1 #5090d0);
        }
        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4a90d9, stop:1 #67e6dc);
            border-radius: 3px;
        }
    """


def get_checkbox_style():
    """Zwraca styl CSS dla checkboxów"""
    return """
        QCheckBox {
            spacing: 8px;
            color: #e0e8f0;
            font-size: 13px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 2px solid #4a5a6a;
            background: #2a3a4a;
        }
        QCheckBox::indicator:hover {
            border-color: #5a9fd4;
            background: #3a4a5a;
        }
        QCheckBox::indicator:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #4a90d9, stop:1 #67e6dc);
            border-color: #4a90d9;
        }
        QCheckBox::indicator:checked:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #5aa0e9, stop:1 #77f6ec);
        }
    """


def get_button_style(color_type="primary"):
    """
    Zwraca styl CSS dla przycisków
    
    Args:
        color_type: "primary", "danger", lub "secondary"
    """
    if color_type == "primary":
        base_color = "#4a90d9"
        hover_color = "#5aa0e9"
        pressed_color = "#3a80c9"
    elif color_type == "danger":
        base_color = "#d94a4a"
        hover_color = "#e95a5a"
        pressed_color = "#c93a3a"
    else:  # secondary
        base_color = "#5a6a7a"
        hover_color = "#6a7a8a"
        pressed_color = "#4a5a6a"
    
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {base_color}, stop:1 {pressed_color});
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {hover_color}, stop:1 {base_color});
        }}
        QPushButton:pressed {{
            background: {pressed_color};
        }}
    """


def get_radio_button_style():
    """Zwraca styl CSS dla przycisków radiowych"""
    return """
        QRadioButton {
            spacing: 6px;
            color: #e0e8f0;
            font-size: 12px;
            padding: 4px;
        }
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 2px solid #4a5a6a;
            background: #2a3a4a;
        }
        QRadioButton::indicator:hover {
            border-color: #5a9fd4;
            background: #3a4a5a;
        }
        QRadioButton::indicator:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #4a90d9, stop:1 #67e6dc);
            border-color: #4a90d9;
        }
        QRadioButton::indicator:checked:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #5aa0e9, stop:1 #77f6ec);
        }
    """
