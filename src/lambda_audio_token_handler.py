import json
import logging
import boto3
import os
import requests  # ❗ REMEMBER: Add 'requests' to your requirements.txt
from src.config.settings import settings # Imports your settings object

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get API Gateway endpoint URL from environment variables
# This must be set in your Lambda configuration
APIGW_ENDPOINT_URL = os.environ.get('APIGW_AUDIO_ENDPOINT_URL')
if not APIGW_ENDPOINT_URL:
    logger.error("Missing APIGW_AUDIO_ENDPOINT_URL environment variable!")
    # This is a critical failure, but we'll let it try to proceed
    # so the error appears in the apigatewaymanagementapi call
    
apigw_management_client = boto3.client(
    'apigatewaymanagementapi',
    endpoint_url=APIGW_ENDPOINT_URL
)

OPENAI_TOKEN_URL = "https://api.openai.com/v1/realtime/transcription_sessions"

def handler(event, context):
    """
    Handles a 'request_token' action by generating an ephemeral OpenAI
    transcription token and sending it back to the client.
    """
    connection_id = event.get('requestContext', {}).get('connectionId')
    if not connection_id:
        logger.error("No connectionId in event")
        return {'statusCode': 400}

    logger.info(f"Received token request from {connection_id}")

    try:
        # 1. Get OpenAI API Key from our settings
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in backend")

        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        # 2. Define the session payload (using the cheaper model)
        payload = {
            "input_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "gpt-4o-mini-transcribe"  # Using the cost-effective model
            },
            "turn_detection": {
                "type": "server_vad"
            },
            "input_audio_noise_reduction": {
                "type": "near_field"
            }
        }

        # 3. Make the POST request to OpenAI to get an ephemeral token
        response = requests.post(OPENAI_TOKEN_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()
        token = data.get("client_secret") # This is the ephemeral token

        if not token:
            raise ValueError("OpenAI did not return a client_secret")

        # 4. Send the token back to the frontend
        response_data = {
            "action": "session_token",
            "token": token
        }
        
        apigw_management_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(response_data)
        )
        
        return {'statusCode': 200, 'body': 'Token generated.'}

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to call OpenAI for token: {e}")
        # Send a descriptive error back to the client
        try:
            apigw_management_client.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({"action": "error", "message": "Failed to get token from provider."})
            )
        except Exception:
            pass # Ignore if we can't send error
        return {'statusCode': 502, 'body': 'Failed to get token from provider.'}
    
    except Exception as e:
        logger.error(f"Internal error: {e}")
        # Send a descriptive error back to the client
        try:
            apigw_management_client.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({"action": "error", "message": "Internal server error."})
            )
        except Exception:
            pass # Ignore if we can't send error
        return {'statusCode': 500, 'body': 'Internal server error.'}