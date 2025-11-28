import multiprocessing
import psutil
import os
import sys

def run_fetch_process(settings, queue):
    """
    Funkcja uruchamiana w osobnym procesie.
    Ustawia niski priorytet i pobiera dane.
    NIE IMPORTUJE PYQT!
    """
    try:
        # Ustaw najniższy priorytet dla tego procesu
        p = psutil.Process(os.getpid())
        # Windows: IDLE_PRIORITY_CLASS, Linux: nice value
        if os.name == 'nt':
            p.nice(psutil.IDLE_PRIORITY_CLASS)
        else:
            p.nice(19)
            
        # Import tutaj, aby uniknąć problemów z cyklicznym importem
        # i upewnić się, że api jest ładowane w procesie potomnym
        from src import api
        
        # Pobierz dane
        timetable = api.fetch_timetable(settings)
        queue.put(timetable)
    except Exception as e:
        print(f"Process error: {e}")
        queue.put(None)
