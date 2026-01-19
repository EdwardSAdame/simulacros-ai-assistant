# src/assistant/assistant_client.py
from typing import List, Dict, Any, Tuple, Generator
import logging
import re

# 🔹 Standard Imports
from src.config.settings import get_openai_client, get_vector_search_max_results
from src.config.model_config import get_model_config
from src.config.system_instructions import build_system_instructions
# 🟢 NEW IMPORT: Visual Guidelines
from src.config.visual_instructions import build_visual_instructions
from src.utils.time_utils import get_current_time_info, infer_target_semester
from src.schemas.quiz_schemas import QuizResponse

# 🔹 Modular Services
from src.services.ai_assets_service import ai_assets_service
from src.utils.stream_parser import StreamParser
from src.utils.quiz_utils import QuizUtils

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 🔹 HELPER: Context & Signal Builders
# ------------------------------------------------------------------
def _build_runtime_signals(
    user_id: str | None, 
    page: str | None, 
    name: str | None, 
    email: str | None, 
    exam_context: str = "ICFES",
    requires_visuals: bool = False  # 🟢 NEW PARAMETER
) -> str:
    """Generates the dynamic system context for the AI."""
    tinfo = get_current_time_info()
    target = infer_target_semester()
    
    signals = [
        f"Today is {tinfo['full_human']}.",
        f"Page: {page or '/'}",
        f"User: {user_id or 'Guest'}",
        f"Target: {target}",
        f"Context: {exam_context}",
        f"Sources: Invicto Knowledge Base."
    ]

    # 🟢 CONDITIONAL INJECTION: Only if visuals are required
    if requires_visuals:
        visuals_trigger = (
            "VISUALS: Use the 'python' tool (Code Interpreter) to AUTOMATICALLY GENERATE PLOTS for any request involving "
            "mathematical functions, geometry, or data trends. Do not just describe the graph—DRAW IT. Output the file."
        )
        visual_style_guide = build_visual_instructions()
        signals.append(visuals_trigger)
        signals.append(visual_style_guide)

    if name: signals.append(f"Name: {name}.")
    if email: signals.append(f"Email: {email}.")
    
    return build_system_instructions(extras=signals, exam_context=exam_context)

def _assign_urls_to_quiz(quiz_data: QuizResponse, urls: List[str]):
    """Binds generated image URLs to quiz questions."""
    if not urls or not quiz_data: return
    idx = 0
    for q in quiz_data.questions:
        if q.image_url == "PENDING_UPLOAD" or (q.image_url and "/mnt/" in q.image_url) or (not q.image_url and idx < len(urls)):
            if idx < len(urls):
                q.image_url = urls[idx]
                idx += 1

def _extract_sources(response_obj: Any) -> List[Dict[str, str]]:
    """Extracts citations from the OpenAI response object."""
    sources = []
    try:
        output_items = getattr(response_obj, "output", []) or []
        for item in output_items:
            if getattr(item, "type", "") == "message":
                content_list = getattr(item, "content", []) or []
                for part in content_list:
                    annotations = getattr(part, "annotations", []) or []
                    for ann in annotations:
                        if getattr(ann, "type", "") == "url_citation":
                            url = getattr(ann, "url", None)
                            title = getattr(ann, "title", "Fuente")
                            if url: sources.append({"title": title, "url": url})
    except Exception as e:
        logger.error(f"Error extracting sources: {e}")
    
    unique_sources = []
    seen_urls = set()
    for s in sources:
        if s["url"] not in seen_urls:
            unique_sources.append(s)
            seen_urls.add(s["url"])
    return unique_sources

# ------------------------------------------------------------------
# 🟢 STANDARD CHAT
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
    user_location: Dict[str, str] | None = None 
) -> Tuple[str, List[str], List[Dict[str, str]]]:
    
    client = get_openai_client()
    cfg = get_model_config(mode)
    target_model = cfg.model
    active_temp, active_top_p = cfg.temperature, cfg.top_p
    active_effort = cfg.reasoning_effort
    
    # 2. Build Inputs
    system_text = system_instruction or _build_runtime_signals(
        user_id, page, name, email, exam_context="ICFES", requires_visuals=requires_visuals
    )
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    # 3. Configure Tools
    tools = []
    if vector_store_ids:
        tools.append({"type": "file_search", "vector_store_ids": vector_store_ids, "max_num_results": get_vector_search_max_results()})
    
    # 🟢 CONDITIONAL TOOL: Only attach Code Interpreter if needed
    if requires_visuals:
        tools.append({"type": "code_interpreter", "container": {"type": "auto"}})
        
    if web_search_config:
        web_tool = {"type": "web_search"}
        if "allowed_domains" in web_search_config:
             web_tool["filters"] = {"allowed_domains": web_search_config["allowed_domains"]}
        if user_location: web_tool["user_location"] = user_location
        tools.append(web_tool)

    # 4. Build Request
    req = {"model": target_model, "input": api_input}
    is_reasoning = (target_model.startswith("o") and not target_model.startswith("gpt")) or "reasoning" in target_model
    
    if is_reasoning:
        if active_effort: req["reasoning"] = {"effort": active_effort}
    else:
        req["temperature"] = active_temp
        req["top_p"] = active_top_p
    if tools: req["tools"] = tools

    try:
        resp = client.responses.create(**{k: v for k, v in req.items() if v is not None})
        
        text = getattr(resp, "output_text", None)
        if not text:
            chunks = []
            for block in getattr(resp, "output", []) or []:
                for c in getattr(block, "content", []) or []:
                    if getattr(c, "type", "") in ("output_text", "text"): chunks.append(getattr(c, "text", ""))
            text = "\n".join(chunks).strip()
        
        if text: 
            text = re.sub(r'\[.*?\]\(sandbox:/mnt/data/.*?\)', '', text).strip()

        generated_urls = ai_assets_service.handle_generated_files(client, resp, folder="chat_assets")
        sources_list = _extract_sources(resp)

        return (text or "[No response]", generated_urls, sources_list)
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise e

# ------------------------------------------------------------------
# 🟢 QUIZ GENERATION (Standard)
# ------------------------------------------------------------------
def generate_structured_quiz(
    conversation_input: List[Dict[str, Any]], 
    user_id: str | None = None, 
    page: str | None = None, 
    name: str | None = None, 
    email: str | None = None, 
    mode: str = "omega",
    exam_context: str = "ICFES",
    requires_visuals: bool = False # 🟢 NEW PARAMETER
) -> QuizResponse:
    
    client = get_openai_client()
    cfg = get_model_config(mode)
    
    # 🟢 PASS THE FLAG DOWN
    system_text = _build_runtime_signals(
        user_id, page, name, email, exam_context=exam_context, requires_visuals=requires_visuals
    )
    
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    req = {
        "model": cfg.model, "input": api_input,
        "text_format": QuizResponse, 
        # "tools": ... (We will add tools conditionally below)
    }
    
    # 🟢 CONDITIONAL TOOL
    if requires_visuals:
        req["tools"] = [{"type": "code_interpreter", "container": {"type": "auto"}}]
    
    is_reasoning = (cfg.model.startswith("o") and not cfg.model.startswith("gpt")) or "reasoning" in cfg.model
    if is_reasoning:
        if cfg.reasoning_effort: req["reasoning"] = {"effort": cfg.reasoning_effort}
    else:
        req["temperature"] = cfg.temperature
        req["top_p"] = cfg.top_p

    try:
        resp = client.responses.parse(**{k: v for k, v in req.items() if v is not None})
        quiz = resp.output_parsed
        
        urls = ai_assets_service.handle_generated_files(client, resp, folder="quiz_assets")
        _assign_urls_to_quiz(quiz, urls)
        
        if quiz and quiz.questions:
            for q in quiz.questions:
                QuizUtils.shuffle_options(q)

        return quiz
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise e

# ------------------------------------------------------------------
# 🟢 QUIZ STREAMING (Refactored)
# ------------------------------------------------------------------
def stream_structured_quiz(
    conversation_input: List[Dict[str, Any]], 
    user_id: str | None = None, 
    page: str | None = None, 
    name: str | None = None, 
    email: str | None = None, 
    mode: str = "omega",
    exam_context: str = "ICFES",
    requires_visuals: bool = False # 🟢 NEW PARAMETER
) -> Generator[Dict[str, Any], None, None]:
    
    client = get_openai_client()
    cfg = get_model_config(mode)
    
    # 🟢 PASS THE FLAG DOWN
    system_text = _build_runtime_signals(
        user_id, page, name, email, exam_context=exam_context, requires_visuals=requires_visuals
    )
    
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    req = {
        "model": cfg.model, "input": api_input,
        "text_format": QuizResponse, 
        # "tools": ... (Conditional below)
    }
    
    # 🟢 CONDITIONAL TOOL
    if requires_visuals:
        req["tools"] = [{"type": "code_interpreter", "container": {"type": "auto"}}]
    
    is_reasoning = (cfg.model.startswith("o") and not cfg.model.startswith("gpt")) or "reasoning" in cfg.model
    if is_reasoning:
        if cfg.reasoning_effort: req["reasoning"] = {"effort": cfg.reasoning_effort}
    else:
        req["temperature"] = cfg.temperature
        req["top_p"] = cfg.top_p

    streamed_questions = []

    try:
        with client.responses.stream(**{k: v for k, v in req.items() if v is not None}) as stream:
            
            parser_generator = StreamParser.parse_quiz_stream(stream)
            
            for event in parser_generator:
                if event["type"] == "intro":
                    yield event
                
                elif event["type"] == "question":
                    q_obj = event["data"]
                    QuizUtils.shuffle_options(q_obj)
                    streamed_questions.append(q_obj)
                    yield event
                
                elif event["type"] == "done":
                    final_parsed = event["full_response"]
                    
                    urls = []
                    if hasattr(stream, 'get_final_response'):
                        final_raw = stream.get_final_response()
                        urls = ai_assets_service.handle_generated_files(client, final_raw, folder="quiz_assets")
                    
                    if final_parsed and hasattr(final_parsed, 'questions') and streamed_questions:
                        if len(final_parsed.questions) == len(streamed_questions):
                            final_parsed.questions = streamed_questions 
                        else:
                            for q in final_parsed.questions:
                                 QuizUtils.shuffle_options(q)

                    if final_parsed and urls:
                        _assign_urls_to_quiz(final_parsed, urls)

                    yield {"type": "done", "full_response": final_parsed}
                    
                elif event["type"] == "error":
                    yield event

    except Exception as e:
        logger.error(f"Streaming failed: {e}")
        yield {"type": "error", "error": str(e)}