# src/utils/time_utils.py

from datetime import datetime
import pytz

def get_current_time_info(timezone: str = "America/Bogota") -> dict:
    """
    Returns current date and time information formatted for chatbot use.
    """
    now = datetime.now(pytz.timezone(timezone))
    return {
        "iso": now.isoformat(),                           # e.g. 2025-08-02T13:45:00-05:00
        "date": now.strftime("%Y-%m-%d"),                 # e.g. 2025-08-02
        "day": now.strftime("%A"),                        # e.g. "Saturday"
        "time": now.strftime("%H:%M"),                    # e.g. "13:45"
        "full_human": now.strftime("%A %d de %B de %Y, %I:%M %p"),
    }

def infer_target_semester(timezone: str = "America/Bogota") -> str:
    """
    Map today's date → target admission semester label.

    Jan–Jun  (1..6)  → YYYY-2  (exam now, ingreso 2 del mismo año)
    Jul–Dec (7..12) → (YYYY+1)-1 (exam ahora, ingreso 1 del siguiente año)
    """
    now = datetime.now(pytz.timezone(timezone))
    y, m = now.year, now.month
    return f"{y}-2" if 1 <= m <= 6 else f"{y + 1}-1"

def semester_season(semester: str) -> str:
    """
    Return '1' if semester ends with '-1', else '2'. Useful for seasonality bucketing.
    """
    s = str(semester).strip()
    return "1" if s.endswith("-1") else "2"
