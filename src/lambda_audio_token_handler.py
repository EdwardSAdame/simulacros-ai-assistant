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

APIGW_ENDPOINT_URL = os.environ.get('APIGW_AUDIO_ENDPOINT_URL')
apigw_client = boto3.client('apigatewaymanagementapi', endpoint_url=APIGW_ENDPOINT_URL) if APIGW_ENDPOINT_URL else None

def handler(event, context):
    set_invocation_context(context)

    connection_id = event.get('requestContext', {}).get('connectionId')
    if not connection_id:
        return {'statusCode': 400, 'body': 'connectionId not found'}

    try:
        try:
            body_data = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            body_data = {}
            
        profile_name = body_data.get('profile_name', body_data.get('mode', 'transcription'))
        ai_tier = body_data.get('ai_mode', body_data.get('tier', 'omega'))
        
        profile = get_audio_profile(profile_name, ai_tier)
        if not profile:
            profile = get_audio_profile('transcription', 'omega')

        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in backend")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        target_url = "https://api.openai.com/v1/realtime/client_secrets"
        
        if profile_name == 'language_tutor':
            session_config = {
                "model": profile.get("model"),
                "type": "realtime",
                "instructions": profile.get("instructions", "You are a helpful assistant."),
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": float(profile.get("vad_threshold", 0.5)),
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": int(profile.get("silence_duration_ms", 500))
                        },
                        # 🟢 THE FIX: Whisper transcription enabled to unlock the UI saving logic!
                        "transcription": {
                            "model": "whisper-1"
                        }
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "voice": profile.get("voice")
                    }
                }
            }
        else:
            session_config = {
                "model": profile.get("model"),
                "type": "realtime",
                "output_modalities": ["text"],
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
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

        response = requests.post(target_url, headers=headers, json={"session": session_config})
        
        if response.status_code != 200:
            log_event("openai_realtime_api_error", {"status_code": response.status_code, "error": response.text}, level="error")
            if apigw_client:
                apigw_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({"action": "error", "message": "Failed to connect to AI audio provider."})
                )
            return {'statusCode': 400, 'body': 'OpenAI rejected request'}
        
        client_secret = response.json().get("value")
        if not client_secret:
            raise ValueError("OpenAI did not return a valid ephemeral token.")

        if apigw_client:
            apigw_client.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "action": "session_token",
                    "token": client_secret,
                    "mode": profile_name 
                })
            )
        
        log_event("audio_token_generated", {"profile": profile_name, "tier": ai_tier})
        return {'statusCode': 200, 'body': 'Token generated successfully'}

    except Exception as error:
        log_event("audio_token_exception", {"error": str(error)}, level="error")
        if apigw_client:
            try:
                apigw_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({"action": "error", "message": "Internal server error connecting to audio."})
                )
            except Exception:
                pass
        return {'statusCode': 500, 'body': 'Internal server error'}