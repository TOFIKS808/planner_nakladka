import requests
import os
import json
from datetime import datetime, timedelta

def fetch_timetable(api_url):
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching timetable data: {e}")
        return None

def get_current_hour():
    try:
        response = requests.get("https://planzajecpk.app/api/hours")
        response.raise_for_status()
        for lesson in response.json():
            start_time = datetime.strptime(lesson['start'], "%H:%M").time()
            end_time = datetime.strptime(lesson['end'], "%H:%M").time()
            now = datetime.now().time()
            if start_time <= now <= end_time:
                return lesson
    except requests.RequestException as e:
        print(f"Error fetching timetable data: {e}")
    return None

def get_next_hour(current_hour_id=None):
    try:
        response = requests.get("https://planzajecpk.app/api/hours")
        response.raise_for_status()
        hours = response.json()
        now = datetime.now().time()
        if current_hour_id is None:
            for lesson in hours:
                start_time = datetime.strptime(lesson['start'], "%H:%M").time()
                if start_time > now:
                    return lesson
            return None
        for lesson in hours:
            if lesson['id'] == current_hour_id + 1:
                return lesson
        return None
    except requests.RequestException as e:
        print(f"Error fetching timetable data: {e}")
        return None

def calculate_break_info(current_hour_obj, next_hour_obj):
    try:
        now = datetime.now()
        current_end = datetime.strptime(current_hour_obj.get('end'), "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        next_start = datetime.strptime(next_hour_obj.get('start'), "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        
        # Oblicz czas od początku przerwy do teraz
        break_start_time = current_end
        time_elapsed = (now - break_start_time).total_seconds() / 60
        break_duration = (next_start - break_start_time).total_seconds() / 60
        
        remaining_time = max(0, (next_start - now).total_seconds() / 60)
        time_elapsed = max(0, min(time_elapsed, break_duration))  # Nie pozwól żeby czas był ujemny lub większy niż break_duration
        
        return {
            "syllabus": "Przerwa",
            "remaining_time": round(remaining_time, 2),
            "break_duration": round(break_duration, 2),
            "time_elapsed": round(time_elapsed, 2),  # Dodajemy czas który już minął
            "hall": "-",
            "lessonType": "",
            "classGroup": "",
            "hallGroup": "",
            "total_duration": round(break_duration, 2),
            "is_break": True  # Flaga wskazująca że to przerwa
        }
    except (KeyError, ValueError, TypeError) as e:
        print(f"Błąd obliczania przerwy: {e}")
        return {
            "syllabus": "Przerwa",
            "remaining_time": 0,
            "break_duration": 0,
            "time_elapsed": 0,
            "hall": "-",
            "lessonType": "",
            "classGroup": "",
            "hallGroup": "",
            "total_duration": 1,
            "is_break": True
        }

def is_lesson_matching_filters(lesson, group_l, group_k):
    lesson_type = lesson.get('lessonType', '')
    if lesson_type in ["W", "Ć"]:
        return True
    if group_l is None and group_k is None:
        return True
    if group_l and group_l in lesson_type:
        return True
    if group_k and group_k in lesson_type:
        return True
    if not lesson_type:
        return True
    return False

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

def get_consecutive_lessons(initial_lesson):
    """Znajduje wszystkie kolejne lekcje tworzące blok (ta sama nazwa, sala i typ)"""
    try:
        response = fetch_timetable("https://planzajecpk.app/api/timetable/a")
        if not response:
            return [initial_lesson]
        
        day = initial_lesson['day']
        current_hour = initial_lesson['hour']
        syllabus = initial_lesson['syllabus']
        hall = initial_lesson['hall']
        lesson_type = initial_lesson.get('lessonType', '')
        
        consecutive_lessons = [initial_lesson]
        
        # Szukaj kolejnych lekcji w następnych godzinach
        next_hour = current_hour + 1
        while True:
            found_next = False
            for lesson in response:
                if (lesson['day'] == day and lesson['hour'] == next_hour and
                    lesson['syllabus'] == syllabus and lesson['hall'] == hall and
                    lesson.get('lessonType', '') == lesson_type):
                    
                    consecutive_lessons.append(lesson)
                    next_hour += 1
                    found_next = True
                    break
            
            if not found_next:
                break
        
        return consecutive_lessons
    except Exception as e:
        print(f"Błąd podczas znajdowania kolejnych lekcji: {e}")
        return [initial_lesson]

def calculate_total_remaining_time(consecutive_lessons, current_hour_obj):
    """Oblicza całkowity pozostały czas dla bloku lekcji"""
    try:
        now = datetime.now()
        
        # Jeśli to przerwa
        if consecutive_lessons[0].get('syllabus') == 'Przerwa':
            return consecutive_lessons[0].get('remaining_time', 0)
        
        # Pobierz godziny z API
        hours_response = requests.get("https://planzajecpk.app/api/hours")
        hours_response.raise_for_status()
        hours_data = hours_response.json()
        
        # Znajdź godzinę końca ostatniej lekcji w bloku
        last_lesson_hour_id = consecutive_lessons[-1]['hour']
        last_hour_obj = None
        for hour_obj in hours_data:
            if hour_obj['id'] == last_lesson_hour_id:
                last_hour_obj = hour_obj
                break
        
        if not last_hour_obj:
            return 0
        
        # Oblicz czas do końca ostatniej lekcji w bloku
        end_time = datetime.strptime(last_hour_obj['end'], "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        
        remaining_seconds = (end_time - now).total_seconds()
        return round(max(0, remaining_seconds / 60), 2)
        
    except Exception as e:
        print(f"Błąd obliczania całkowitego czasu: {e}")
        return 0

def calculate_lesson_time_elapsed(consecutive_lessons, current_hour_obj):
    """Oblicza czas jaki już minął od początku bloku lekcji"""
    try:
        now = datetime.now()
        
        # Pobierz godziny z API
        hours_response = requests.get("https://planzajecpk.app/api/hours")
        hours_response.raise_for_status()
        hours_data = hours_response.json()
        
        # Znajdź godzinę rozpoczęcia pierwszej lekcji w bloku
        first_lesson_hour_id = consecutive_lessons[0]['hour']
        first_hour_obj = None
        for hour_obj in hours_data:
            if hour_obj['id'] == first_lesson_hour_id:
                first_hour_obj = hour_obj
                break
        
        if not first_hour_obj:
            return 0
        
        # Oblicz czas od początku pierwszej lekcji
        start_time = datetime.strptime(first_hour_obj['start'], "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        
        time_elapsed = (now - start_time).total_seconds() / 60
        return round(max(0, time_elapsed), 2)
        
    except Exception as e:
        print(f"Błąd obliczania czasu lekcji: {e}")
        return 0

def get_current_lesson(settings=None):
    if settings is None:
        settings = load_settings()
    
    response = fetch_timetable("https://planzajecpk.app/api/timetable/a")
    current_hour_obj = get_current_hour()

    if not current_hour_obj or not response:
        next_hour_obj = get_next_hour()
        if not next_hour_obj:
            return {
                "syllabus": "Przerwa",
                "remaining_time": 0,
                "lessonType": "",
                "classGroup": "",
                "hallGroup": "",
                "break_duration": 0,
                "total_duration": 1,
                "time_elapsed": 0,
                "is_break": True,
                "consecutive_count": 0
            }
        try:
            now = datetime.now()
            next_start = datetime.strptime(next_hour_obj['start'], "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            remaining_time = round(max(0, (next_start - now).total_seconds() / 60), 2)
            total_duration = max(1, remaining_time)
            
            # Dla przerwy przed pierwszą lekcją, time_elapsed = 0 (dopiero zaczyna się przerwa)
            return {
                "syllabus": "Przerwa",
                "remaining_time": remaining_time,
                "break_duration": remaining_time,
                "time_elapsed": 0,
                "hall": "-",
                "lessonType": "",
                "classGroup": "",
                "hallGroup": "",
                "total_duration": total_duration,
                "is_break": True,
                "consecutive_count": 0
            }
        except (KeyError, ValueError):
            return {
                "syllabus": "Przerwa",
                "remaining_time": 0,
                "break_duration": 0,
                "time_elapsed": 0,
                "hall": "-",
                "lessonType": "",
                "classGroup": "",
                "hallGroup": "",
                "total_duration": 1,
                "is_break": True,
                "consecutive_count": 0
            }
    
    group_l = settings.get("group_l")
    group_k = settings.get("group_k")
    
    for lesson in response:
        if lesson['day'] == datetime.now().weekday() + 1 and lesson['hour'] == current_hour_obj['id']:
            if not is_lesson_matching_filters(lesson, group_l, group_k):
                continue
            
            # Znajdź wszystkie kolejne lekcji tworzące blok
            consecutive_lessons = get_consecutive_lessons(lesson)
            total_remaining_time = calculate_total_remaining_time(consecutive_lessons, current_hour_obj)
            time_elapsed = calculate_lesson_time_elapsed(consecutive_lessons, current_hour_obj)
            
            # Przygotuj obiekt lekcji z informacjami o bloku
            current_lesson = consecutive_lessons[0].copy()
            current_lesson["remaining_time"] = total_remaining_time
            current_lesson["total_duration"] = max(1, len(consecutive_lessons) * 45)
            current_lesson["time_elapsed"] = time_elapsed
            current_lesson["consecutive_count"] = len(consecutive_lessons)
            current_lesson["break_duration"] = 0
            current_lesson["is_break"] = False
            
            return current_lesson
    
    # Jeśli nie ma lekcji w aktualnej godzinie - przerwa
    next_hour_obj = get_next_hour(current_hour_obj['id'])
    if next_hour_obj:
        break_info = calculate_break_info(current_hour_obj, next_hour_obj)
        break_info.update({
            "lessonType": "",
            "classGroup": "",
            "hallGroup": "",
            "consecutive_count": 0
        })
        return break_info
    
    return {
        "syllabus": "Przerwa",
        "remaining_time": 0,
        "lessonType": "",
        "classGroup": "",
        "hallGroup": "",
        "break_duration": 0,
        "total_duration": 1,
        "time_elapsed": 0,
        "is_break": True,
        "consecutive_count": 0
    }

def get_next_lesson(current_hour_obj, settings=None):
    """Pobiera informacje o następnej lekcji lub przerwie (zachowuje kompatybilność)"""
    if settings is None:
        settings = load_settings()
    
    if current_hour_obj is None:
        # Brak aktualnej lekcji - następna to pierwsza lekcja dnia lub koniec
        next_hour_obj = get_next_hour()
        if not next_hour_obj:
            return {
                "syllabus": "Koniec zajęć",
                "hall": "-",
                "lessonType": "",
                "classGroup": "",
                "hallGroup": "",
                "remaining_time": 0,
                "break_duration": 0,
                "total_duration": 1,
                "time_elapsed": 0,
                "is_break": False,
                "consecutive_count": 0
            }
        
        # Sprawdź czy w następnej godzinie jest lekcja
        response = fetch_timetable("https://planzajecpk.app/api/timetable/a")
        group_l = settings.get("group_l")
        group_k = settings.get("group_k")
        
        if response:
            for lesson in response:
                if lesson['day'] == datetime.now().weekday() + 1 and lesson['hour'] == next_hour_obj['id']:
                    if not is_lesson_matching_filters(lesson, group_l, group_k):
                        continue
                    
                    # Znajdź wszystkie kolejne lekcji tworzące blok
                    consecutive_lessons = get_consecutive_lessons(lesson)
                    next_lesson = consecutive_lessons[0].copy()
                    next_lesson["total_duration"] = max(1, len(consecutive_lessons) * 45)
                    next_lesson["consecutive_count"] = len(consecutive_lessons)
                    next_lesson["time_elapsed"] = 0
                    next_lesson["is_break"] = False
                    
                    # Oblicz czas do rozpoczęcia tej lekcji
                    now = datetime.now()
                    next_start = datetime.strptime(next_hour_obj['start'], "%H:%M").replace(
                        year=now.year, month=now.month, day=now.day
                    )
                    remaining_time = round(max(0, (next_start - now).total_seconds() / 60), 2)
                    next_lesson["remaining_time"] = remaining_time
                    
                    return next_lesson
        
        # Jeśli nie ma lekcji w następnej godzinie - przerwa do końca dnia
        now = datetime.now()
        next_start = datetime.strptime(next_hour_obj['start'], "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        remaining_time = round(max(0, (next_start - now).total_seconds() / 60), 2)
        total_duration = max(1, remaining_time)
        
        return {
            "syllabus": "Przerwa",
            "hall": "-",
            "lessonType": "",
            "classGroup": "",
            "hallGroup": "",
            "remaining_time": remaining_time,
            "break_duration": remaining_time,
            "total_duration": total_duration,
            "time_elapsed": 0,
            "is_break": True,
            "consecutive_count": 0
        }
    
    # Jeśli jest aktualna lekcja, znajdź następną
    response = fetch_timetable("https://planzajecpk.app/api/timetable/a")
    if not response:
        return {
            "syllabus": "Przerwa",
            "hall": "-",
            "lessonType": "",
            "classGroup": "",
            "hallGroup": "",
            "remaining_time": 0,
            "break_duration": 0,
            "total_duration": 1,
            "time_elapsed": 0,
            "is_break": True,
            "consecutive_count": 0
        }
    
    current_hour_id = current_hour_obj.get('id')
    next_hour_obj = get_next_hour(current_hour_id)
    group_l = settings.get("group_l")
    group_k = settings.get("group_k")
    
    if next_hour_obj:
        # Szukaj lekcji w następnej godzinie
        for lesson in response:
            if lesson['day'] == datetime.now().weekday() + 1 and lesson['hour'] == next_hour_obj['id']:
                if not is_lesson_matching_filters(lesson, group_l, group_k):
                    continue
                
                # Znajdź wszystkie kolejne lekcji tworzące blok
                consecutive_lessons = get_consecutive_lessons(lesson)
                next_lesson = consecutive_lessons[0].copy()
                next_lesson["total_duration"] = max(1, len(consecutive_lessons) * 45)
                next_lesson["consecutive_count"] = len(consecutive_lessons)
                next_lesson["time_elapsed"] = 0
                next_lesson["is_break"] = False
                
                # Oblicz czas do rozpoczęcia tej lekcji
                now = datetime.now()
                next_start = datetime.strptime(next_hour_obj['start'], "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                remaining_time = round(max(0, (next_start - now).total_seconds() / 60), 2)
                next_lesson["remaining_time"] = remaining_time
                
                return next_lesson
        
        # Jeśli nie ma lekcji w następnej godzinie - oblicz przerwę
        break_info = calculate_break_info(current_hour_obj, next_hour_obj)
        break_info["total_duration"] = max(1, break_info.get("break_duration", 1))
        return break_info
    
    # Koniec dnia
    return {
        "syllabus": "Koniec zajęć",
        "hall": "-",
        "lessonType": "",
        "classGroup": "",
        "hallGroup": "",
        "remaining_time": 0,
        "break_duration": 0,
        "total_duration": 1,
        "time_elapsed": 0,
        "is_break": False,
        "consecutive_count": 0
    }