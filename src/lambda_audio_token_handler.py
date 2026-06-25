# src/lambda_audio_token_handler.py

import json
import logging
import boto3
import os
import requests
from src.config.settings import settings
from src.config.audio_config import get_audio_profile
from src.utils.logging_utils import log_event, set_invocation_context

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

APIGW_ENDPOINT_URL = os.environ.get('APIGW_AUDIO_ENDPOINT_URL')
if APIGW_ENDPOINT_URL:
    apigw_management_client = boto3.client('apigatewaymanagementapi', endpoint_url=APIGW_ENDPOINT_URL)
else:
    logger.error("Missing APIGW_AUDIO_ENDPOINT_URL environment variable")

def handler(event, context):
    set_invocation_context(context)

    request_context = event.get('requestContext', {})
    connection_id = request_context.get('connectionId')
    
    if not connection_id:
        log_event("audio_token_failed", {"reason": "No connectionId in event"}, level="error")
        return {'statusCode': 400, 'body': 'connectionId not found'}

    try:
        body_str = event.get('body', '{}')
        try:
            body_data = json.loads(body_str)
        except json.JSONDecodeError:
            body_data = {}
            
        profile_name = body_data.get('profile_name', body_data.get('mode', 'transcription'))
        ai_tier = body_data.get('ai_mode', body_data.get('tier', 'omega'))
        
        profile = get_audio_profile(profile_name, ai_tier)
        if not profile:
            log_event("audio_profile_not_found", {"requested_profile": profile_name, "fallback": "transcription/omega"}, level="warning")
            profile = get_audio_profile('transcription', 'omega')
        
        log_event("audio_token_requested", {
            "connection_id": connection_id,
            "profile": profile_name,
            "tier": ai_tier
        })

        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in backend")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        target_url = "https://api.openai.com/v1/realtime/client_secrets"
        
        if profile_name == 'language_tutor':
            # 🟢 THE FIX: Everything properly nested inside audio.input per the GA docs
            session_config = {
                "model": profile.get("model", "gpt-4o-realtime-preview-2024-12-17"),
                "type": "realtime",
                "instructions": profile.get("instructions", "You are a helpful assistant."),
                "audio": {
                    "input": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": 24000
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": float(profile.get("vad_threshold", 0.5)),
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": int(profile.get("silence_duration_ms", 500))
                        }
                    },
                    "output": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": 24000
                        },
                        "voice": profile.get("voice", "alloy")
                    }
                }
            }
            payload = {"session": session_config}
                
        else:
            # 🟢 THE FIX: Standard transcription mode, using output_modalities to save tokens
            session_config = {
                "model": profile.get("model", "gpt-4o-mini-realtime-preview-2024-12-17"),
                "type": "realtime",
                "output_modalities": ["text"],
                "audio": {
                    "input": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": 24000
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": float(profile.get("vad_threshold", 0.5)),
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": int(profile.get("silence_duration_ms", 2000))
                        },
                        "transcription": {
                            "model": "whisper-1"
                        }
                    }
                }
            }
            payload = {"session": session_config}

        selected_model = payload.get("session", {}).get("model", "unknown")
        
        log_event("openai_realtime_api_call", {
            "target_url": target_url,
            "model": selected_model
        })
        
        response = requests.post(target_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            error_details = f"OpenAI API Error ({response.status_code}): {response.text}"
            log_event("openai_realtime_api_error", {"status_code": response.status_code, "error": response.text}, level="error")
            
            apigw_management_client.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({"action": "error", "message": error_details})
            )
            return {'statusCode': 400, 'body': 'OpenAI rejected request'}
        
        data = response.json()
        
        client_secret = data.get("value")
        
        if not client_secret:
            client_secret_data = data.get("client_secret", {})
            client_secret = client_secret_data.get("value") if isinstance(client_secret_data, dict) else client_secret_data

        if not client_secret:
            error_msg = f"OpenAI did not return a valid ephemeral token. Response: {data}"
            log_event("audio_token_missing", {"error": error_msg}, level="error")
            raise ValueError("OpenAI did not return a client_secret")

        response_data = {
            "action": "session_token",
            "token": client_secret,
            "mode": profile_name 
        }
        
        apigw_management_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(response_data)
        )
        
        log_event("audio_token_generated", {"profile": profile_name, "tier": ai_tier})
        
        return {'statusCode': 200, 'body': f'Token generated for profile: {profile_name}'}

    except Exception as error:
        log_event("audio_token_exception", {"error": str(error)}, level="error")
        try:
            if APIGW_ENDPOINT_URL:
                apigw_management_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({"action": "error", "message": f"Backend Exception: {str(error)}"})
                )
        except Exception as publish_error:
            log_event("failed_to_send_error_to_client", {"error": str(publish_error)}, level="error")
        return {'statusCode': 500, 'body': 'Internal server error'}