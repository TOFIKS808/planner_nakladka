"""
Moduł zarządzający ustawieniami overlay
"""
import json
import os
from PyQt6.QtCore import QTimer, QMutex


class SettingsManager:
    """Zarządza cache'owaniem i zapisem ustawień overlay"""
    
    def __init__(self, config_path):
        self.config_path = config_path
        self._settings_cache = {}
        self._settings_mutex = QMutex()
        self._save_pending = False
        
        # Timer do opóźnionego zapisu ustawień
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._delayed_save_settings)
    
    def load_settings(self):
        """Wczytuje ustawienia z pliku do cache"""
        try:
            if not os.path.exists(self.config_path):
                self._settings_cache = self._get_default_settings()
                return self._settings_cache.copy()
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            
            # Połącz załadowane dane z domyślnymi
            default_settings = self._get_default_settings()
            self._settings_cache = {**default_settings, **loaded_data}
            
            return self._settings_cache.copy()
            
        except Exception as e:
            print("Błąd podczas wczytywania ustawień:", e)
            self._settings_cache = self._get_default_settings()
            return self._settings_cache.copy()
    
    def _get_default_settings(self):
        """Zwraca domyślne ustawienia"""
        return {
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
    
    def get_current_settings(self):
        """Zwraca aktualne ustawienia z cache"""
        try:
            self._settings_mutex.lock()
            return self._settings_cache.copy()
        finally:
            self._settings_mutex.unlock()
    
    def get_group_settings(self):
        """Pobiera aktualne ustawienia grup z cache"""
        settings = self.get_current_settings()
        return {
            "group_c": settings.get("group_c"),
            "group_l": settings.get("group_l"),
            "group_k": settings.get("group_k")
        }
    
    def update_settings(self, new_settings):
        """Aktualizuje ustawienia w cache i planuje zapis do pliku"""
        try:
            self._settings_mutex.lock()
            
            # AKTUALIZUJ TYLKO PRZEKAZANE KLUCZE - nie usuwaj istniejących
            for key, value in new_settings.items():
                # ZACHOWAJ ISTNIEJĄCE WARTOŚCI GRUP JEŚLI NOWA WARTOŚĆ JEST None
                if key in ["group_c", "group_l", "group_k"] and value is None:
                    current_value = self._settings_cache.get(key)
                    if current_value is not None:
                        # Zachowaj istniejącą wartość, nie nadpisuj na None
                        continue
                
                # ZAPISZ WARTOŚĆ DLA WSZYSTKICH INNYCH PRZYPADKÓW
                self._settings_cache[key] = value
            
            # Użyj opóźnionego zapisu
            self.request_save_settings()
            
        except Exception as e:
            print("Błąd aktualizacji ustawień:", e)
        finally:
            self._settings_mutex.unlock()
    
    def update_group_settings(self, group_settings):
        """Aktualizuje ustawienia grup w cache"""
        self.update_settings(group_settings)
    
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
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._settings_cache, f, indent=4)
            
        except Exception as e:
            print("Błąd zapisu ustawień:", e)
        finally:
            self._settings_mutex.unlock()
    
    def save_settings(self):
        """Zachowaj kompatybilność - użyj opóźnionego zapisu"""
        self.request_save_settings()
    
    def save_settings_immediately(self):
        """Zapisuje ustawienia natychmiast (dla SettingsWindow)"""
        self._save_timer.stop()
        if self._save_pending:
            self._delayed_save_settings()
        else:
            self._save_settings_impl()
    
    def stop_timers(self):
        """Zatrzymuje wszystkie timery (przy zamykaniu aplikacji)"""
        self._save_timer.stop()
        if self._save_pending:
            self._delayed_save_settings()
