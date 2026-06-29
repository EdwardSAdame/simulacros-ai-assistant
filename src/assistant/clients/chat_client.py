# src/assistant/clients/chat_client.py
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
from src.config.tools_config import get_custom_tools
from src.services.admission_service import query_admission_data

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
            BaseAssistantClient.inject_pdf_inputs(api_input, pdf_urls)

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
        enable_image_generation: bool = True
    ) -> Generator[Any, None, None]:
        
        client = get_openai_client()
        cfg = get_model_config(mode)
        
        system_text = system_instruction or build_runtime_signals(
            user_id, page, name, email, requires_visuals=False, intent="chat"
        )
            
        api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
        api_input.extend(conversation_input)

        tools = get_custom_tools()
        
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

        tool_name = None
        tool_call_id = ""
        tool_args_buffer = ""
        
        pending_tool_calls = []

        try:
            stream = client.responses.create(**req)
            
            for event in stream:
                event_type = getattr(event, "type", "")
                
                if event_type == "response.completed":
                    resp_obj = getattr(event, "response", event)
                    usage_obj = getattr(resp_obj, "usage", None)
                    if usage_obj is not None:
                        yield {"type": "usage_metrics", "data": BaseAssistantClient.extract_usage_metrics(usage_obj)}

                if event_type == "response.output_text.delta":
                    yield event
                    
                elif event_type == "response.output_item.added":
                    item = getattr(event, "item", None)
                    if item and getattr(item, "type", "") == "function_call":
                        tool_name = getattr(item, "name", "")
                        tool_call_id = getattr(item, "call_id", "") or getattr(item, "id", "")
                        
                elif event_type == "response.function_call_arguments.delta":
                    tool_args_buffer += getattr(event, "delta", "")
                    
                elif event_type == "response.function_call_arguments.done":
                    item = getattr(event, "item", None)
                    if item:
                        tool_call_id = getattr(item, "call_id", "") or getattr(item, "id", "") or tool_call_id
                    
                    if tool_name == "query_admission_data":
                        pending_tool_calls.append({
                            "name": tool_name,
                            "id": tool_call_id,
                            "args": tool_args_buffer
                        })
                    
                    tool_name = None
                    tool_call_id = ""
                    tool_args_buffer = ""
                
                else:
                    yield event

            if pending_tool_calls:
                logger.info(f"Executing {len(pending_tool_calls)} parallel tool calls.")
                
                for tc in pending_tool_calls:
                    try:
                        args = json.loads(tc["args"])
                        tool_result = query_admission_data(
                            career=args.get("career"),
                            min_score=args.get("min_score"),
                            max_score=args.get("max_score"),
                            semester=args.get("semester"),
                            sort_by=args.get("sort_by"),
                            sort_order=args.get("sort_order"),
                            limit=args.get("limit")
                        )
                        
                        api_input.append({
                            "type": "function_call",
                            "call_id": tc["id"],
                            "name": tc["name"],
                            "arguments": tc["args"]
                        })
                        api_input.append({
                            "type": "function_call_output",
                            "call_id": tc["id"],
                            "output": tool_result
                        })
                    except Exception as e:
                        logger.error(f"Error executing tool {tc['name']}: {e}")
                        api_input.append({
                            "type": "function_call_output",
                            "call_id": tc["id"],
                            "output": json.dumps({"error": "Query execution failed."})
                        })
                
                req2 = BaseAssistantClient.build_request_payload(cfg, api_input, tools)
                req2["stream"] = True
                stream2 = client.responses.create(**req2)
                
                for event2 in stream2:
                    event_type2 = getattr(event2, "type", "")
                    
                    if event_type2 == "response.completed":
                        resp_obj2 = getattr(event2, "response", event2)
                        usage_obj2 = getattr(resp_obj2, "usage", None)
                        if usage_obj2 is not None:
                            yield {"type": "usage_metrics", "data": BaseAssistantClient.extract_usage_metrics(usage_obj2)}

                    if event_type2 == "response.output_text.delta":
                        yield event2

        except Exception as e:
            logger.error(f"Stream chat failed: {e}")
            raise e