import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Global logger instance
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# -------- Invocation context (set per Lambda call) --------
_context: Dict[str, Any] = {
    "service": os.getenv("SERVICE_NAME", "simulacros-ai-assistant"),
    "stage": os.getenv("STAGE", os.getenv("ENV", "prod")),
    "region": os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", None)),
    "function": os.getenv("AWS_LAMBDA_FUNCTION_NAME"),
    "request_id": None,
}


def set_invocation_context(context: Any) -> None:
    """
    Call at the start of each Lambda:
        set_invocation_context(context)
    Stores AWS Lambda request metadata for later logs.
    """
    try:
        _context["function"] = getattr(context, "function_name", _context.get("function"))
        _context["request_id"] = getattr(context, "aws_request_id", None)
    except Exception:
        pass


# -------- JSON formatter --------
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
            "details": getattr(record, "details", None),
            **_context,  # service, stage, region, function, request_id
        }

        # Include exception info if attached
        if hasattr(record, "exc_info") and record.exc_info:
            payload["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "stack": "".join(traceback.format_exception(*record.exc_info)),
            }

        return json.dumps(payload, ensure_ascii=False)


# Attach handler once
if not logger.handlers or not any(isinstance(h.formatter, JSONFormatter) for h in logger.handlers):
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)


# -------- Public API --------
def log_event(event_type: str, details: Optional[dict] = None, level: str = "info", error: Exception = None):
    """
    Structured logging wrapper.

    Example:
        log_event("conversation_created", {"conversation_id": "123"})
        log_event("lambda_exception", {"error": str(e)}, level="error", error=e)
    """
    record = {
        "event": event_type,
        "details": details or {},
    }

    if error:
        logger.error(record, exc_info=error)
        return

    level = level.lower()
    if level == "info":
        logger.info(record)
    elif level == "warning":
        logger.warning(record)
    elif level == "error":
        logger.error(record)
    else:
        logger.debug(record)
