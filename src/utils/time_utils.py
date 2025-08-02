# src/utils/time_utils.py

from datetime import datetime
import pytz

def get_current_time_info(timezone: str = "America/Bogota") -> dict:
    """
    Returns current date and time information formatted for chatbot use.

    :param timezone: Timezone string, default is Colombia time.
    :return: Dictionary with ISO, date, time, and human-readable formats.
    """
    now = datetime.now(pytz.timezone(timezone))

    return {
        "iso": now.isoformat(),                           # e.g. 2025-08-02T13:45:00-05:00
        "date": now.strftime("%Y-%m-%d"),                 # e.g. 2025-08-02
        "day": now.strftime("%A"),                        # e.g. "Saturday"
        "time": now.strftime("%H:%M"),                    # e.g. "13:45"
        "full_human": now.strftime("%A %d de %B de %Y, %I:%M %p")  # e.g. "Sábado 02 de agosto de 2025, 01:45 PM"
    }
