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
        time_elapsed = max(0, min(time_elapsed, break_duration))

        return {
            "syllabus": "Przerwa",
            "remaining_time": round(remaining_time, 2),
            "break_duration": round(break_duration, 2),
            "time_elapsed": round(time_elapsed, 2),
            "hall": "-",
            "lessonType": "",
            "classGroup": "",
            "hallGroup": "",
            "total_duration": round(break_duration, 2),
            "is_break": True
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

def get_full_lesson_block(initial_lesson):
    """Znajduje CAŁY blok lekcji - zarówno wstecz jak i do przodu"""
    try:
        response = fetch_timetable("https://planzajecpk.app/api/timetable/a")
        if not response:
            return [initial_lesson]
        
        day = initial_lesson['day']
        current_hour = initial_lesson['hour']
        syllabus = initial_lesson['syllabus']
        hall = initial_lesson['hall']
        lesson_type = initial_lesson.get('lessonType', '')
        
        # Znajdź wszystkie lekcje w bloku
        full_block = []
        
        # 1. SZUKAJ WSTECZ - znajdź poprzednie lekcje w bloku
        prev_hour = current_hour - 1
        previous_lessons = []
        
        while True:
            found_prev = False
            for lesson in response:
                if (lesson['day'] == day and lesson['hour'] == prev_hour and
                    lesson['syllabus'] == syllabus and lesson['hall'] == hall and
                    lesson.get('lessonType', '') == lesson_type):
                    
                    previous_lessons.insert(0, lesson)
                    prev_hour -= 1
                    found_prev = True
                    break
            
            if not found_prev:
                break
        
        # 2. DODAJ POPRZEDNIE LEKCJE + AKTUALNĄ + NASTĘPNE
        full_block.extend(previous_lessons)
        full_block.append(initial_lesson)
        
        # 3. SZUKAJ DO PRZODU - znajdź następne lekcje w bloku
        next_hour = current_hour + 1
        while True:
            found_next = False
            for lesson in response:
                if (lesson['day'] == day and lesson['hour'] == next_hour and
                    lesson['syllabus'] == syllabus and lesson['hall'] == hall and
                    lesson.get('lessonType', '') == lesson_type):
                    
                    full_block.append(lesson)
                    next_hour += 1
                    found_next = True
                    break
            
            if not found_next:
                break
        
        return full_block
        
    except Exception as e:
        print(f"Błąd podczas znajdowania pełnego bloku lekcji: {e}")
        return [initial_lesson]

def calculate_block_remaining_time(lesson_block):
    """Oblicza całkowity pozostały czas do końca bloku lekcji"""
    try:
        if not lesson_block:
            return 0
            
        now = datetime.now()
        
        # Pobierz godziny z API
        hours_response = requests.get("https://planzajecpk.app/api/hours")
        hours_response.raise_for_status()
        hours_data = hours_response.json()
        
        # Znajdź godzinę końca OSTATNIEJ lekcji w bloku
        last_lesson = lesson_block[-1]
        last_hour_id = last_lesson['hour']
        
        last_hour_obj = None
        for hour_obj in hours_data:
            if hour_obj['id'] == last_hour_id:
                last_hour_obj = hour_obj
                break
        
        if not last_hour_obj:
            return 0
        
        # Oblicz czas do końca ostatniej lekcji w bloku
        end_time = datetime.strptime(last_hour_obj['end'], "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        
        remaining_seconds = max(0, (end_time - now).total_seconds())
        return round(remaining_seconds / 60, 2)
        
    except Exception as e:
        print(f"Błąd obliczania pozostałego czasu bloku: {e}")
        return 0

def calculate_block_total_duration(lesson_block):
    """Oblicza całkowity czas trwania bloku lekcji"""
    try:
        if not lesson_block:
            return 45
            
        # Pobierz godziny z API
        hours_response = requests.get("https://planzajecpk.app/api/hours")
        hours_response.raise_for_status()
        hours_data = hours_response.json()
        
        # Znajdź godzinę rozpoczęcia PIERWSZEJ lekcji w bloku
        first_lesson = lesson_block[0]
        first_hour_id = first_lesson['hour']
        
        first_hour_obj = None
        for hour_obj in hours_data:
            if hour_obj['id'] == first_hour_id:
                first_hour_obj = hour_obj
                break
        
        # Znajdź godzinę końca OSTATNIEJ lekcji w bloku
        last_lesson = lesson_block[-1]
        last_hour_id = last_lesson['hour']
        
        last_hour_obj = None
        for hour_obj in hours_data:
            if hour_obj['id'] == last_hour_id:
                last_hour_obj = hour_obj
                break
        
        if not first_hour_obj or not last_hour_obj:
            return len(lesson_block) * 45
        
        # Oblicz całkowity czas trwania bloku
        start_time = datetime.strptime(first_hour_obj['start'], "%H:%M")
        end_time = datetime.strptime(last_hour_obj['end'], "%H:%M")
        
        total_minutes = (end_time.hour * 60 + end_time.minute) - (start_time.hour * 60 + start_time.minute)
        return max(total_minutes, len(lesson_block) * 45)
        
    except Exception as e:
        print(f"Błąd obliczania całkowitego czasu bloku: {e}")
        return len(lesson_block) * 45

def calculate_block_elapsed_time(lesson_block):
    """Oblicza czas który już minął od początku bloku lekcji"""
    try:
        if not lesson_block:
            return 0
            
        now = datetime.now()
        
        # Pobierz godziny z API
        hours_response = requests.get("https://planzajecpk.app/api/hours")
        hours_response.raise_for_status()
        hours_data = hours_response.json()
        
        # Znajdź godzinę rozpoczęcia PIERWSZEJ lekcji w bloku
        first_lesson = lesson_block[0]
        first_hour_id = first_lesson['hour']
        
        first_hour_obj = None
        for hour_obj in hours_data:
            if hour_obj['id'] == first_hour_id:
                first_hour_obj = hour_obj
                break
        
        if not first_hour_obj:
            return 0
        
        # Oblicz czas od początku pierwszej lekcji w bloku
        start_time = datetime.strptime(first_hour_obj['start'], "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        
        elapsed_seconds = max(0, (now - start_time).total_seconds())
        return round(elapsed_seconds / 60, 2)
        
    except Exception as e:
        print(f"Błąd obliczania czasu który minął: {e}")
        return 0

def get_current_lesson_with_full_block(settings=None):
    """Pobiera aktualną lekcję z pełnym łączeniem wstecznym"""
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
            
            # Znajdź CAŁY blok lekcji (wstecz + do przodu)
            full_lesson_block = get_full_lesson_block(lesson)
            
            # Oblicz czasy dla całego bloku
            total_remaining_time = calculate_block_remaining_time(full_lesson_block)
            total_duration = calculate_block_total_duration(full_lesson_block)
            time_elapsed = calculate_block_elapsed_time(full_lesson_block)
            
            # Przygotuj obiekt lekcji z informacjami o bloku
            current_lesson = full_lesson_block[0].copy()  # Używamy pierwszej lekcji z bloku
            current_lesson["remaining_time"] = total_remaining_time
            current_lesson["total_duration"] = total_duration
            current_lesson["time_elapsed"] = time_elapsed
            current_lesson["consecutive_count"] = len(full_lesson_block)
            current_lesson["break_duration"] = 0
            current_lesson["is_break"] = False
            current_lesson["full_block"] = full_lesson_block
            
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

def get_real_next_lesson(current_hour_obj, current_syllabus, settings=None):
    """Znajduje prawdziwą następną lekcję pomijając połączone lekcje"""
    try:
        response = fetch_timetable("https://planzajecpk.app/api/timetable/a")
        if not response:
            return {"syllabus": "Brak dalszych zajęć", "hall": "-"}
        
        current_hour_id = current_hour_obj.get('id') if current_hour_obj else None
        
        # Zacznij szukanie od następnej godziny po aktualnej
        next_hour_obj = get_next_hour(current_hour_id)
        
        # Szukaj pierwszej lekcji która NIE ma tej samej nazwy co aktualna
        while next_hour_obj:
            for lesson in response:
                if (lesson['day'] == datetime.now().weekday() + 1 and 
                    lesson['hour'] == next_hour_obj['id'] and
                    lesson.get('syllabus') != current_syllabus):
                    
                    # Sprawdź czy lekcja pasuje do filtrów
                    if is_lesson_matching_filters(lesson, 
                                                 settings.get("group_l") if settings else None,
                                                 settings.get("group_k") if settings else None):
                        return lesson
            
            # Przejdź do następnej godziny
            next_hour_obj = get_next_hour(next_hour_obj['id'])
        
        return {"syllabus": "Koniec zajęć", "hall": "-"}
        
    except Exception as e:
        print(f"Błąd podczas znajdowania następnych zajęć: {e}")
        return {"syllabus": "Brak dalszych zajęć", "hall": "-"}

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
                    consecutive_lessons = get_full_lesson_block(lesson)
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
                consecutive_lessons = get_full_lesson_block(lesson)
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

# Zachowaj kompatybilność - aliasy
get_current_lesson = get_current_lesson_with_full_block