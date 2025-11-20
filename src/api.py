import requests
import os
import json
from datetime import datetime

def fetch_timetable(settings=None):
    try:
        if settings is None:
                settings = load_settings()
        
        if settings["group_c"] is not None or settings["group_l"] != " ": group_c = settings["group_c"][-1]
        else: group_c = 1
        if settings["group_k"] is not None or settings["group_l"] != " ": group_k = settings["group_k"][-1]
        else: group_k = 1
        if settings["group_l"] is not None or settings["group_l"] != " ": group_l = settings["group_l"][-1]
        else: group_l = 1
        response = requests.get()
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching timetable data: {e}")
        return None

def get_current_segment(timetable=None):
    if timetable is None:
        timetable = fetch_timetable()

        for lesson in timetable:
            start_time = datetime.strptime(lesson['start'], "%H:%M").time()
            end_time = datetime.strptime(lesson['end'], "%H:%M").time()
            now = datetime.now().time()
            if start_time <= now <= end_time:
                return lesson

def get_next_segment(timetable=None):
    if timetable is None:
        timetable = fetch_timetable()

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