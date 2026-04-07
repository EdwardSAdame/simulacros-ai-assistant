# src/lambda_audio_token_handler.py

import json
import logging
import boto3
import os
import requests
from src.config.settings import settings

# 🟢 NEW IMPORT: Import the dynamic function instead of the static dictionary
from src.config.audio_config import get_audio_profile

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
            
        # 🟢 FIX: Differentiate between the Audio Profile and the AI Tier.
        # We fall back to checking 'mode' for the profile to preserve backwards compatibility with your frontend.
        profile_name = body_data.get('profile_name', body_data.get('mode', 'transcription'))
        
        # 🟢 NEW: Extract the AI Tier (alpha/omega). 
        # (Make sure your Wix frontend includes 'ai_mode' or 'tier' in the WebSocket payload)
        ai_tier = body_data.get('ai_mode', body_data.get('tier', 'omega'))
        
        # 🟢 NEW: Safely get the dynamic profile based on both the requested audio type and the user's tier
        profile = get_audio_profile(profile_name, ai_tier)
        if not profile:
            logger.warning(f"Profile {profile_name} not found. Falling back to transcription/omega.")
            profile = get_audio_profile('transcription', 'omega')
        
        logger.info(f"Received token request from {connection_id} for profile: {profile_name} at tier: {ai_tier}")

        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in backend")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        if profile_name == 'language_tutor':
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
            
            payload = {
                "input_audio_format": "pcm16",
                "input_audio_transcription": {
                    # 🟢 Pulled dynamically! This will be the Alpha or Omega model depending on ai_tier
                    "model": profile.get("model", "gpt-4o-mini-transcribe") 
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": float(profile.get("vad_threshold", 0.5)),
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": int(profile.get("silence_duration_ms", 2000))
                }
            }

        logger.info(f"Targeting OpenAI URL: {target_url} with model: {payload.get('input_audio_transcription', {}).get('model', payload.get('model'))}")
        
        response = requests.post(target_url, headers=headers, json=payload)
        
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
            "mode": profile_name # Keep returning the requested profile_name back to the client
        }
        
        apigw_management_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(response_data)
        )
        
        return {'statusCode': 200, 'body': f'Token generated for profile: {profile_name}'}

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