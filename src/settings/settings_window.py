import os
import json
import threading
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QCheckBox, QComboBox, QPushButton, QFileDialog, QMessageBox,
    QSizePolicy, QFrame, QApplication
)
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath

from src.settings.styles import (
    get_button_style, get_checkbox_style, get_slider_style
)
from src.settings.ui_components import FancyCloseButton


class SubgroupFetcher(QObject):
    fetched = pyqtSignal(str, dict)

    def fetch(self, group_c):
        def _run():
            try:
                import requests
                url = f"https://pk-timetable-scraper-api-orpin.vercel.app/api2/subgroups/{group_c}"
                res = requests.get(url, timeout=3)
                if res.status_code == 200:
                    self.fetched.emit(group_c, res.json())
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()


class SettingsWindow(QWidget):
    def __init__(self, overlay=None, parent=None, **kwargs):
        super().__init__(parent)
        self.overlay = overlay
        self.scaling_enabled = False
        self.hidden_subjects = []
        self._is_loading = True
        self._subgroups_cache = {}

        self.setWindowTitle("⚙️ Ustawienia nakładki")
        self.setFixedWidth(430)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        if os.name == "nt":
            base_dir = os.getenv("APPDATA")
            self.config_dir = os.path.join(base_dir, "OverlayApp")
        else:
            base_dir = os.path.expanduser("~/.config")
            self.config_dir = os.path.join(base_dir, "overlay")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, "settings.json")

        self.dragging = False
        self.drag_position = None

        self._fetcher = SubgroupFetcher()
        self._fetcher.fetched.connect(self._on_subgroups_fetched)

        self._build_ui()
        self.load_settings()
        self._is_loading = False

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── KONTENER Z ZAOKRĄGLONYMI ROGAMI I CIEMNYM TŁEM ──
        self.container = QWidget(self)
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QWidget#container {
                background-color: rgb(21, 26, 38);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # ── PASEK TYTUŁU ──
        title_bar = QWidget()
        title_bar.setFixedHeight(44)
        title_bar.setStyleSheet("""
            background-color: rgb(28, 34, 48);
            border-top-left-radius: 11px;
            border-top-right-radius: 11px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        """)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(18, 0, 12, 0)

        title_label = QLabel("⚙️ Ustawienia nakładki")
        title_label.setStyleSheet("""
            color: #f1f5f9;
            font-size: 14px;
            font-weight: bold;
            font-family: 'Segoe UI';
            background: transparent;
        """)
        tb_layout.addWidget(title_label)
        tb_layout.addStretch()

        self.close_button = FancyCloseButton()
        self.close_button.clicked.connect(self.close_settings)
        tb_layout.addWidget(self.close_button)

        container_layout.addWidget(title_bar)

        # ── ZAWARTOŚĆ OKNA ──
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 14, 20, 16)
        content_layout.setSpacing(11)

        # ── SEKCJA: WYGLĄD I ZACHOWANIE ──
        content_layout.addWidget(self._section_title("WYGLĄD I ZACHOWANIE"))

        # Przezroczystość
        opacity_row = QHBoxLayout()
        ol = QLabel("Przezroczystość nakładki:")
        ol.setStyleSheet("color: #e2e8f0; font-size: 13px; font-weight: 500; font-family: 'Segoe UI'; background: transparent;")
        self.opacity_value_label = QLabel("100%")
        self.opacity_value_label.setStyleSheet("color: #4ade80; font-size: 13px; font-weight: bold; font-family: 'Segoe UI'; background: transparent;")
        opacity_row.addWidget(ol)
        opacity_row.addStretch()
        opacity_row.addWidget(self.opacity_value_label)
        content_layout.addLayout(opacity_row)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.opacity_slider.sliderReleased.connect(self.save_opacity)
        self.opacity_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.opacity_slider.setStyleSheet(get_slider_style())
        content_layout.addWidget(self.opacity_slider)

        # Checkboxy
        self.scaling_checkbox = QCheckBox("Włącz skalowanie nakładki (przeciągnij za róg)")
        self.scaling_checkbox.setStyleSheet(get_checkbox_style())
        self.scaling_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scaling_checkbox.stateChanged.connect(self.on_scaling_change)
        content_layout.addWidget(self.scaling_checkbox)

        self.clickthrough_checkbox = QCheckBox("Pozwól klikać przez nakładkę")
        self.clickthrough_checkbox.setStyleSheet(get_checkbox_style())
        self.clickthrough_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clickthrough_checkbox.stateChanged.connect(self.on_clickthrough_change)
        content_layout.addWidget(self.clickthrough_checkbox)

        self.drag_checkbox = QCheckBox("Pozwól przenosić nakładkę")
        self.drag_checkbox.setStyleSheet(get_checkbox_style())
        self.drag_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drag_checkbox.stateChanged.connect(self.on_drag_change)
        content_layout.addWidget(self.drag_checkbox)

        content_layout.addWidget(self._thin_line())

        # ── SEKCJA: GRUPY ZAJĘCIOWE ──
        content_layout.addWidget(self._section_title("GRUPY ZAJĘCIOWE"))

        all_groups = [
            "11A1","11A2","11A3","11B1","11I1","11I2","11K1","11K2",
            "11L1","11L2","11M1","11M2","11M3","11S1","11S2","11T1","11T2","11W1",
            "12A1","12A2","12A3","12B1","12I1","12K1","12K2",
            "12L1","12L2","12M1","12M2","12S1","12S2","12T1","12W1",
            "13A4","13A6","13B1","13I4","13I7","13K1","13K2",
            "13L3","13L4","13M4","13M5","13S1","13S3","13T4","13T8","13W1",
            "14A3","14A4","14A6","14B1","14I4","14I6","14K1","14K2","14K3",
            "14L3","14L4","14M4","14M5","14S1","14S2","14T4","14T8","14W1",
            "41A4","41A6","41I1","41I2","41K8","41L3","41L4","41M4","41M5","41S2","41T4"
        ]

        combo_style = """
            QComboBox {
                background: rgb(28, 34, 48);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-family: 'Segoe UI';
                min-height: 22px;
            }
            QComboBox:hover {
                border-color: #4ade80;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid rgba(255, 255, 255, 140);
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: rgb(21, 26, 38);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.2);
                selection-background-color: #16a34a;
                selection-color: white;
                outline: none;
                padding: 4px;
            }
        """

        default_labs = ["L01","L02","L03","L04","L05","L06","L07", "GL01","GL02","GL03","GL04","GL05","GL06","GL07"]
        default_klabs = ["K01","K02","K03","K04","K05","K06", "GK/P01","GK/P02","GK/P03","GK/P04","GK/P05","GK/P06"]

        self.group_c = self._labeled_combo("Kierunek / Grupa główna", all_groups, content_layout, combo_style)
        self.group_l = self._labeled_combo("Grupa Laboratoryjna (Lab)", default_labs, content_layout, combo_style)
        self.group_k = self._labeled_combo("Grupa Projektowa (Proj)", default_klabs, content_layout, combo_style)

        content_layout.addWidget(self._thin_line())

        # ── SEKCJA: SYNCHRONIZACJA Z WWW ──
        content_layout.addWidget(self._section_title("SYNCHRONIZACJA Z WWW"))

        self.sync_info_label = QLabel("Ukryte przedmioty z WWW: 0")
        self.sync_info_label.setStyleSheet("color: #4ade80; font-size: 13px; font-weight: 600; font-family: 'Segoe UI'; background: transparent;")
        content_layout.addWidget(self.sync_info_label)

        sync_btn_layout = QHBoxLayout()
        sync_btn_layout.setSpacing(8)

        sync_btn_style_p = """
            QPushButton {
                background: rgba(34, 197, 94, 0.22);
                color: #86efac;
                border: 1px solid rgba(74, 222, 128, 0.55);
                padding: 6px 8px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background: rgba(34, 197, 94, 0.38); border-color: rgba(74, 222, 128, 0.9); color: #fff; }
        """
        sync_btn_style_d = """
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.16);
                padding: 6px 8px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.12); border-color: rgba(255, 255, 255, 0.3); color: #fff; }
        """
        import_clip_btn = QPushButton("📋 Schowek")
        import_clip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_clip_btn.clicked.connect(self.import_from_clipboard)
        import_clip_btn.setStyleSheet(sync_btn_style_p)
        sync_btn_layout.addWidget(import_clip_btn)

        import_file_btn = QPushButton("📁 Plik...")
        import_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_file_btn.clicked.connect(self.import_from_file)
        import_file_btn.setStyleSheet(sync_btn_style_d)
        sync_btn_layout.addWidget(import_file_btn)

        clear_btn = QPushButton("🗑️ Wyczyść")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self.clear_hidden_subjects)
        clear_btn.setStyleSheet(sync_btn_style_d)
        sync_btn_layout.addWidget(clear_btn)

        content_layout.addLayout(sync_btn_layout)

        content_layout.addWidget(self._thin_line())

        # ── PRZYCISKI GŁÓWNE ──
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        save_btn = QPushButton("💾 Zapisz ustawienia")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(lambda: self.save_settings(force=True))
        save_btn.setStyleSheet(get_button_style("primary"))
        btn_layout.addWidget(save_btn)

        close_app_btn = QPushButton("❌ Zamknij program")
        close_app_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_app_btn.clicked.connect(self.confirm_close_app)
        close_app_btn.setStyleSheet(get_button_style("danger"))
        btn_layout.addWidget(close_app_btn)

        content_layout.addLayout(btn_layout)

        container_layout.addWidget(content_widget)
        main_layout.addWidget(self.container)

    # ── Helpery UI ──
    def _section_title(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: rgba(220, 225, 240, 0.6); font-size: 11px; font-weight: 700; letter-spacing: 1.2px; font-family: 'Segoe UI'; padding: 2px 0px; background: transparent;")
        return lbl

    def _thin_line(self):
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255, 255, 255, 0.08);")
        line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return line

    def _labeled_combo(self, label_text, items, parent_layout, style):
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #f1f5f9; font-size: 12px; font-weight: 600; font-family: 'Segoe UI'; padding: 0; margin: 0; background: transparent;")
        parent_layout.addWidget(lbl)
        combo = QComboBox()
        combo.addItems(["—"] + items)
        combo.setStyleSheet(style)
        combo.setCursor(Qt.CursorShape.PointingHandCursor)
        combo.currentTextChanged.connect(self._on_combo_text_changed)
        parent_layout.addWidget(combo)
        return combo

    # ── Drag ──
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and self.drag_position:
            delta = event.globalPosition().toPoint() - self.drag_position
            self.move(self.pos() + delta)
            self.drag_position = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.drag_position = None
            event.accept()

    # ── Callbacki ──
    def _on_opacity_changed(self, value):
        self.opacity_value_label.setText(f"{value}%")
        self.preview_opacity(value)

    def preview_opacity(self, value):
        if self.overlay:
            try:
                self.overlay.setWindowOpacity(value / 100.0)
            except Exception as e:
                print("Błąd przy zmianie przezroczystości:", e)

    def save_opacity(self):
        if not self._is_loading:
            self.save_settings()

    def _on_combo_text_changed(self, text):
        if self._is_loading:
            return
        self.on_group_changed(None)

    def on_group_changed(self, button):
        if self._is_loading:
            return
        self.update_subgroups()
        self.save_settings()

    def update_subgroups(self):
        group_c = self.get_checked_label(self.group_c)
        if not group_c:
            return
        
        if group_c in self._subgroups_cache:
            self._apply_subgroups_data(self._subgroups_cache[group_c])
            return

        self._fetcher.fetch(group_c)

    def _on_subgroups_fetched(self, group_c, data):
        self._subgroups_cache[group_c] = data
        current_selected_group = self.get_checked_label(self.group_c)
        if current_selected_group == group_c:
            self._apply_subgroups_data(data)

    def _apply_subgroups_data(self, data):
        curr_l = self.get_checked_label(self.group_l)
        curr_k = self.get_checked_label(self.group_k)

        self.group_l.blockSignals(True)
        existing_l = [self.group_l.itemText(i) for i in range(self.group_l.count()) if self.group_l.itemText(i) != "—"]
        combined_l = list(dict.fromkeys(existing_l + data.get("labs", [])))
        self.group_l.clear()
        self.group_l.addItems(["—"] + combined_l)
        self.set_checked_label(self.group_l, curr_l)
        self.group_l.blockSignals(False)

        self.group_k.blockSignals(True)
        existing_k = [self.group_k.itemText(i) for i in range(self.group_k.count()) if self.group_k.itemText(i) != "—"]
        combined_k = list(dict.fromkeys(existing_k + data.get("klabs", [])))
        self.group_k.clear()
        self.group_k.addItems(["—"] + combined_k)
        self.set_checked_label(self.group_k, curr_k)
        self.group_k.blockSignals(False)

    def on_scaling_change(self, state):
        if self._is_loading:
            return
        if self.overlay:
            self.overlay.scaling_enabled = self.scaling_checkbox.isChecked()
            self.overlay.update()
            self.save_settings()

    def on_clickthrough_change(self, state):
        if self._is_loading:
            return
        if self.overlay:
            if self.clickthrough_checkbox.isChecked():
                self.overlay.enable_clickthrough()
            else:
                self.overlay.disable_clickthrough()
            self.save_settings()

    def on_drag_change(self, state):
        if self._is_loading:
            return
        if self.overlay:
            self.overlay.drag_enabled = self.drag_checkbox.isChecked()
            self.save_settings()

    # ── Import z WWW ──
    def import_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if not text:
            QMessageBox.warning(self, "Pusty schowek", "Schowek jest pusty. Kliknij 'Kopiuj konfigurację dla Nakładki' na stronie WWW.")
            return
        self._apply_imported_config(text)

    def import_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik konfiguracji",
            "",
            "Pliki JSON (*.json);;Wszystkie pliki (*.*)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self._apply_imported_config(content)
        except Exception as e:
            QMessageBox.critical(self, "Błąd odczytu", f"Nie udało się odczytać pliku: {e}")

    def clear_hidden_subjects(self):
        reply = QMessageBox.question(
            self,
            "Wyczyść ukryte przedmioty",
            "Czy na pewno chcesz przywrócić wszystkie ukryte przedmioty?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.hidden_subjects = []
            if hasattr(self, "sync_info_label"):
                self.sync_info_label.setText("Ukryte przedmioty z WWW: 0")
            self.save_settings(force=True, force_clear_hidden=True)
            if self.overlay and hasattr(self.overlay, "update_manager"):
                self.overlay.update_manager.timetable_cache = None
                self.overlay.update_manager.trigger_update()
            QMessageBox.information(self, "Wyczyszczono", "Przywrócono wszystkie ukryte przedmioty.")

    def _apply_imported_config(self, raw_json):
        try:
            data = json.loads(raw_json)
        except Exception as e:
            QMessageBox.critical(self, "Błąd formatu", f"Dane nie są poprawnym formatem JSON: {e}")
            return

        applied = []
        group_c = data.get("group_c")
        if group_c:
            self.set_checked_label(self.group_c, group_c)
            applied.append(f"Grupa główna: {group_c}")
            self.update_subgroups()

        subgroups = data.get("subgroups", [])
        hidden = data.get("hidden_subjects", [])

        if subgroups:
            for sg in subgroups:
                if sg.startswith("GL") or sg.startswith("L"):
                    self.set_checked_label(self.group_l, sg)
                    applied.append(f"Lab: {sg}")
                elif sg.startswith("GK") or sg.startswith("K"):
                    self.set_checked_label(self.group_k, sg)
                    applied.append(f"Proj: {sg}")
                else:
                    matched_l = -1
                    for i in range(self.group_l.count()):
                        t = self.group_l.itemText(i)
                        if t == sg:
                            matched_l = i
                            break
                        elif matched_l == -1 and t != "—" and (t.endswith(sg) or sg.endswith(t)):
                            matched_l = i
                    if matched_l >= 0:
                        self.group_l.setCurrentIndex(matched_l)
                        applied.append(f"Lab: {self.group_l.itemText(matched_l)}")

                    matched_k = -1
                    for i in range(self.group_k.count()):
                        t = self.group_k.itemText(i)
                        if t == sg:
                            matched_k = i
                            break
                        elif matched_k == -1 and t != "—" and (t.endswith(sg) or sg.endswith(t)):
                            matched_k = i
                    if matched_k >= 0:
                        self.group_k.setCurrentIndex(matched_k)
                        applied.append(f"Proj: {self.group_k.itemText(matched_k)}")

        if isinstance(hidden, list):
            self.hidden_subjects = list(hidden)
            if hasattr(self, "sync_info_label"):
                self.sync_info_label.setText(f"Ukryte przedmioty z WWW: {len(self.hidden_subjects)}")
            applied.append(f"Ukryte przedmioty: {len(self.hidden_subjects)}")

        # Natychmiast zapisz na dysk i w cache wymuszając zapis!
        self.save_settings(force=True, force_clear_hidden=(len(self.hidden_subjects) == 0))

        if self.overlay and hasattr(self.overlay, "update_manager"):
            self.overlay.update_manager.timetable_cache = None
            self.overlay.update_manager.trigger_update()

        msg = "Pomyślnie zaimportowano i trwale zapisano ustawienia!\n\n" + "\n".join(applied)
        QMessageBox.information(self, "Import zakończony", msg)

    # ── Ustawienia ──
    def load_settings(self):
        self._is_loading = True
        try:
            # 1. Zawsze wczytuj z pliku na dysku jako źródła prawdy
            file_data = {}
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                except Exception:
                    file_data = {}

            if self.overlay:
                overlay_data = self.overlay.get_current_settings()
                data = {**overlay_data, **file_data}
            else:
                data = file_data

            # Wczytaj ukryte przedmioty JAKO PIERWSZE!
            loaded_hidden = data.get("hidden_subjects", [])
            if loaded_hidden:
                self.hidden_subjects = list(loaded_hidden)
            elif not hasattr(self, "hidden_subjects") or not self.hidden_subjects:
                self.hidden_subjects = list(loaded_hidden)

            if hasattr(self, "sync_info_label"):
                self.sync_info_label.setText(f"Ukryte przedmioty z WWW: {len(self.hidden_subjects)}")

            # Zablokuj sygnały na WSZYSTKICH kontrolkach podczas ładowania
            self.opacity_slider.blockSignals(True)
            self.clickthrough_checkbox.blockSignals(True)
            self.drag_checkbox.blockSignals(True)
            self.scaling_checkbox.blockSignals(True)
            self.group_c.blockSignals(True)
            self.group_l.blockSignals(True)
            self.group_k.blockSignals(True)

            self.opacity_slider.setValue(int(data.get("opacity", 1.0) * 100))
            self.opacity_value_label.setText(f"{int(data.get('opacity', 1.0) * 100)}%")
            self.clickthrough_checkbox.setChecked(data.get("clickthrough", True))
            self.drag_checkbox.setChecked(data.get("drag_enabled", True))
            self.scaling_checkbox.setChecked(data.get("scaling_enabled", False))

            self.set_checked_label(self.group_c, data.get("group_c"))
            self.set_checked_label(self.group_l, data.get("group_l"))
            self.set_checked_label(self.group_k, data.get("group_k"))
        except Exception as e:
            print(f"Błąd wczytywania ustawień: {e}")
        finally:
            self.opacity_slider.blockSignals(False)
            self.clickthrough_checkbox.blockSignals(False)
            self.drag_checkbox.blockSignals(False)
            self.scaling_checkbox.blockSignals(False)
            self.group_c.blockSignals(False)
            self.group_l.blockSignals(False)
            self.group_k.blockSignals(False)
            self._is_loading = False

    def set_checked_label(self, combo, label):
        if label:
            idx = combo.findText(label)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.addItem(label)
                combo.setCurrentIndex(combo.count() - 1)
        else:
            combo.setCurrentIndex(0)

    def get_checked_label(self, combo):
        val = combo.currentText()
        return val if val != "—" else None

    def save_settings(self, force=False, force_clear_hidden=False):
        if self._is_loading and not force:
            return
        try:
            disk_data = {}
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        disk_data = json.load(f)
                except Exception:
                    disk_data = {}

            # Ochrona przed skasowaniem ukrytych przedmiotów
            current_hidden = getattr(self, "hidden_subjects", [])
            if not current_hidden and not force_clear_hidden:
                disk_hidden = disk_data.get("hidden_subjects", [])
                if disk_hidden:
                    self.hidden_subjects = list(disk_hidden)
                    current_hidden = self.hidden_subjects

            s = {
                "opacity": round(self.opacity_slider.value() / 100.0, 2),
                "clickthrough": self.clickthrough_checkbox.isChecked(),
                "drag_enabled": self.drag_checkbox.isChecked(),
                "scaling_enabled": self.scaling_checkbox.isChecked(),
                "hidden_subjects": current_hidden
            }
            if force_clear_hidden:
                s["force_clear_hidden"] = True

            for key, combo in [("group_c", self.group_c), ("group_l", self.group_l), ("group_k", self.group_k)]:
                val = self.get_checked_label(combo)
                if val is not None:
                    s[key] = val

            # Trwały zapis NATYCHMIAST do pliku settings.json na dysku
            disk_data.update({k: v for k, v in s.items() if k != "force_clear_hidden"})
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(disk_data, f, indent=4)

            # Zsynchronizuj z overlay jeśli dostępny
            if self.overlay:
                self.overlay.update_settings(s)
                if hasattr(self.overlay.settings_manager, "save_settings_immediately"):
                    self.overlay.settings_manager.save_settings_immediately()
        except Exception as e:
            print(f"Błąd zapisywania ustawień: {e}")

    def confirm_close_app(self):
        reply = QMessageBox.question(self, "Zamknij program", "Czy na pewno chcesz zamknąć program?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.save_settings(force=True)
            if self.overlay:
                if hasattr(self.overlay, "close"): self.overlay.close()
                elif hasattr(self.overlay, "quit"): self.overlay.quit()
                self.close()

    def close_settings(self):
        self.hide()
        if self.overlay and hasattr(self.overlay, "_clickthrough_enabled") and self.overlay._clickthrough_enabled:
            self.overlay.enable_clickthrough()

    def showEvent(self, event):
        self.load_settings()
        self.adjustSize()
        super().showEvent(event)

    def closeEvent(self, event):
        self.close_settings()
        event.accept()
