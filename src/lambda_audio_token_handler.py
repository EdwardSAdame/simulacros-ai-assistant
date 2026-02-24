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
    Realtime session token. Supports 'transcription' and 'language_tutor' modes.
    """
    connection_id = event.get('requestContext', {}).get('connectionId')
    if not connection_id:
        logger.error("No connectionId in event")
        return {'statusCode': 400}

    try:
        # 1. Parse the incoming body to determine the mode
        body_str = event.get('body', '{}')
        try:
            body_data = json.loads(body_str)
        except json.JSONDecodeError:
            body_data = {}
            
        # Default to "transcription" to protect existing functionality
        mode = body_data.get('mode', 'transcription')
        
        logger.info(f"Received token request from {connection_id} for mode: {mode}")

        # 2. Get OpenAI API Key
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in backend")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 3. Dynamically build the payload based on the mode
        if mode == "language_tutor":
            # --- SPEECH-TO-SPEECH (LANGUAGE TUTOR) ---
            payload = {
                "model": "gpt-4o-realtime-preview-2024-12-17",  # Newer model recommended for voice agents
                "modalities": ["audio", "text"],
                "voice": "alloy",  # The AI must have a voice to speak back
                "instructions": (
                    "You are a friendly, encouraging language tutor. "
                    "Help the user practice speaking a foreign language. "
                    "Respond conversationally, correct major mistakes gently, and keep your answers concise to encourage the user to speak more. "
                    "If they ask you to speak in a specific language, seamlessly switch to that language."
                ),
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 1000,
                    "silence_duration_ms": 800  # 800ms gives language learners time to think
                },
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16"
            }
        else:
            # --- TRANSCRIPTION (LEGACY / DEFAULT) ---
            # Kept exactly as your original code
            payload = {
                "model": "gpt-4o-realtime-preview-2024-10-01",
                "modalities": ["audio", "text"],
                "instructions": (
                    "You are a professional transcriber. "
                    "Transcribe the user's speech accurately and quickly. "
                    "If the audio is a fragment, do your best to punctuate it logically."
                ),
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 1000,
                    "silence_duration_ms": 500   
                },
                "input_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                }
            }

        # 4. Make the POST request to OpenAI
        response = requests.post(OPENAI_TOKEN_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            logger.error(f"OpenAI Error: {response.text}")
            raise ValueError(f"OpenAI returned status {response.status_code}")
        
        data = response.json()
        
        # 5. Extract client_secret safely
        client_secret_data = data.get("client_secret", {})
        if isinstance(client_secret_data, dict):
            client_secret = client_secret_data.get("value")
        else:
            client_secret = client_secret_data

        if not client_secret:
            raise ValueError("OpenAI did not return a client_secret")

        # 6. Send the token back to the frontend
        response_data = {
            "action": "session_token",
            "token": client_secret,
            "mode": mode  # Return the mode so frontend knows the setup
        }
        
        apigw_management_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(response_data)
        )
        
        return {'statusCode': 200, 'body': f'Token generated for mode: {mode}.'}

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