import json
import logging
from src.services.mock_exam_service import MockExamService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda entry point for fetching mock exams and catalogs.
    Expects an 'action' parameter ('get_catalog' or 'get_exam').
    For 'get_exam', expects 'component' and 'examId'.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # 1. Extract parameters safely (Supports GET and POST)
        params = event.get('queryStringParameters') or {}
        
        if not params and event.get('body'):
            try:
                body_parsed = json.loads(event.get('body', '{}'))
                if isinstance(body_parsed, dict):
                    params = body_parsed
            except json.JSONDecodeError:
                pass

        # 2. Extract routing variables
        action = params.get('action')
        exam_type = params.get('examType', 'icfes')

        # 3. Route to the correct service method based on 'action'
        if action == 'get_catalog':
            logger.info(f"Routing request to fetch catalog for type: {exam_type}")
            message, payload = MockExamService.get_catalog(exam_type=exam_type)

        elif action == 'get_exam':
            component = params.get('component')
            exam_id = params.get('examId')

            # Validation specifically for fetching an exam
            if not component or not exam_id:
                logger.warning("Missing required parameters for get_exam: component or examId")
                return build_response(400, {'error': 'Missing required parameters: component and examId are required.'})

            logger.info(f"Routing request to fetch specific exam: {exam_type} -> {component} -> {exam_id}")
            message, payload = MockExamService.get_specific_exam(
                exam_type=exam_type, 
                component=component,
                exam_id=exam_id
            )

        else:
            # Handle missing or invalid action parameter
            logger.warning(f"Invalid or missing action parameter: {action}")
            return build_response(400, {'error': "A valid 'action' parameter is required ('get_catalog' or 'get_exam')."})

        # 4. Handle Service Failure (e.g., file not found)
        if payload is None:
            logger.error(f"Operation failed: {message}")
            return build_response(404, {'error': message})

        # 5. Return Success
        return build_response(200, {
            'message': message,
            'data': payload
        })

    except Exception as e:
        logger.error(f"Unexpected error in lambda_mock_exam_handler: {str(e)}", exc_info=True)
        return build_response(500, {'error': 'Internal server error while processing the request.'})


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