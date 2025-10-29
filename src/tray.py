from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt
import sys
import os


class Tray:
    """
    Klasa odpowiedzialna za ikonę w zasobniku systemowym (tray)
    oraz szybki dostęp do funkcji overlaya.
    """

    def __init__(self, app, overlay):
        self.app = app
        self.overlay = overlay

        # Uzyskaj poprawną ścieżkę do zasobów (działa też po spakowaniu .exe)
        def resource_path(relative_path):
            """Zwraca poprawną ścieżkę do pliku zarówno w .exe, jak i w dev."""
            if hasattr(sys, '_MEIPASS'):
                return os.path.join(sys._MEIPASS, relative_path)
            return os.path.join(os.path.abspath("."), relative_path)

        icon_path = resource_path("images/ikona.ico")

        # Tworzymy ikonę tray
        self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self.app)
        self.tray_icon.setToolTip("Overlay")

        # Budujemy menu
        self.menu = QMenu()

        # Akcje menu
        self.toggle_action = QAction("Pokaż / Ukryj overlay")
        self.toggle_action.triggered.connect(self.toggle_overlay)
        self.menu.addAction(self.toggle_action)

        self.menu.addSeparator()

        # Clickthrough action z możliwością zaznaczenia
        self.clickthrough_action = QAction("Tryb kliknięć przez nakładkę", checkable=True)
        self.clickthrough_action.triggered.connect(self.toggle_clickthrough)
        self.menu.addAction(self.clickthrough_action)

        # Dragging action z możliwością zaznaczenia
        self.drag_action = QAction("Przenoszenie nakładki", checkable=True)
        self.drag_action.triggered.connect(self.toggle_drag)
        self.menu.addAction(self.drag_action)

        # Scaling action z możliwością zaznaczenia
        self.scaling_action = QAction("Skalowanie nakładki", checkable=True)
        self.scaling_action.triggered.connect(self.toggle_scaling)
        self.menu.addAction(self.scaling_action)

        self.menu.addSeparator()

        # Otwórz ustawienia
        self.settings_action = QAction("Otwórz ustawienia")
        self.settings_action.triggered.connect(self.open_settings)
        self.menu.addAction(self.settings_action)

        self.quit_action = QAction("Zakończ")
        self.quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()
        
        # Aktualizuj początkowy stan
        self.update_all_states()

    def toggle_overlay(self):
        """Pokazuje lub ukrywa overlay."""
        if not self.overlay:
            return

        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            self.overlay.show()
            self.overlay.raise_()

    def toggle_clickthrough(self):
        """Włącza/wyłącza tryb clickthrough."""
        if not self.overlay:
            return

        if self.overlay._clickthrough_enabled:
            self.overlay.disable_clickthrough()
        else:
            self.overlay.enable_clickthrough()
        
        # Aktualizuj stan zaznaczenia
        self.update_clickthrough_state()

    def toggle_drag(self):
        """Włącza/wyłącza możliwość przenoszenia."""
        if not self.overlay:
            return

        self.overlay.drag_enabled = self.drag_action.isChecked()
        if hasattr(self.overlay, 'settings_window') and self.overlay.settings_window:
            self.overlay.settings_window.drag_checkbox.setChecked(self.overlay.drag_enabled)
        self.overlay.save_settings()
        self.overlay.update_ui_states()
        
    def toggle_scaling(self):
        """Włącza/wyłącza możliwość skalowania."""
        if not self.overlay:
            return

        self.overlay.scaling_enabled = self.scaling_action.isChecked()
        if hasattr(self.overlay, 'settings_window') and self.overlay.settings_window:
            self.overlay.settings_window.scaling_checkbox.setChecked(self.overlay.scaling_enabled)
        self.overlay.save_settings()
        self.overlay.update_ui_states()
        self.overlay.update()

    def open_settings(self):
        """Otwiera okno ustawień."""
        if self.overlay and hasattr(self.overlay, 'settings_window'):
            self.overlay.settings_window.show()
            self.overlay.settings_window.raise_()

    def update_clickthrough_state(self):
        """Aktualizuje stan zaznaczenia clickthrough w menu tray"""
        if self.overlay and hasattr(self.overlay, '_clickthrough_enabled'):
            self.clickthrough_action.setChecked(self.overlay._clickthrough_enabled)

    def update_drag_state(self):
        """Aktualizuje stan zaznaczenia drag w menu tray"""
        if self.overlay and hasattr(self.overlay, 'drag_enabled'):
            self.drag_action.setChecked(self.overlay.drag_enabled)

    def update_scaling_state(self):
        """Aktualizuje stan zaznaczenia scaling w menu tray"""
        if self.overlay and hasattr(self.overlay, 'scaling_enabled'):
            self.scaling_action.setChecked(self.overlay.scaling_enabled)

    def update_all_states(self):
        """Aktualizuje wszystkie stany w menu tray"""
        self.update_clickthrough_state()
        self.update_drag_state()
        self.update_scaling_state()

    def set_overlay(self, new_overlay):
        """
        Ustawia nową referencję do overlaya — potrzebne po rekreacji overlaya
        (np. po zmianie przezroczystości).
        """
        self.overlay = new_overlay
        self.update_all_states()

    def quit_app(self):
        """Zamyka aplikację."""
        if self.overlay and hasattr(self.overlay, "cursor_timer"):
            if self.overlay.cursor_timer.isActive():
                self.overlay.cursor_timer.stop()

        self.tray_icon.hide()
        self.app.quit()
