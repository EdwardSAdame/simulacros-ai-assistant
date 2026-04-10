import json
import logging
from src.services.purchase_service import process_purchase_webhook

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda entry point for Wix pricing plan purchase webhooks.
    """
    try:
        logger.info("Received purchase webhook event from API Gateway.")

        # API Gateway typically sends the payload in the 'body' field as a JSON string.
        # We use .get() to avoid KeyErrors if the event structure is unexpected.
        raw_body = event.get("body", "{}")
        
        # Safely parse the body into a Python dictionary
        if isinstance(raw_body, str):
            try:
                payload = json.loads(raw_body)
            except json.JSONDecodeError as parse_error:
                logger.error(f"Failed to parse JSON body: {str(parse_error)}")
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({"message": "Invalid JSON payload format"})
                }
        else:
            payload = raw_body

        logger.info("Successfully parsed webhook payload. Delegating to purchase service.")

        # Pass the parsed dictionary to the business logic layer
        result = process_purchase_webhook(payload)

        # Return a standardized API Gateway response
        return {
            "statusCode": result.get("statusCode", 200),
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"message": result.get("message", "Processed successfully")})
        }

    except Exception as e:
        logger.error(f"Critical unhandled error in lambda_purchase_handler: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"message": "Internal server error processing webhook"})
        }