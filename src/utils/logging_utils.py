import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        # Format all logs as JSON
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage()
        }
        return json.dumps(log_record)

# Attach formatter only once
if not logger.handlers or not any(isinstance(h.formatter, JSONFormatter) for h in logger.handlers):
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

def log_event(event_type: str, details: dict, level: str = "info"):
    """
    Logs structured JSON to CloudWatch.
    """
    message = {
        "event": event_type,
        "details": details
    }

    if level == "info":
        logger.info(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)
    else:
        logger.debug(message)
