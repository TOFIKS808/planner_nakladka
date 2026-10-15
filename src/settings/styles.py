"""
Style CSS dla elementów UI okna ustawień (Zielony / Szmaragdowy motyw nakładki)
"""

def get_slider_style():
    return """
        QSlider {
            background: transparent;
        }
        QSlider::groove:horizontal {
            border: none;
            height: 4px;
            background: rgba(255, 255, 255, 20);
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #4ade80;
            border: 2px solid #22c55e;
            width: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }
        QSlider::handle:horizontal:hover {
            background: #86efac;
            border-color: #4ade80;
        }
        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #16a34a, stop:1 #4ade80);
            border-radius: 2px;
        }
    """

def get_checkbox_style():
    return """
        QCheckBox {
            spacing: 12px;
            color: #d1d5db;
            font-size: 14px;
            font-family: 'Segoe UI';
            background: transparent;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 40);
            background: rgba(30, 36, 50, 150);
        }
        QCheckBox::indicator:hover {
            border-color: rgba(74, 222, 128, 180);
            background: rgba(40, 48, 65, 150);
        }
        QCheckBox::indicator:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #16a34a, stop:1 #4ade80);
            border-color: #22c55e;
        }
    """

def get_button_style(color_type="primary"):
    if color_type == "primary" or color_type == "green":
        bg = "rgba(34, 197, 94, 0.22)"
        bg_hover = "rgba(34, 197, 94, 0.38)"
        border = "rgba(74, 222, 128, 0.55)"
        border_hover = "rgba(74, 222, 128, 0.9)"
        text_color = "#86efac"
    elif color_type == "danger" or color_type == "red":
        bg = "rgba(160, 45, 45, 130)"
        bg_hover = "rgba(200, 60, 60, 190)"
        border = "rgba(255, 100, 100, 120)"
        border_hover = "rgba(255, 150, 150, 180)"
        text_color = "#fecdd3"
    else:  # neutral / default
        bg = "rgba(255, 255, 255, 0.06)"
        bg_hover = "rgba(255, 255, 255, 0.12)"
        border = "rgba(255, 255, 255, 0.16)"
        border_hover = "rgba(255, 255, 255, 0.3)"
        text_color = "#e2e8f0"
    
    return f"""
        QPushButton {{
            background: {bg};
            color: {text_color};
            border: 1px solid {border};
            padding: 8px 20px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 14px;
            font-family: 'Segoe UI';
        }}
        QPushButton:hover {{
            background: {bg_hover};
            border-color: {border_hover};
            color: #ffffff;
        }}
        QPushButton:pressed {{
            background: rgba(0, 0, 0, 120);
        }}
    """

def get_radio_button_style():
    return ""
