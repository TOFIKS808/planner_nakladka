import requests
import os
import json
import urllib.parse
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
        hidden_subjects = settings.get("hidden_subjects", [])

        # Sprawdź czy grupy są ustawione (nie None)
        if not group_c_val or not group_l_val or not group_k_val:
            # print("Brak ustawionych grup") # Debug
            return None

        # Pobierz ostatni znak (zakładając format np. "11K1" -> "1")
        try:
            group_c = group_c_val
            group_k = group_k_val
            group_l = group_l_val
        except IndexError:
            print("Błąd formatu grupy")
            return None
        
        # Use the global session
        roman = {1:'I', 2:'II', 3:'III', 4:'IV', 5:'V', 6:'VI', 7:'VII', 8:'VIII', 9:'IX', 10:'X', 11:'XI', 12:'XII'}
        now = datetime.now()
        day_str = f"{now.day:02d} {roman[now.month]}"
        
        url = f"https://pk-timetable-scraper-api-orpin.vercel.app/api2/timetable/{group_c}?day={day_str}&lab={group_l}&klab={group_k}&week=auto&merge=true&fill=true&changes=true"
        if hidden_subjects:
            url += f"&hide={urllib.parse.quote(json.dumps(hidden_subjects))}"

        response = session.get(url)
        response.raise_for_status()
        data = response.json()

        # Dodatkowa ochrona po stronie klienta:
        if data and hidden_subjects:
            clean_hidden = [str(h).strip().lower() for h in hidden_subjects if str(h).strip()]
            filtered = []
            days_pl = ['pon', 'wt', 'śr', 'czw', 'pt', 'sob', 'nie']
            today_day = days_pl[now.weekday()]
            for item in data:
                name = (item.get("name") or "").strip().lower()
                syll = (item.get("syllabus") or "").strip().lower()
                start = (item.get("start") or "").strip().lower()
                clean_start = start.lstrip('0')
                if item.get("is_break") or "okienko" in name or "okienko" in syll:
                    filtered.append(item)
                    continue
                is_hidden = False
                for h in clean_hidden:
                    if '(' not in h:
                        if h == name or h in name or h == syll or h in syll:
                            is_hidden = True
                            break
                    else:
                        subj_part = h.split('(')[0].strip()
                        if subj_part and (subj_part in name or subj_part in syll):
                            day_match = (today_day in h) if any(d in h for d in days_pl) else True
                            time_match = start and (start in h or (clean_start and clean_start in h))
                            if day_match and time_match:
                                is_hidden = True
                                break
                if not is_hidden:
                    filtered.append(item)
            data = filtered

        return data
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
