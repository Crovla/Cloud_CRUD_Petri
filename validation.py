from datetime import date

from config import STATUSES, today

def validate(data):
    clean, errors = {}, {}

    raw_name = data.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    if 2 <= len(name) <= 80:
        clean["name"] = name
    else:
        errors["name"] = "Name must be 2-80 characters."

    try:
        count = int(str(data.get("colony_count")).strip())
        if count < 0:
            raise ValueError
        clean["colony_count"] = count
    except ValueError:
        errors["colony_count"] = "Colony count must be a whole number, 0 or more."

    try:
        temp = float(str(data.get("temperature")).strip().replace(",", "."))
        if not 0 <= temp <= 100:
            raise ValueError
        clean["temperature"] = temp
    except ValueError:
        errors["temperature"] = "Temperature must be a number between 0 and 100."

    flag = data.get("is_pathogenic", False)
    if isinstance(flag, str):
        value = flag.lower()
        if value in ("on", "true", "1", "yes"):
            flag = True
        elif value in ("off", "false", "0", "no", ""):
            flag = False
    if isinstance(flag, bool):
        clean["is_pathogenic"] = flag
    else:
        errors["is_pathogenic"] = "Must be true or false."

    for field in ("incubation_started_on", "incubation_ends_on"):
        try:
            clean[field] = date.fromisoformat(str(data.get(field)))
        except ValueError:
            errors[field] = "Enter a valid date (YYYY-MM-DD)."
    start, end = clean.get("incubation_started_on"), clean.get("incubation_ends_on")
    if start and start > today():
        errors["incubation_started_on"] = "The start of incubation cannot be in the future."
    if start and end and end < start:
        errors["incubation_ends_on"] = "The incubation cannot end before it starts."
    status = data.get("incubation_status", "Incubating")
    if status not in STATUSES:
        errors["incubation_status"] = "Select a valid status."
    else:
        clean["incubation_status"] = status
    return clean, errors