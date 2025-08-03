import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log_event(event_type: str, details: dict, level: str = "info"):
    """
    Logs a structured JSON message.
    """
    log_entry = {
        "event": event_type,
        "details": details
    }

    if level == "info":
        logger.info(json.dumps(log_entry))
    elif level == "warning":
        logger.warning(json.dumps(log_entry))
    elif level == "error":
        logger.error(json.dumps(log_entry))
    else:
        logger.debug(json.dumps(log_entry))
