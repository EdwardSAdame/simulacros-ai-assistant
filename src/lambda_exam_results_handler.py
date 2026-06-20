# src/lambda_exam_results_handler.py
import json
import logging

from src.services.exam_results_service import process_and_save_exam
from src.utils.logging_utils import log_event, set_invocation_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    set_invocation_context(context)

    # 1. UNIVERSAL CORS PREFLIGHT HANDLING
    # Browsers send 'Access-Control-Request-Method' for preflight requests.
    # This check is reliable regardless of whether 'httpMethod' is null.
    headers = event.get("headers") or {}
    normalized_headers = {k.lower(): v for k, v in headers.items()}
    
    if "access-control-request-method" in normalized_headers:
        return _response(200, {"ok": True})

    try:
        # Lightweight invocation log
        log_event("exam_results_lambda_invocation", {
            "source": "ExamResultsHandler",
            "has_body": "body" in (event or {}) and event.get("body") is not None
        })

        # Parse API Gateway body
        body = json.loads(event.get("body", "{}"))

        # Required routing fields
        user_id = body.get("userId")
        exam_id = body.get("examId")

        # Validation
        if not user_id or not exam_id:
            log_event("exam_results_validation_failed", {
                "reason": "missing userId or examId"
            }, level="warning")
            return _response(400, {"error": "userId and examId are required"})

        # Pass to the service layer for business logic and database persistence
        saved_record = process_and_save_exam(
            user_id=user_id,
            exam_id=exam_id,
            payload=body
        )

        log_event("exam_results_saved_successfully", {
            "user_id": user_id,
            "exam_id": exam_id,
            "score": saved_record.get("TotalScore")
        })

        return _response(200, {"ok": True, "saved": saved_record})

    except ValueError as ve:
        log_event("exam_results_validation_error", {
            "source": "ExamResultsHandler",
            "error": str(ve)
        }, level="warning")
        return _response(400, {"error": str(ve)})

    except Exception as e:
        log_event("lambda_exception", {
            "source": "ExamResultsHandler"
        }, level="error", error=e)
        return _response(500, {"error": "Internal error processing exam results"})


def _response(status_code, body):
    """Generates the HTTP response with Wix-compatible CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,POST"
        },
        "body": json.dumps(body)
    }