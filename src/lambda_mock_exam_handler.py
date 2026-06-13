import json
import logging
from src.services.mock_exam_service import MockExamService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda entry point for generating dynamic mock exam catalogs.
    Expects an 'action' parameter equal to 'get_catalog'.
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
            logger.info(f"Routing request to fetch dynamic catalog for type: {exam_type}")
            message, payload = MockExamService.get_catalog(exam_type=exam_type)
        else:
            # Handle missing or invalid action parameter
            logger.warning(f"Invalid or missing action parameter: {action}")
            return build_response(400, {'error': "A valid 'action' parameter is required (must be 'get_catalog')."})

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