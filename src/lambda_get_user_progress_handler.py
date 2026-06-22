# src/lambda_get_user_progress_handler.py
import json
import logging

from src.services.exam_results_service import get_user_progress
from src.utils.logging_utils import log_event, set_invocation_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    set_invocation_context(context)

    # 1. UNIVERSAL CORS PREFLIGHT HANDLING
    headers = event.get("headers") or {}
    normalized_headers = {k.lower(): v for k, v in headers.items()}
    
    if "access-control-request-method" in normalized_headers:
        return _response(200, {"ok": True})

    try:
        log_event("get_user_progress_invocation", {
            "source": "GetUserProgressHandler"
        })

        # 2. Extract userId (Checking both Query Strings and Body to be safe)
        user_id = None
        query_params = event.get("queryStringParameters") or {}
        user_id = query_params.get("userId")

        if not user_id and event.get("body"):
            body = json.loads(event.get("body"))
            user_id = body.get("userId")

        # 3. Validation
        if not user_id:
            log_event("get_user_progress_validation_failed", {
                "reason": "missing userId"
            }, level="warning")
            return _response(400, {"error": "userId is required"})

        # 4. Fetch data using the existing service layer
        progress_data = get_user_progress(user_id=user_id)

        log_event("get_user_progress_success", {
            "user_id": user_id,
            "exams_found": len(progress_data)
        })

        # 5. Return the array of past exams
        return _response(200, {"ok": True, "progress": progress_data})

    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        return _response(400, {"error": str(ve)})
    except Exception as e:
        log_event("lambda_exception", {
            "source": "GetUserProgressHandler"
        }, level="error", error=e)
        return _response(500, {"error": "Internal error fetching user progress"})


def _response(status_code, body):
    """Generates the HTTP response with Wix-compatible CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST"
        },
        "body": json.dumps(body)
    }