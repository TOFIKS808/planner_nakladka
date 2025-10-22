import requests
from datetime import datetime

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


def get_current_lesson():
    responce = fetch_timetable("https://planzajecpk.app/api/timetable/a")

    current = get_current_hour()
    if not current or not responce:
        nextLesson = get_next_hour()
        cel = datetime.strptime(nextLesson['start'], "%H:%M")
        teraz = datetime.now()
        cel_dzis = teraz.replace(hour=cel.hour, minute=cel.minute, second=0, microsecond=0)
        return {"syllabus": "Przerwa", "remaining_time": round((cel_dzis - teraz).total_seconds() / 60, 2), "hall": "-"}
    for lesson in responce:
        if lesson['day'] == datetime.now().weekday()+1 and lesson['hour'] == current['id']:
            cel = datetime.strptime(current['end'], "%H:%M")
            teraz = datetime.now()
            cel_dzis = teraz.replace(hour=cel.hour, minute=cel.minute, second=0, microsecond=0)
            lesson["remaining_time"] = round((cel_dzis - teraz).total_seconds() / 60, 2)
            return lesson
        
def get_next_hour():
    try:
        response = requests.get("https://planzajecpk.app/api/hours")
        response.raise_for_status()
        now = datetime.now().time()
        for lesson in response.json():
            start_time = datetime.strptime(lesson['start'], "%H:%M").time()
            if now < start_time:
                return lesson
    except requests.RequestException as e:
        print(f"Error fetching timetable data: {e}")
        return None
        
def get_next_lesson():
    responce = fetch_timetable("https://planzajecpk.app/api/timetable/a")
    current = get_current_hour()
    if not current or not responce:
        return {"syllabus": "Brak dalszych zajęć", "hall": "-"}
    next_id = current['id'] + 1
    for lesson in responce:
        if lesson['day'] == datetime.now().weekday()+1 and lesson['hour'] == next_id:
            return lesson
        