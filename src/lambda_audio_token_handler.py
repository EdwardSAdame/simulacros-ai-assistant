# src/lambda_audio_token_handler.py
import json
import logging
import boto3
import os
import requests  # REMEMBER: Add 'requests' to your requirements.txt
from src.config.settings import settings # Imports your settings object

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

# 🔹 CHANGED: Use the standard Realtime Sessions endpoint to ensure full config support
OPENAI_TOKEN_URL = "https://api.openai.com/v1/realtime/sessions"

def handler(event, context):
    """
    Handles a 'request_token' action by generating an ephemeral OpenAI
    Realtime session token with tuned VAD and intelligence instructions.
    """
    connection_id = event.get('requestContext', {}).get('connectionId')
    if not connection_id:
        logger.error("No connectionId in event")
        return {'statusCode': 400}

    logger.info(f"Received token request from {connection_id}")

    try:
        # 1. Get OpenAI API Key
        api_key = settings.OPENAI_API_KEY
        
        # 🔹 TIP: For smart grammar correction, 'gpt-4o-realtime-preview-2024-10-01' is recommended
        # If your settings.OPENAI_AUDIO_MODEL is 'whisper-1', this might still work, 
        # but using the specific realtime model ensures 'instructions' are obeyed.
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
            
            # 🔹 CRITICAL FIX 1: Instructions for "Post-processing" on the fly
            # This tells the model to fix grammar/stuttering instantly.
            "instructions": (
                "You are a professional transcriber. "
                "Output the user's speech as clean, grammatically correct text. "
                "Fix stutters, partial words, and fragmented sentences into coherent thoughts. "
                "Do not respond to the user, just transcribe what they say."
            ),
            
            # 🔹 CRITICAL FIX 2: VAD Tuning to prevent chopping sentences
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.6,             # Slightly higher threshold to ignore background noise
                "prefix_padding_ms": 300,
                "silence_duration_ms": 1200   # WAIT 1.2 SECONDS of silence before finalizing the sentence
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
        
        # The ephemeral token is usually in 'client_secret' -> 'value' for /sessions
        client_secret = data.get("client_secret", {}).get("value")
        
        # Fallback if structure is flat (older API versions)
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
        # Send a descriptive error back to the client
        try:
            apigw_management_client.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({"action": "error", "message": "Failed to generate AI token."})
            )
        except Exception:
            pass 
        return {'statusCode': 500, 'body': 'Internal server error.'}