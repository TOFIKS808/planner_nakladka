import src.api as api
import json

try:
    # Fetch with default settings (group 1)
    settings = {"group_c": "1", "group_l": "1", "group_k": "1"}
    timetable = api.fetch_timetable(settings)
    
    if timetable:
        print(f"Timetable items: {len(timetable)}")
        if len(timetable) > 0:
            print("First lesson keys:", timetable[0].keys())
            print("First lesson sample:", json.dumps(timetable[0], indent=2, ensure_ascii=False))
            
            # Check if 'hall' or 'sala' exists
            if 'hall' in timetable[0]:
                print("Field 'hall' found.")
            if 'sala' in timetable[0]:
                print("Field 'sala' found.")
    else:
        print("Failed to fetch timetable.")

except Exception as e:
    print(f"Error: {e}")
