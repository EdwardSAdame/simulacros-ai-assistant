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
    Call at the start of each Lambda to capture Request ID.
    Usage: set_invocation_context(context)
    """
    try:
        _context["function"] = getattr(context, "function_name", _context.get("function"))
        _context["request_id"] = getattr(context, "aws_request_id", None)
    except Exception:
        pass

# -------- JSON formatter --------
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # 1. Base Payload (Timestamp + Context)
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            **_context,  # service, stage, region, function, request_id
        }

        # 2. Extract Structured Data (from 'extra' param)
        # Esto arregla el problema: lee datos inyectados explícitamente
        if hasattr(record, "structured_data"):
            payload.update(record.structured_data)
        else:
            # Fallback para logs normales (ej. librerías externas)
            payload["message"] = record.getMessage()

        # 3. Include Exception Info
        if hasattr(record, "exc_info") and record.exc_info:
            payload["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "stack": "".join(traceback.format_exception(*record.exc_info)),
            }

        return json.dumps(payload, ensure_ascii=False)

# Attach handler once & clear default AWS handlers to avoid duplication
if not logger.handlers or not any(isinstance(h.formatter, JSONFormatter) for h in logger.handlers):
    for h in logger.handlers:
        logger.removeHandler(h)
        
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

# -------- Public API --------
def log_event(event_type: str, details: Optional[dict] = None, level: str = "info", error: Exception = None):
    """
    Structured logging wrapper optimized for CloudWatch Insights.
    
    Usage:
        log_event("context_resolution", {"url": "/home", "exam": "ICFES"})
    """
    # Empaquetamos los datos
    data = {
        "event": event_type,
        "details": details or {}
    }

    # CRÍTICO: Usamos 'extra' para pasar el objeto limpio al Formatter
    extra_payload = {"structured_data": data}

    if error:
        logger.error(event_type, exc_info=error, extra=extra_payload)
        return

    lvl = level.lower()
    if lvl == "warning":
        logger.warning(event_type, extra=extra_payload)
    elif lvl == "error":
        logger.error(event_type, extra=extra_payload)
    else:
        logger.info(event_type, extra=extra_payload)