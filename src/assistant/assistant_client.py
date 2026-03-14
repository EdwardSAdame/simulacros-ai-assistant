# src/assistant/assistant_client.py
import logging
import re
from typing import List, Dict, Any, Tuple, Generator

# CONFIG & CLIENT
from src.config.settings import get_openai_client, get_vector_search_max_results
from src.config.model_config import get_model_config
from src.schemas.quiz_schemas import QuizResponse
from src.config.creative_image_instructions import get_creative_image_system_prompt

# NEW REFACTORED MODULES
from src.services.signal_service import build_runtime_signals
from src.assistant.artifact_handler import handle_generated_files, assign_urls_to_quiz
from src.utils.response_parser import extract_sources
from src.utils.stream_parser import StreamParser
from src.utils.quiz_utils import QuizUtils

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
) -> Tuple[str, List[str], List[Dict[str, str]]]:
    
    client = get_openai_client()
    cfg = get_model_config(mode)
    
    # 1. Build System Signal
    system_text = system_instruction or build_runtime_signals(
        user_id, page, name, email, exam_context="ICFES", requires_visuals=requires_visuals
    )
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    # 2. Inject PDFs
    if pdf_urls:
        _inject_pdf_inputs(api_input, pdf_urls)

    # 3. Configure Tools
    tools = _configure_tools(vector_store_ids, requires_visuals, pdf_urls, web_search_config, user_location)

    # 4. Build Request
    req = _build_request_payload(cfg, api_input, tools)

    try:
        resp = client.responses.create(**req)
        
        # 5. Process Text
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

        # 6. Process Artifacts & Sources (Delegated)
        generated_urls_map = handle_generated_files(client, resp, folder="chat_assets")
        sources_list = extract_sources(resp)

        # Extract only the S3 URLs (values) from the dictionary and convert to a list
        generated_urls = list(generated_urls_map.values()) if isinstance(generated_urls_map, dict) else generated_urls_map

        return (text or "[No response]", generated_urls, sources_list)
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise e

# ------------------------------------------------------------------
# CHAT STREAMING (WITH IMAGE GENERATION)
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
    
    base_system_text = system_instruction or build_runtime_signals(
        user_id, page, name, email, requires_visuals=False
    )
    
    if enable_image_generation:
        brand_instruction = get_creative_image_system_prompt()
        system_text = f"{base_system_text}\n\n{brand_instruction}"
    else:
        system_text = base_system_text
        
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    tools = []
    if enable_image_generation:
        tools.append({
            "type": "image_generation",
            "partial_images": 3
        })

    req = _build_request_payload(cfg, api_input, tools)
    req["stream"] = True

    try:
        stream = client.responses.create(**req)
        for event in stream:
            yield event
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
    exam_context: str = "ICFES",
    requires_visuals: bool = False,
    pdf_urls: List[str] | None = None,
    vector_store_ids: List[str] | None = None,
    web_search_config: Dict[str, Any] | None = None,
    user_location: Dict[str, str] | None = None
) -> QuizResponse:
    
    client = get_openai_client()
    cfg = get_model_config(mode)
    
    system_text = build_runtime_signals(
        user_id, page, name, email, exam_context=exam_context, requires_visuals=requires_visuals
    )
    
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    if pdf_urls:
        _inject_pdf_inputs(api_input, pdf_urls)

    # Dynamic Tool Configuration using helper
    tools = _configure_tools(vector_store_ids, requires_visuals, pdf_urls, web_search_config, user_location)

    req = _build_request_payload(cfg, api_input, tools=tools)
    req["text_format"] = QuizResponse
    
    try:
        resp = client.responses.parse(**req)
        quiz = resp.output_parsed
        
        # Artifact Handling
        generated_urls = handle_generated_files(client, resp, folder="quiz_assets")
        assign_urls_to_quiz(quiz, generated_urls)
        
        if quiz and quiz.questions:
            for q in quiz.questions:
                QuizUtils.shuffle_options(q)

        return quiz
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
    exam_context: str = "ICFES",
    requires_visuals: bool = False,
    pdf_urls: List[str] | None = None,
    vector_store_ids: List[str] | None = None,
    web_search_config: Dict[str, Any] | None = None,
    user_location: Dict[str, str] | None = None
) -> Generator[Dict[str, Any], None, None]:
    
    client = get_openai_client()
    cfg = get_model_config(mode)
    
    system_text = build_runtime_signals(
        user_id, page, name, email, exam_context=exam_context, requires_visuals=requires_visuals
    )
    
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    if pdf_urls:
        _inject_pdf_inputs(api_input, pdf_urls)

    # Dynamic Tool Configuration using helper
    tools = _configure_tools(vector_store_ids, requires_visuals, pdf_urls, web_search_config, user_location)

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
                    
                    # Handle Artifacts on Stream Completion
                    generated_urls = []
                    if hasattr(stream, 'get_final_response'):
                        final_raw = stream.get_final_response()
                        generated_urls = handle_generated_files(client, final_raw, folder="quiz_assets")
                    
                    if final_parsed and hasattr(final_parsed, 'questions') and streamed_questions:
                        # Sync streamed questions with final object
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
def _inject_pdf_inputs(api_input, pdf_urls):
    """Mutates api_input to attach PDF files."""
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

def _configure_tools(vector_store_ids, requires_visuals, pdf_urls, web_search_config, user_location):
    tools = []
    if vector_store_ids:
        tools.append({"type": "file_search", "vector_store_ids": vector_store_ids, "max_num_results": get_vector_search_max_results()})
    
    if requires_visuals or (pdf_urls and len(pdf_urls) > 0):
        tools.append({"type": "code_interpreter", "container": {"type": "auto"}})
        
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