import logging
import re
import json
from typing import List, Dict, Any, Tuple, Generator, Optional

from src.config.settings import (
    get_openai_client, 
    get_image_generation_size,
    get_image_generation_partials 
)
from src.config.model_config import get_model_config

from src.services.signal_service import build_runtime_signals
from src.assistant.artifact_handler import handle_generated_files
from src.utils.response_parser import extract_sources
from src.services.image_usage_service import ImageUsageService

from .base_client import BaseAssistantClient

logger = logging.getLogger(__name__)

class ChatClient:
    """
    Handles standard and streaming chat interactions with OpenAI.
    """

    @staticmethod
    def send_message_to_assistant(
        conversation_input: List[Dict[str, Any]], 
        user_id: str | None = None, 
        page: str | None = None, 
        name: str | None = None, 
        email: str | None = None, 
        mode: str = "omega",
        system_instruction: str | None = None,
        vector_store_ids: List[str] | None = None,
        requires_visuals: bool = False,
        web_search_config: Dict[str, Any] | None = None,
        user_location: Dict[str, str] | None = None,
        pdf_urls: List[str] | None = None,
        active_container_id: str | None = None,
        conversation_id: str | None = None 
    ) -> Tuple[str, List[str], List[Dict[str, str]], Dict[str, int], Optional[str]]:
        
        client = get_openai_client()
        cfg = get_model_config(mode)
        
        system_text = system_instruction or build_runtime_signals(
            user_id, page, name, email, exam_context="GENERAL", requires_visuals=requires_visuals, intent="chat"
        )
        api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
        api_input.extend(conversation_input)

        if pdf_urls:
            BaseAssistantClient.inject_pdf_inputs(api_input, pdf_urls, cfg.pdf_detail_level)

        tools = BaseAssistantClient.configure_tools(
            vector_store_ids, requires_visuals, False, pdf_urls, web_search_config, user_location, cfg, active_container_id
        )

        req = BaseAssistantClient.build_request_payload(cfg, api_input, tools)

        try:
            resp = client.responses.create(**req)
            
            text = getattr(resp, "output_text", None)
            output_list = getattr(resp, "output", []) or []
            
            if not text:
                chunks = []
                for item in output_list:
                    content_list = getattr(item, "content", []) or []
                    for c in content_list:
                        if getattr(c, "type", "") == "text": 
                            chunks.append(getattr(c, "text", ""))
                text = "\n".join(chunks).strip()
            
            if text: 
                text = re.sub(r'\[.*?\]\(sandbox:/mnt/data/.*?\)', '', text).strip()

            container_id = BaseAssistantClient.extract_container_id(output_list)

            generated_urls_map = handle_generated_files(client, resp, folder="chat_assets")
            
            if isinstance(generated_urls_map, dict) and user_id:
                creative_image_urls = [url for fname, url in generated_urls_map.items() if fname.startswith("creative_image_")]
                creative_image_count = len(creative_image_urls)
                
                if creative_image_count > 0:
                    try:
                        active_conversation = conversation_id if conversation_id else f"chat_{user_id[-6:]}"
                        image_tracker = ImageUsageService()
                        image_tracker.log_image_usage(
                            user_id=user_id,
                            conversation_id=active_conversation,
                            source="chat",  
                            tier=mode,
                            engine=cfg.image_model,
                            size=get_image_generation_size(),
                            quality=cfg.image_quality,
                            partials=get_image_generation_partials(),
                            image_count=creative_image_count,
                            image_url=creative_image_urls[0] if creative_image_urls else None
                        )
                    except Exception as track_err:
                        logger.error(f"Failed to log standard chat image usage: {track_err}")

            sources_list = extract_sources(resp)
            generated_urls = list(generated_urls_map.values()) if isinstance(generated_urls_map, dict) else generated_urls_map
            usage_data = BaseAssistantClient.extract_usage_metrics(getattr(resp, "usage", None))

            return (text or "[No response]", generated_urls, sources_list, usage_data, container_id)
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise e

    @staticmethod
    def stream_chat_response(
        conversation_input: List[Dict[str, Any]], 
        user_id: str | None = None, 
        page: str | None = None, 
        name: str | None = None, 
        email: str | None = None, 
        mode: str = "omega",
        system_instruction: str | None = None,
        enable_image_generation: bool = True,
        requires_web_search: bool = False
    ) -> Generator[Any, None, None]:
        
        client = get_openai_client()
        cfg = get_model_config(mode)
        
        system_text = system_instruction or build_runtime_signals(
            user_id, page, name, email, requires_visuals=False, intent="chat"
        )
            
        api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
        api_input.extend(conversation_input)

        web_search_config = {"scope": "open_web", "search_enabled": True} if requires_web_search else None
        
        tools = BaseAssistantClient.configure_tools(
            vector_store_ids=None,
            requires_visuals=False,
            code_interpreter_only=False,
            pdf_urls=None,
            web_search_config=web_search_config,
            user_location=None,
            model_config=cfg,
            active_container_id=None
        )
        
        if enable_image_generation:
            tools.append({
                "type": "image_generation",
                "model": cfg.image_model,
                "partial_images": get_image_generation_partials(), 
                "size": get_image_generation_size(),
                "quality": cfg.image_quality
            })

        req = BaseAssistantClient.build_request_payload(cfg, api_input, tools)
        req["stream"] = True

        try:
            stream = client.responses.create(**req)
            
            for event in stream:
                event_type = getattr(event, "type", "")
                
                if event_type == "response.completed":
                    resp_obj = getattr(event, "response", event)
                    usage_obj = getattr(resp_obj, "usage", None)
                    if usage_obj is not None:
                        yield {"type": "usage_metrics", "data": BaseAssistantClient.extract_usage_metrics(usage_obj)}

                else:
                    yield event

        except Exception as e:
            logger.error(f"Stream chat failed: {e}")
            raise e