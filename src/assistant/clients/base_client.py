import logging
from typing import List, Dict, Any, Optional

from src.config.settings import (
    get_vector_search_max_results, 
    get_code_interpreter_memory,
    get_image_generation_size,
    get_image_generation_partials 
)
from src.utils.logging_utils import log_event

logger = logging.getLogger(__name__)

class BaseAssistantClient:
    """
    Provides foundational utilities for interacting with the OpenAI API.
    Handles payload construction, tool configuration, payload sanitization, and usage metric extraction.
    """

    @staticmethod
    def extract_container_id(output_list: List[Any]) -> Optional[str]:
        """Safely extracts the active container_id from a Code Interpreter call block."""
        for item in output_list:
            if getattr(item, "type", "") == "code_interpreter_call":
                cid = getattr(item, "container_id", None)
                if not cid and hasattr(item, "code_interpreter"):
                    cid = getattr(item.code_interpreter, "container_id", None)
                if not cid and hasattr(item, "code_interpreter_call"):
                    cid = getattr(item.code_interpreter_call, "container_id", None)
                if cid:
                    return cid
        return None

    @staticmethod
    def extract_usage_metrics(usage_obj: Any) -> Dict[str, int]:
        if not usage_obj:
            return {}

        if isinstance(usage_obj, dict):
            input_tokens = (
                usage_obj.get("input_tokens") or 
                usage_obj.get("prompt_tokens") or 
                usage_obj.get("promptTokens") or 
                usage_obj.get("prompt_token_count") or 0
            )
            output_tokens = (
                usage_obj.get("output_tokens") or 
                usage_obj.get("completion_tokens") or 
                usage_obj.get("completionTokens") or 
                usage_obj.get("candidates_token_count") or 0
            )
            total_tokens = (
                usage_obj.get("total_tokens") or 
                usage_obj.get("totalTokens") or 0
            )
            
            completion_details = usage_obj.get("output_tokens_details", usage_obj.get("completion_tokens_details", {}))
            reasoning_tokens = completion_details.get("reasoning_tokens", 0) if isinstance(completion_details, dict) else 0
            
            prompt_details = usage_obj.get("input_tokens_details", usage_obj.get("prompt_tokens_details", {}))
            cached_tokens = prompt_details.get("cached_tokens", 0) if isinstance(prompt_details, dict) else 0
            
        else:
            input_tokens = (
                getattr(usage_obj, "input_tokens", None) or 
                getattr(usage_obj, "prompt_tokens", None) or 
                getattr(usage_obj, "promptTokens", None) or 0
            )
            output_tokens = (
                getattr(usage_obj, "output_tokens", None) or 
                getattr(usage_obj, "completion_tokens", None) or 
                getattr(usage_obj, "completionTokens", None) or 0
            )
            total_tokens = (
                getattr(usage_obj, "total_tokens", None) or 
                getattr(usage_obj, "totalTokens", None) or 0
            )
            
            completion_details = getattr(usage_obj, "output_tokens_details", getattr(usage_obj, "completion_tokens_details", None))
            reasoning_tokens = getattr(completion_details, "reasoning_tokens", 0) if completion_details else 0
            
            prompt_details = getattr(usage_obj, "input_tokens_details", getattr(usage_obj, "prompt_tokens_details", None))
            cached_tokens = getattr(prompt_details, "cached_tokens", 0) if prompt_details else 0

        return {
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "total_tokens": int(total_tokens),
            "reasoning_tokens": int(reasoning_tokens),
            "cached_tokens": int(cached_tokens)
        }

    @staticmethod
    def sanitize_input_content(api_input: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensures input structures match OpenAI API specifications.
        Flattens legacy image_url structures to conform to the Responses API payload.
        """
        for message in api_input:
            if "content" in message and isinstance(message["content"], list):
                for content_part in message["content"]:
                    if content_part.get("type") in ["image_url", "input_image"]:
                        content_part["type"] = "input_image"
                        img_url_data = content_part.get("image_url")
                        if isinstance(img_url_data, dict) and "url" in img_url_data:
                            content_part["image_url"] = img_url_data["url"]
        return api_input

    @staticmethod
    def _is_image_url(url: str) -> bool:
        """
        Determines whether a given URL points to a standard image file based on extension.
        """
        image_extensions = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".tiff")
        clean_url = url.split("?")[0].lower()
        return any(clean_url.endswith(ext) for ext in image_extensions)

    @staticmethod
    def inject_file_inputs(api_input: List[Dict[str, Any]], attachments: List[Any], detail_level: str = "high") -> None:
        """
        Injects user attachments into the message array, routing standard images as input_image
        and non-image document files as input_file according to API specifications.
        Supports URLs, File IDs, and Base64 data.
        """
        target_message = None
        if api_input and api_input[-1].get("role") == "user":
            target_message = api_input[-1]
        else:
            target_message = {"role": "user", "content": []}
            api_input.append(target_message)
        
        current_content = target_message.get("content")
        if isinstance(current_content, str):
            target_message["content"] = [{"type": "input_text", "text": current_content}]
        elif current_content is None:
            target_message["content"] = []
             
        valid_file_count = 0
        valid_image_count = 0

        for item in attachments:
            url = None
            file_id = None
            file_data = None
            
            if isinstance(item, dict):
                url = item.get("url")
                file_id = item.get("file_id")
                file_data = item.get("file_data")
            elif isinstance(item, str):
                if item.startswith("http"):
                    url = item
                elif item.startswith("file-"):
                    file_id = item
                elif item.startswith("data:"):
                    file_data = item
            
            if url:
                if BaseAssistantClient._is_image_url(url):
                    target_message["content"].append({
                        "type": "input_image",
                        "image_url": url.strip()
                    })
                    valid_image_count += 1
                else:
                    target_message["content"].append({
                        "type": "input_file",
                        "file_url": url.strip(),
                        "detail": detail_level
                    })
                    valid_file_count += 1
            elif file_id:
                target_message["content"].append({
                    "type": "input_file",
                    "file_id": file_id.strip(),
                    "detail": detail_level
                })
                valid_file_count += 1
            elif file_data:
                target_message["content"].append({
                    "type": "input_file",
                    "filename": item.get("filename", "upload.pdf") if isinstance(item, dict) else "upload.pdf",
                    "file_data": file_data.strip(),
                    "detail": detail_level
                })
                valid_file_count += 1

        log_event("file_inputs_injected", {
            "file_count": valid_file_count,
            "image_count": valid_image_count,
            "detail_level": detail_level
        })

    @staticmethod
    def configure_tools(
        vector_store_ids: Optional[List[str]] = None, 
        requires_visuals: bool = False, 
        requires_creative_images: bool = False, 
        attachments: Optional[List[Any]] = None, 
        web_search_config: Optional[Dict[str, Any]] = None, 
        user_location: Optional[str] = None, 
        cfg: Any = None, 
        active_container_id: Optional[str] = None,
        code_interpreter_only: bool = False,
        model_config: Any = None
    ) -> List[Dict[str, Any]]:
        tools = []
        active_cfg = cfg or model_config

        if code_interpreter_only:
            memory_limit = get_code_interpreter_memory()
            container_config = active_container_id if active_container_id else {"type": "auto", "memory_limit": memory_limit}
            tools.append({
                "type": "code_interpreter", 
                "container": container_config
            })
            log_event("container_requested", {
                "context": "forced_code_interpreter", 
                "memory_limit": memory_limit,
                "explicit_id": active_container_id
            })
            return tools

        if vector_store_ids:
            tools.append({"type": "file_search", "vector_store_ids": vector_store_ids, "max_num_results": get_vector_search_max_results()})
        
        if requires_visuals or (attachments and len(attachments) > 0):
            memory_limit = get_code_interpreter_memory()
            container_config = active_container_id if active_container_id else {"type": "auto", "memory_limit": memory_limit}

            tools.append({
                "type": "code_interpreter", 
                "container": container_config
            })
            
            log_event("container_requested", {
                "context": "chat", 
                "memory_limit": memory_limit,
                "explicit_id": active_container_id
            })
            
        if requires_creative_images and active_cfg:
            tools.append({
                "type": "image_generation",
                "action": "generate",
                "model": getattr(active_cfg, "image_model", "gpt-image-2"),
                "partial_images": get_image_generation_partials(),
                "size": get_image_generation_size(),
                "quality": getattr(active_cfg, "image_quality", "auto")
            })
            
        if web_search_config:
            web_tool = {"type": "web_search"}
            if "allowed_domains" in web_search_config:
                 web_tool["filters"] = {"allowed_domains": web_search_config["allowed_domains"]}
            if user_location: web_tool["user_location"] = user_location
            tools.append(web_tool)
            
        return tools

    @staticmethod
    def build_request_payload(cfg, api_input, tools) -> Dict[str, Any]:
        sanitized_input = BaseAssistantClient.sanitize_input_content(api_input)
        req = {"model": cfg.model, "input": sanitized_input}
        
        is_reasoning = (
            cfg.model.startswith("o") or 
            cfg.model.startswith("gpt-5") or 
            "reasoning" in cfg.model or
            (cfg.reasoning_effort is not None and cfg.reasoning_effort.lower() != "none")
        )
        
        if is_reasoning:
            if cfg.reasoning_effort: 
                req["reasoning"] = {"effort": cfg.reasoning_effort}
        else:
            req["temperature"] = cfg.temperature
            req["top_p"] = cfg.top_p
        
        if tools: 
            req["tools"] = tools
        
        return {k: v for k, v in req.items() if v is not None}