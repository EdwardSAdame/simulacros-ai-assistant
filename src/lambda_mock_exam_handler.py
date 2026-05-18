import json
import logging
from src.services.mock_exam_service import MockExamService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda entry point for fetching mock exams.
    Expects 'component' (and optionally 'examType') in the query string parameters or body.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # 1. Extract parameters safely
        params = event.get('queryStringParameters') or {}
        
        # Fallback to body if called via POST instead of GET
        if not params and event.get('body'):
            try:
                body_parsed = json.loads(event.get('body', '{}'))
                if isinstance(body_parsed, dict):
                    params = body_parsed
            except json.JSONDecodeError:
                pass

        exam_type = params.get('examType', 'icfes')
        component = params.get('component')

        # 2. Validate input
        if not component:
            logger.warning("Missing required parameter: component")
            return build_response(400, {'error': 'Missing required parameter: component'})

        # 3. Call internal service
        logger.info(f"Fetching exam for type: {exam_type}, component: {component}")
        message, exam_payload = MockExamService.get_random_exam(
            exam_type=exam_type, 
            component=component
        )

        # 4. Handle Service Failure (e.g., folder not found, no json files)
        if exam_payload is None:
            logger.error(f"Exam not found: {message}")
            return build_response(404, {'error': message})

        # 5. Return Success
        return build_response(200, {
            'message': message,
            'data': exam_payload
        })

    except Exception as e:
        logger.error(f"Unexpected error in lambda_mock_exam_handler: {str(e)}", exc_info=True)
        return build_response(500, {'error': 'Internal server error while fetching the exam.'})


def build_response(status_code: int, body: dict) -> dict:
    """
    Helper function to construct standard API Gateway HTTP responses with CORS headers.
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body)
    }