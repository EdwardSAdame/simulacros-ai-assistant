# src/assistant/assistant_client.py
import logging
import re
import json
from typing import List, Dict, Any, Tuple, Generator, Optional

# CONFIG & CLIENT 
from src.config.settings import get_openai_client, get_vector_search_max_results, get_code_interpreter_memory
from src.config.model_config import get_model_config
from src.schemas.quiz_schemas import QuizResponse

# NEW REFACTORED MODULES
from src.services.signal_service import build_runtime_signals
from src.assistant.artifact_handler import handle_generated_files, assign_urls_to_quiz
from src.utils.response_parser import extract_sources
from src.utils.stream_parser import StreamParser
from src.utils.quiz_utils import QuizUtils
from src.utils.logging_utils import log_event

# IMPORT OUR NEW FUNCTION CALLING ASSETS
from src.config.tools_config import get_custom_tools
from src.services.admission_service import query_admission_data

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# STANDARD CHAT
# ------------------------------------------------------------------
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
    pdf_urls: List[str] | None = None
) -> Tuple[str, List[str], List[Dict[str, str]], Dict[str, int]]:
    
    client = get_openai_client()
    cfg = get_model_config(mode)
    
    system_text = system_instruction or build_runtime_signals(
        user_id, page, name, email, exam_context="GENERAL", requires_visuals=requires_visuals, intent="chat"
    )
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    if pdf_urls:
        _inject_pdf_inputs(api_input, pdf_urls)

    tools = _configure_tools(vector_store_ids, requires_visuals, False, pdf_urls, web_search_config, user_location)

    req = _build_request_payload(cfg, api_input, tools)

    try:
        resp = client.responses.create(**req)
        
        text = getattr(resp, "output_text", None)
        if not text:
            chunks = []
            output_list = getattr(resp, "output", []) or []
            for item in output_list:
                content_list = getattr(item, "content", []) or []
                for c in content_list:
                    if getattr(c, "type", "") == "text": 
                        chunks.append(getattr(c, "text", ""))
            text = "\n".join(chunks).strip()
        
        if text: 
            text = re.sub(r'\[.*?\]\(sandbox:/mnt/data/.*?\)', '', text).strip()

        generated_urls_map = handle_generated_files(client, resp, folder="chat_assets")
        sources_list = extract_sources(resp)

        generated_urls = list(generated_urls_map.values()) if isinstance(generated_urls_map, dict) else generated_urls_map

        # Extract usage data
        usage_data = _extract_usage_metrics(getattr(resp, "usage", None))

        return (text or "[No response]", generated_urls, sources_list, usage_data)
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise e

# ------------------------------------------------------------------
# CHAT STREAMING (WITH PARALLEL TOOL CALLING INTERCEPTION)
# ------------------------------------------------------------------
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
            "partial_images": 3
        })

    req = _build_request_payload(cfg, api_input, tools)
    req["stream"] = True

    tool_name = None
    tool_call_id = ""
    tool_args_buffer = ""
    
    pending_tool_calls = []

    try:
        stream = client.responses.create(**req)
        
        for event in stream:
            if hasattr(event, "usage") and event.usage is not None:
                yield {"type": "usage_metrics", "data": _extract_usage_metrics(event.usage)}

            event_type = getattr(event, "type", "")
            
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
            
            req2 = _build_request_payload(cfg, api_input, tools)
            req2["stream"] = True
            stream2 = client.responses.create(**req2)
            
            for event2 in stream2:
                if hasattr(event2, "usage") and event2.usage is not None:
                    yield {"type": "usage_metrics", "data": _extract_usage_metrics(event2.usage)}

                if getattr(event2, "type", "") == "response.output_text.delta":
                    yield event2

    except Exception as e:
        logger.error(f"Stream chat failed: {e}")
        raise e

# ------------------------------------------------------------------
# QUIZ GENERATION (Standard)
# ------------------------------------------------------------------
def generate_structured_quiz(
    conversation_input: List[Dict[str, Any]], 
    user_id: str | None = None, 
    page: str | None = None, 
    name: str | None = None, 
    email: str | None = None, 
    mode: str = "omega",
    exam_context: str = "GENERAL",  
    requires_visuals: bool = False,
    requires_creative_images: bool = False,
    pdf_urls: List[str] | None = None,
    vector_store_ids: List[str] | None = None,
    web_search_config: Dict[str, Any] | None = None,
    user_location: Dict[str, str] | None = None,
    category: str = "general"
) -> Tuple[QuizResponse, Dict[str, int]]:
    
    client = get_openai_client()
    cfg = get_model_config(mode)
    
    system_text = build_runtime_signals(
        user_id, page, name, email, exam_context=exam_context, requires_visuals=requires_visuals, intent="quiz", category=category
    )
    
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    if pdf_urls:
        _inject_pdf_inputs(api_input, pdf_urls)

    tools = _configure_tools(vector_store_ids, False, False, pdf_urls, web_search_config, user_location)

    req = _build_request_payload(cfg, api_input, tools=tools)
    req["text_format"] = QuizResponse
    
    try:
        resp = client.responses.parse(**req)
        quiz = resp.output_parsed
        
        generated_urls = handle_generated_files(client, resp, folder="quiz_assets")
        assign_urls_to_quiz(quiz, generated_urls)
        
        if quiz and quiz.questions:
            for q in quiz.questions:
                QuizUtils.shuffle_options(q)

        usage_data = _extract_usage_metrics(getattr(resp, "usage", None))

        return (quiz, usage_data)
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise e

# ------------------------------------------------------------------
# QUIZ STREAMING (Refactored)
# ------------------------------------------------------------------
def stream_structured_quiz(
    conversation_input: List[Dict[str, Any]], 
    user_id: str | None = None, 
    page: str | None = None, 
    name: str | None = None, 
    email: str | None = None, 
    mode: str = "omega",
    exam_context: str = "GENERAL", 
    requires_visuals: bool = False,
    requires_creative_images: bool = False,
    pdf_urls: List[str] | None = None,
    vector_store_ids: List[str] | None = None,
    web_search_config: Dict[str, Any] | None = None,
    user_location: Dict[str, str] | None = None,
    category: str = "general"
) -> Generator[Dict[str, Any], None, None]:
    
    client = get_openai_client()
    cfg = get_model_config(mode)
    
    system_text = build_runtime_signals(
        user_id, page, name, email, exam_context=exam_context, requires_visuals=requires_visuals, intent="quiz", category=category
    )
    
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    if pdf_urls:
        _inject_pdf_inputs(api_input, pdf_urls)

    tools = _configure_tools(vector_store_ids, False, False, pdf_urls, web_search_config, user_location)

    req = _build_request_payload(cfg, api_input, tools=tools)
    req["text_format"] = QuizResponse
    
    streamed_questions = []

    try:
        with client.responses.stream(**req) as stream:
            parser_generator = StreamParser.parse_quiz_stream(stream)
            
            for event in parser_generator:
                if event["type"] == "question":
                    q_obj = event["data"]
                    QuizUtils.shuffle_options(q_obj)
                    streamed_questions.append(q_obj)
                    yield event
                
                elif event["type"] == "done":
                    final_parsed = event["full_response"]
                    
                    generated_urls = []
                    if hasattr(stream, 'get_final_response'):
                        final_raw = stream.get_final_response()
                        generated_urls = handle_generated_files(client, final_raw, folder="quiz_assets")
                        
                        usage_data = _extract_usage_metrics(getattr(final_raw, "usage", None))
                        if usage_data:
                            yield {"type": "usage_metrics", "data": usage_data}
                    
                    if final_parsed and hasattr(final_parsed, 'questions') and streamed_questions:
                        if len(final_parsed.questions) == len(streamed_questions):
                            final_parsed.questions = streamed_questions 
                        else:
                            for q in final_parsed.questions:
                                QuizUtils.shuffle_options(q)

                    if final_parsed and generated_urls:
                        assign_urls_to_quiz(final_parsed, generated_urls)

                    yield {"type": "done", "full_response": final_parsed}
                    
                else:
                    yield event

    except Exception as e:
        logger.error(f"Streaming failed: {e}")
        yield {"type": "error", "error": str(e)}

# ------------------------------------------------------------------
# INTERNAL HELPERS
# ------------------------------------------------------------------
def _extract_usage_metrics(usage_obj: Any) -> Dict[str, int]:
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

def _inject_pdf_inputs(api_input, pdf_urls):
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
         
    for url in pdf_urls:
        if url and isinstance(url, str) and url.startswith("http"):
            target_message["content"].append({
                "type": "input_file",
                "file_url": url
            })

def _configure_tools(vector_store_ids, requires_visuals, requires_creative_images, pdf_urls, web_search_config, user_location):
    tools = []
    if vector_store_ids:
        tools.append({"type": "file_search", "vector_store_ids": vector_store_ids, "max_num_results": get_vector_search_max_results()})
    
    if requires_visuals or (pdf_urls and len(pdf_urls) > 0):
        # Apply the dynamic memory setting
        memory_limit = get_code_interpreter_memory()
        tools.append({
            "type": "code_interpreter", 
            "container": {
                "type": "auto", 
                "memory_limit": memory_limit
            }
        })
        # Track standard chat container requests
        log_event("container_requested", {"context": "standard_chat", "memory_limit": memory_limit})
        
    if requires_creative_images:
        tools.append({
            "type": "image_generation",
            "partial_images": 3
        })
        
    if web_search_config:
        web_tool = {"type": "web_search"}
        if "allowed_domains" in web_search_config:
             web_tool["filters"] = {"allowed_domains": web_search_config["allowed_domains"]}
        if user_location: web_tool["user_location"] = user_location
        tools.append(web_tool)
    return tools

def _build_request_payload(cfg, api_input, tools):
    req = {"model": cfg.model, "input": api_input}
    is_reasoning = (cfg.model.startswith("o") and not cfg.model.startswith("gpt")) or "reasoning" in cfg.model
    
    if is_reasoning:
        if cfg.reasoning_effort: req["reasoning"] = {"effort": cfg.reasoning_effort}
    else:
        req["temperature"] = cfg.temperature
        req["top_p"] = cfg.top_p
    
    if tools: req["tools"] = tools
    
    return {k: v for k, v in req.items() if v is not None}