import requests
import os
import json
from datetime import datetime

# Global session for connection pooling
session = requests.Session()

def fetch_timetable(settings=None):
    try:
        if settings is None:
            settings = load_settings()
        
        # Pobierz grupy z ustawień, używając .get() dla bezpieczeństwa
        group_c_val = settings.get("group_c")
        group_l_val = settings.get("group_l")
        group_k_val = settings.get("group_k")

        # Sprawdź czy grupy są ustawione (nie None)
        if not group_c_val or not group_l_val or not group_k_val:
            # print("Brak ustawionych grup") # Debug
            return None

        # Pobierz ostatni znak (zakładając format np. "11K1" -> "1")
        try:
            group_c = group_c_val[-1]
            group_k = group_k_val[-1]
            group_l = group_l_val[-1]
        except IndexError:
            print("Błąd formatu grupy")
            return None
        
        # Use the global session
        response = session.get()
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching timetable data: {e}")
        return None

def get_current_segment(timetable=None):
    if timetable is None:
        timetable = fetch_timetable()

    if timetable:
        for lesson in timetable:
            start_time = datetime.strptime(lesson['start'], "%H:%M").time()
            end_time = datetime.strptime(lesson['end'], "%H:%M").time()
            now = datetime.now().time()
            if start_time <= now <= end_time:
                return lesson

def get_next_segment(timetable=None):
    if timetable is None:
        timetable = fetch_timetable()

    if timetable:
        now = datetime.now().time()
        for lesson in timetable:
            start_time = datetime.strptime(lesson['start'], "%H:%M").time()
            if now < start_time:
                return lesson

def load_settings():
    try:
        if os.name == "nt":
            base_dir = os.getenv("APPDATA")
            config_dir = os.path.join(base_dir, "OverlayApp")
        else:
            base_dir = os.path.expanduser("~/.config")
            config_dir = os.path.join(base_dir, "overlay")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "settings.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            return settings
        return {}
    except Exception as e:
        print(f"Błąd wczytywania ustawień: {e}")
        return {}