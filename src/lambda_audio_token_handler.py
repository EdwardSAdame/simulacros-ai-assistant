import json
import logging
import boto3
import os
import requests
from src.config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get API Gateway endpoint URL from environment variables
APIGW_ENDPOINT_URL = os.environ.get('APIGW_AUDIO_ENDPOINT_URL')
if not APIGW_ENDPOINT_URL:
    logger.error("Missing APIGW_AUDIO_ENDPOINT_URL environment variable!")
    
apigw_management_client = boto3.client(
    'apigatewaymanagementapi',
    endpoint_url=APIGW_ENDPOINT_URL
)

# Standard Realtime Sessions endpoint
OPENAI_TOKEN_URL = "https://api.openai.com/v1/realtime/sessions"

def handler(event, context):
    """
    Handles a 'request_token' action by generating an ephemeral OpenAI
    Realtime session token with LIGHTNING FAST settings.
    """
    connection_id = event.get('requestContext', {}).get('connectionId')
    if not connection_id:
        logger.error("No connectionId in event")
        return {'statusCode': 400}

    logger.info(f"Received token request from {connection_id}")

    try:
        # 1. Get OpenAI API Key
        api_key = settings.OPENAI_API_KEY
        
        # Use the preview model for best performance
        model_name = "gpt-4o-realtime-preview-2024-10-01" 

        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in backend")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 2. Define the session payload
        payload = {
            "model": model_name,
            "modalities": ["audio", "text"],
            
            # Instructions help mitigate fragmentation by forcing context awareness
            "instructions": (
                "You are a professional transcriber. "
                "Transcribe the user's speech accurately and quickly. "
                "If the audio is a fragment, do your best to punctuate it logically."
            ),
            
            # --- LIGHTNING FAST CONFIGURATION ---
            "turn_detection": {
                "type": "server_vad",
                
                # 0.5 is more sensitive. It keeps the turn alive during soft speech/short pauses.
                "threshold": 0.5,
                
                # 1000ms buffer ensures the FIRST word (e.g., "Roma") is never lost.
                # This does NOT slow down the response; it just sends more past audio.
                "prefix_padding_ms": 1000,
                
                # 500ms wait time. 
                # This makes the AI respond INSTANTLY (0.5s) after you stop speaking.
                # TRADE-OFF: You must speak fluidly. If you pause > 0.5s, it will cut you off.
                "silence_duration_ms": 500   
            },
            "input_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "whisper-1"
            }
        }

        # 3. Make the POST request to OpenAI
        response = requests.post(OPENAI_TOKEN_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            logger.error(f"OpenAI Error: {response.text}")
            raise ValueError(f"OpenAI returned status {response.status_code}")
        
        data = response.json()
        
        # Extract client_secret
        client_secret = data.get("client_secret", {}).get("value")
        if not client_secret:
            client_secret = data.get("client_secret")

        if not client_secret:
            raise ValueError("OpenAI did not return a client_secret")

        # 4. Send the token back to the frontend
        response_data = {
            "action": "session_token",
            "token": client_secret
        }
        
        apigw_management_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(response_data)
        )
        
        return {'statusCode': 200, 'body': 'Token generated.'}

    except Exception as e:
        logger.error(f"Internal error: {e}", exc_info=True)
        try:
            apigw_management_client.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({"action": "error", "message": "Failed to generate AI token."})
            )
        except Exception:
            pass 
        return {'statusCode': 500, 'body': 'Internal server error.'}