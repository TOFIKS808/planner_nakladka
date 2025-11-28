"""
Moduł zarządzający aktualizacjami danych z API
"""
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject
from datetime import datetime
from src import api


import multiprocessing
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from datetime import datetime
from src import api
from src.fetcher import run_fetch_process

class UpdateManager(QObject):
    """Zarządza okresowymi aktualizacjami danych z API"""
    
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self._api_update_in_progress = False
        
        # Caching
        self.timetable_cache = None
        self.last_fetch_time = 0
        self.CACHE_DURATION = 60  # 1 minute for testing
        
        # Multiprocessing
        self.queue = multiprocessing.Queue()
        self.check_queue_timer = QTimer(self.widget)
        self.check_queue_timer.timeout.connect(self.check_queue)
        
        # Timery dla aktualizacji
        self.update_timer = QTimer(self.widget)
        self.update_timer.timeout.connect(self.trigger_update)
        
        self.progress_timer = QTimer(self.widget)
        self.progress_timer.timeout.connect(self.fast_progress_update)
        
        # Dane lekcji
        self.currentLesson = None
        self.nextLesson = None
    
    def start_updates(self):
        """Rozpoczyna okresowe aktualizacje"""
        # Timer dla aktualizacji danych co 30 sekund
        self.update_timer.start(30000)
        
        # Timer dla płynnego odświeżania progress bara co 10 sekund
        self.progress_timer.start(10000)
        
        # Sprawdź czy grupy są ustawione przed pierwszą aktualizacją
        if not self.are_groups_set():
            self.widget.title = "Ustaw grupy w opcjach"
            self.widget.left_text = "Kliknij prawym przyciskiem"
            self.widget.right_text = "na ikonę w tray"
            self.widget.room_text = "-"
            self.widget.setProgress(0.0)
            return
        
        # Od razu wykonaj pierwszą aktualizację
        self.trigger_update()
    
    def are_groups_set(self):
        """Sprawdza czy wszystkie wymagane grupy są ustawione"""
        settings = self.widget.settings_manager.get_current_settings()
        group_c = settings.get("group_c")
        group_l = settings.get("group_l")
        group_k = settings.get("group_k")
        
        return group_c is not None and group_l is not None and group_k is not None
    
    def trigger_update(self):
        """Inicjuje proces aktualizacji (z cache lub API)"""
        if self._api_update_in_progress:
            return
        
        self._api_update_in_progress = True
        
        # SPRAWDŹ CZY GRUPY SĄ USTAWIONE
        if not self.are_groups_set():
            self.widget.title = "Ustaw grupy w opcjach"
            self.widget.left_text = "Kliknij prawym przyciskiem"
            self.widget.right_text = "na ikonę w tray"
            self.widget.room_text = "-"
            self.widget.setProgress(0.0)
            self.widget.update_text_labels()
            self._api_update_in_progress = False
            return
        
        # Sprawdź cache
        import time
        current_time = time.time()
        
        if self.timetable_cache and (current_time - self.last_fetch_time < self.CACHE_DURATION):
            # Użyj danych z cache
            self.process_timetable(self.timetable_cache)
            self._api_update_in_progress = False
        else:
            # Uruchom osobny proces
            settings = self.widget.settings_manager.get_current_settings()
            p = multiprocessing.Process(target=run_fetch_process, args=(settings, self.queue))
            p.start()
            # Uruchom timer sprawdzający kolejkę
            self.check_queue_timer.start(100)

    def check_queue(self):
        """Sprawdza czy są dane w kolejce"""
        if not self.queue.empty():
            timetable = self.queue.get()
            self.check_queue_timer.stop()
            self.handle_fetch_result(timetable)

    def handle_fetch_result(self, timetable):
        """Odbiera dane z procesu i aktualizuje UI"""
        try:
            if timetable is None:
                if self.timetable_cache:
                    print("Warning: Fetch failed, using stale cache.")
                    self.process_timetable(self.timetable_cache)
                else:
                    raise Exception("Failed to fetch timetable data and no cache available.")
            else:
                # Zaktualizuj cache
                import time
                self.timetable_cache = timetable
                self.last_fetch_time = time.time()
                self.process_timetable(timetable)
            
        except Exception as e:
            print("Błąd podczas aktualizacji danych UI:", e)
            self._set_error_state()
        finally:
            self._api_update_in_progress = False

    def process_timetable(self, timetable):
        """Przetwarza dane planu i aktualizuje UI"""
        # Pobierz aktualną lekcję
        currentLesson = api.get_current_segment(timetable)
        if not currentLesson or not isinstance(currentLesson, dict):
            currentLesson = {
                "syllabus": "Brak zajęć",
                "remaining_time": 0,
                "total_duration": 0,
                "is_break": False,
                "time_elapsed": 0,
                "start": "00:00",
                "end": "00:00"
            }
        
        # Pobierz następną lekcję
        nextLesson = api.get_next_segment(timetable)
        if not nextLesson or not isinstance(nextLesson, dict):
            nextLesson = {
                "syllabus": "Brak dalszych zajęć",
                "hall": "-",
            }
        
        self.widget.title = currentLesson.get("syllabus", "Brak zajęć")
        
        # Update room text
        current_hall = currentLesson.get("hall", "-")
        self.widget.room_text = current_hall if current_hall else "-"
        
        # ZAPISZ DANE JAKO ATRYBUTY DLA SZYBKIEGO ODŚWIEŻANIA
        self.currentLesson = currentLesson
        self.nextLesson = nextLesson
        
        # Zaktualizuj progress bar od razu
        self.update_progress()

    def _set_error_state(self):
        """Ustawia UI w stan błędu"""
        self.currentLesson = {
            "syllabus": "Błąd ładowania",
            "remaining_time": 0,
            "total_duration": 0,
            "is_break": False,
            "time_elapsed": 0,
            "start": "00:00",
            "end": "00:00"
        }
        self.nextLesson = {
            "syllabus": "Brak danych",
            "hall": "-",
        }
        self.widget.title = "Błąd ładowania"
        self.widget.room_text = "-"
        self.widget.setProgress(0.0)
        self.widget.update_text_labels()
    
    def fast_progress_update(self):
        """Szybka aktualizacja tylko progress bara"""
        if self.currentLesson is not None and not self._api_update_in_progress:
            self.update_progress()
    
    def update_progress(self):
        """Aktualizuje progress bar - teraz proste obliczenia"""
        if self.currentLesson is None:
            return
        
        try:
            # Pobierz czasy z aktualnej lekcji
            if self.currentLesson.get("id") == -1:
                start_time_str = self.currentLesson.get("exactStart")
                end_time_str = self.currentLesson.get("exactEnd")
            else:
                start_time_str = self.currentLesson.get("start")
                end_time_str = self.currentLesson.get("end")
            
            if not start_time_str or not end_time_str:
                self.widget.setProgress(0.0)
                return
            
            if end_time_str == "00:00":
                end_time_str = self.nextLesson.get("start", "00:00")
            
            # Pobierz aktualną datę
            today = datetime.now().date()
            
            # Połącz aktualną datę z czasem rozpoczęcia i zakończenia
            start_datetime = datetime.combine(today, datetime.strptime(start_time_str, '%H:%M').time())
            end_datetime = datetime.combine(today, datetime.strptime(end_time_str, '%H:%M').time())
            
            current_time = datetime.now()
            
            # Jeśli lekcja kończy się po północy, dodaj jeden dzień do czasu zakończenia
            if end_datetime < start_datetime:
                end_datetime = end_datetime.replace(day=end_datetime.day + 1)
            
            # Oblicz całkowity czas trwania i czas pozostały
            total_duration = (end_datetime - start_datetime).total_seconds() / 60  # w minutach
            elapsed_time = (current_time - start_datetime).total_seconds() / 60  # w minutach
            remaining_time = (end_datetime - current_time).total_seconds() / 60  # w minutach
            
            self.widget.left_text = f"{round(remaining_time)}min → {self.nextLesson.get('syllabus', '-')}"
            # Jeśli sala jest pusta (np. dla przerwy), wyświetl "-"
            hall = self.nextLesson.get("hall", "")
            self.widget.right_text = hall if hall else "-"
            
            # Oblicz postęp (0.0 - 1.0)
            if total_duration > 0:
                progress = min(max(elapsed_time / total_duration, 0.0), 1.0)
            else:
                progress = 0.0
            
            self.widget.setProgress(progress)
            self.widget.update_text_labels()  # Sync QLabel widgets after updating left_text and right_text
            
        except Exception as e:
            print(f"Błąd podczas aktualizacji postępu: {e}")
            self.widget.setProgress(0.0)
    
    def stop_timers(self):
        """Zatrzymuje wszystkie timery i wątki (przy zamykaniu aplikacji)"""
        if self.update_timer.isActive():
            self.update_timer.stop()
        if self.progress_timer.isActive():
            self.progress_timer.stop()
        if self.check_queue_timer.isActive():
            self.check_queue_timer.stop()
