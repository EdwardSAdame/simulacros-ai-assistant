# src/lambda_audio_token_handler.py

import json
import logging
import boto3
import os
import requests
from src.config.settings import settings
from src.config.audio_config import AUDIO_PROFILES

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

APIGW_ENDPOINT_URL = os.environ.get('APIGW_AUDIO_ENDPOINT_URL')
if APIGW_ENDPOINT_URL:
    apigw_management_client = boto3.client('apigatewaymanagementapi', endpoint_url=APIGW_ENDPOINT_URL)
else:
    logger.error("Missing APIGW_AUDIO_ENDPOINT_URL environment variable")

def handler(event, context):
    request_context = event.get('requestContext', {})
    connection_id = request_context.get('connectionId')
    
    if not connection_id:
        logger.error("No connectionId in event")
        return {'statusCode': 400, 'body': 'connectionId not found'}

    try:
        body_str = event.get('body', '{}')
        try:
            body_data = json.loads(body_str)
        except json.JSONDecodeError:
            body_data = {}
            
        mode = body_data.get('mode', 'transcription')
        
        # Safely get the profile or an empty dict fallback
        profile = AUDIO_PROFILES.get(mode, AUDIO_PROFILES.get('transcription', {}))
        
        logger.info(f"Received token request from {connection_id} for mode: {mode}")

        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in backend")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # --- CRITICAL FIX: Route dynamically based on the requested feature ---
        if mode == 'language_tutor':
            # --- SPEECH TO SPEECH (Conversational WebRTC API) ---
            target_url = "https://api.openai.com/v1/realtime/sessions"
            
            payload = {
                "model": profile.get("model", "gpt-4o-realtime-preview-2024-12-17"),
                "modalities": ["audio", "text"],
                "instructions": profile.get("instructions", "You are a helpful assistant."),
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": float(profile.get("vad_threshold", 0.5)),
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": int(profile.get("silence_duration_ms", 500))
                },
                "input_audio_format": "pcm16"
            }

            if profile.get("voice"):
                payload["voice"] = profile["voice"]
                payload["output_audio_format"] = "pcm16"
                
            if profile.get("requires_transcription_model"):
                payload["input_audio_transcription"] = {
                    "model": "whisper-1"
                }
                
        else:
            # --- SPEECH TO TEXT (Transcription WebSocket API) ---
            target_url = "https://api.openai.com/v1/realtime/transcription_sessions"
            
            # PERFECTED PAYLOAD: Nested EXACTLY as the OpenAI Docs request
            payload = {
                "input_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "gpt-4o-transcribe"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": float(profile.get("vad_threshold", 0.5)),
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": int(profile.get("silence_duration_ms", 500))
                }
            }

        logger.info(f"Targeting OpenAI URL: {target_url}")
        
        response = requests.post(target_url, headers=headers, json=payload)
        
        # --- NEW: SEND NATIVE OPENAI ERRORS TO FRONTEND IF IT FAILS ---
        if response.status_code != 200:
            error_details = f"OpenAI API Error ({response.status_code}): {response.text}"
            logger.error(error_details)
            apigw_management_client.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({"action": "error", "message": error_details})
            )
            return {'statusCode': 400, 'body': 'OpenAI rejected request'}
        
        data = response.json()
        client_secret_data = data.get("client_secret", {})
        client_secret = client_secret_data.get("value") if isinstance(client_secret_data, dict) else client_secret_data

        if not client_secret:
            raise ValueError("OpenAI did not return a client_secret")

        response_data = {
            "action": "session_token",
            "token": client_secret,
            "mode": mode
        }
        
        apigw_management_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(response_data)
        )
        
        return {'statusCode': 200, 'body': f'Token generated for mode: {mode}'}

    except Exception as error:
        logger.error(f"Internal error: {error}", exc_info=True)
        try:
            if APIGW_ENDPOINT_URL:
                apigw_management_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({"action": "error", "message": f"Backend Exception: {str(error)}"})
                )
        except Exception as publish_error:
            logger.error(f"Failed to send error to client: {publish_error}")
        return {'statusCode': 500, 'body': 'Internal server error'}