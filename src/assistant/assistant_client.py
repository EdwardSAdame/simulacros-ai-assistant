# src/assistant/assistant_client.py
from typing import List, Dict, Any, Type, Generator, Tuple, Optional
import logging
import json
import re
from pydantic import BaseModel, ValidationError

from src.config.settings import get_openai_client, get_vector_search_max_results
from src.config.model_config import get_model_config
from src.config.system_instructions import build_system_instructions
from src.utils.time_utils import get_current_time_info, infer_target_semester, semester_season
from src.schemas.quiz_schemas import QuizResponse, QuizQuestion 
from src.services.storage_service import storage_service

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 🔹 HELPER: Handle File Artifacts (Robust)
# ------------------------------------------------------------------
def _get_files_client(client):
    """Locates the container files accessor in the OpenAI client."""
    if hasattr(client, "beta"):
        if hasattr(client.beta, "containers") and hasattr(client.beta.containers, "files"):
            return getattr(client.beta.containers, "files")
        if hasattr(client.beta, "container_files"):
            return getattr(client.beta, "container_files")
    if hasattr(client, "containers") and hasattr(client.containers, "files"):
        return getattr(client.containers, "files")
    return getattr(client, "container_files", None)

def _handle_generated_files(client, response_obj, folder: str = "chat_assets") -> List[str]:
    """Scans the OpenAI response for generated files."""
    uploaded_urls = []
    container_id = None
    
    cf_client = _get_files_client(client)
    if not cf_client: return []

    try:
        output_items = getattr(response_obj, "output", []) or []
        for item in output_items:
            item_type = getattr(item, "type", "")
            if item_type == "code_interpreter_call":
                cid = getattr(item, "container_id", None)
                if not cid and hasattr(item, "code_interpreter"):
                    cid = getattr(item.code_interpreter, "container_id", None)
                if not cid and hasattr(item, "code_interpreter_call"):
                    cid = getattr(item.code_interpreter_call, "container_id", None)
                if cid: container_id = cid

            if item_type == "message":
                content_list = getattr(item, "content", []) or []
                if isinstance(content_list, list):
                    for part in content_list:
                        annotations = getattr(part, "annotations", []) or []
                        for ann in annotations:
                            if getattr(ann, "type", "") == "container_file_citation":
                                file_id = getattr(ann, "file_id", None)
                                fname = getattr(ann, "filename", "graph.png")
                                if file_id: _process_file(cf_client, container_id, file_id, fname, uploaded_urls, folder)

        if not uploaded_urls and container_id:
            try:
                container_files = cf_client.list(container_id)
                for c_file in container_files:
                    fname = getattr(c_file, "filename", None) or getattr(c_file, "name", None)
                    fid = getattr(c_file, "id", None) or getattr(c_file, "file_id", None)
                    if not fname: fname = "generated_plot.png"
                    if fid: _process_file(cf_client, container_id, fid, fname, uploaded_urls, folder)
            except Exception: pass
    except Exception: pass
    return uploaded_urls

def _process_file(cf_client, container_id, file_id, filename, url_list, folder: str):
    """Downloads content from OpenAI and uploads to AWS S3."""
    try:
        file_content = None
        if hasattr(cf_client, "content") and hasattr(cf_client.content, "retrieve"):
            try:
                if container_id: file_content = cf_client.content.retrieve(container_id=container_id, file_id=file_id)
                else: file_content = cf_client.content.retrieve(file_id=file_id)
            except: pass
            
        if file_content is None and callable(getattr(cf_client, "content", None)):
            try: file_content = cf_client.content(file_id)
            except: pass

        if not file_content: return

        if hasattr(file_content, "read"): file_content = file_content.read()
        elif hasattr(file_content, "content"): file_content = file_content.content
        elif hasattr(file_content, "text"): file_content = file_content.text.encode('utf-8')

        if not isinstance(file_content, (bytes, bytearray)):
            try: file_content = bytes(file_content)
            except: pass

        fname = str(filename).lower()
        if fname.endswith(".jpg") or fname.endswith(".jpeg"): ctype = "image/jpeg"
        elif fname.endswith(".pdf"): ctype = "application/pdf"
        else: 
            ctype = "image/png"
            if not fname.endswith(".png"): filename = f"{filename}.png"

        s3_url = storage_service.upload_image_from_bytes(file_content, ctype, folder=folder)
        logger.info(f"✅ Asset uploaded to S3: {s3_url}")
        url_list.append(s3_url)
    except Exception as e:
        logger.error(f"File transfer failed for {file_id}: {e}")

def _assign_urls_to_quiz(quiz_data: QuizResponse, urls: List[str]):
    if not urls: return
    idx = 0
    for q in quiz_data.questions:
        if q.image_url == "PENDING_UPLOAD" or (q.image_url and "/mnt/" in q.image_url) or (not q.image_url and idx < len(urls)):
            if idx < len(urls):
                q.image_url = urls[idx]
                idx += 1

def _build_runtime_signals(user_id: str | None, page: str | None, name: str | None, email: str | None, exam_context: str = "ICFES") -> str:
    """
    Helper for Quiz calls. 
    🟢 CRITICAL FIX: Now accepts 'exam_context' to pass to the System Prompt Builder.
    """
    tinfo = get_current_time_info()
    target = infer_target_semester()
    
    visuals_instruction = (
        "VISUALS: Use the 'python' tool (Code Interpreter) to AUTOMATICALLY GENERATE PLOTS for any request involving "
        "mathematical functions, geometry, or data trends. Do not just describe the graph—DRAW IT. Output the file."
    )

    signals = [
        f"Today is {tinfo['full_human']}.",
        f"Page: {page or '/'}",
        f"User: {user_id or 'Guest'}",
        f"Target: {target}",
        "Sources: Invicto Knowledge Base.",
        visuals_instruction
    ]
    if name: signals.append(f"Name: {name}.")
    if email: signals.append(f"Email: {email}.")
    
    # 🟢 PASS THE EXAM CONTEXT HERE
    return build_system_instructions(extras=signals, exam_context=exam_context)

# ------------------------------------------------------------------
# 🔹 HELPER: Handle Web Citations
# ------------------------------------------------------------------
def _format_citations(text: str, response_obj: Any) -> str:
    """
    Extracts URL citations from the response annotations and appends a 
    Sources section to the text if they exist.
    """
    citations = []
    try:
        # Iterate through output items to find messages with content
        output_items = getattr(response_obj, "output", []) or []
        for item in output_items:
            if getattr(item, "type", "") == "message":
                content_list = getattr(item, "content", []) or []
                for part in content_list:
                    # Check for annotations in the text content
                    annotations = getattr(part, "annotations", []) or []
                    for ann in annotations:
                        if getattr(ann, "type", "") == "url_citation":
                            url = getattr(ann, "url", None)
                            title = getattr(ann, "title", "Fuente")
                            if url:
                                citations.append(f"- [{title}]({url})")
    except Exception as e:
        logger.error(f"Error extracting citations: {e}")

    # If we found citations, append them neatly
    if citations:
        # Deduplicate while preserving order
        unique_citations = list(dict.fromkeys(citations))
        text += "\n\n**Fuentes Consultadas:**\n" + "\n".join(unique_citations)
    
    return text

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
    model_override: str | None = None # 🟢 NEW PARAMETER
) -> Tuple[str, List[str]]: 
    
    client = get_openai_client()
    cfg = get_model_config(mode)

    # 🟢 LOGIC: Use override if provided, otherwise use config model
    target_model = model_override if model_override else cfg.model

    if not system_instruction:
        # Default fallback (should rarely happen if chat_service does its job)
        system_text = _build_runtime_signals(user_id, page, name, email, exam_context="ICFES")
    else:
        system_text = system_instruction
    
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    tool_stores = vector_store_ids if vector_store_ids else []
    tools = []
    
    # 1. Vector Store Tool
    if tool_stores:
        tools.append({"type": "file_search", "vector_store_ids": tool_stores, "max_num_results": get_vector_search_max_results()})
    
    # 2. Code Interpreter Tool (Conditional)
    if requires_visuals:
        tools.append({"type": "code_interpreter", "container": {"type": "auto"}})

    # 3. 🟢 Web Search Tool (The new logic)
    if web_search_config:
        web_tool = {"type": "web_search"}
        # Check if we have domain filters
        if "allowed_domains" in web_search_config and web_search_config["allowed_domains"]:
             web_tool["filters"] = {"allowed_domains": web_search_config["allowed_domains"]}
        tools.append(web_tool)

    # 🟢 Use target_model here
    req = {"model": target_model, "input": api_input, "temperature": cfg.temperature, "top_p": cfg.top_p}
    
    # If using reasoning models (o1), remove unsupported params but tools might still be allowed (check specific model support)
    # Note: o1-preview currently supports very limited tools, but assuming standard GPT-4o usage here.
    if target_model.startswith("o1") or "reasoning" in target_model: 
        req.pop("temperature", None)
        req.pop("top_p", None)
        # o1 usually doesn't support tools yet, but we leave the logic in case it's enabled or using o3
    else:
        if tools:
            req["tools"] = tools

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
            # 🟢 Process Citations
            text = _format_citations(text, resp)

        generated_urls = _handle_generated_files(client, resp, folder="chat_assets")

        return (text or "[No response]", generated_urls)
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise e

# ------------------------------------------------------------------
# 🟢 QUIZ GENERATION
# ------------------------------------------------------------------
def generate_structured_quiz(
    conversation_input: List[Dict[str, Any]], 
    user_id: str | None = None, 
    page: str | None = None, 
    name: str | None = None, 
    email: str | None = None, 
    mode: str = "omega",
    exam_context: str = "ICFES" # 🟢 NEW PARAMETER
) -> QuizResponse:
    
    client = get_openai_client()
    cfg = get_model_config(mode)
    
    # 🟢 PASS THE CONTEXT DOWN
    system_text = _build_runtime_signals(user_id, page, name, email, exam_context=exam_context)
    
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    req = {
        "model": cfg.model, "input": api_input, "temperature": cfg.temperature, "top_p": cfg.top_p,
        "text_format": QuizResponse, 
        "tools": [{"type": "code_interpreter", "container": {"type": "auto"}}]
    }
    if cfg.model.startswith("o1"): req.pop("temperature", None); req.pop("top_p", None)

    try:
        resp = client.responses.parse(**{k: v for k, v in req.items() if v is not None})
        quiz = resp.output_parsed
        urls = _handle_generated_files(client, resp, folder="quiz_assets")
        _assign_urls_to_quiz(quiz, urls)
        return quiz
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise e

def stream_structured_quiz(
    conversation_input: List[Dict[str, Any]], 
    user_id: str | None = None, 
    page: str | None = None, 
    name: str | None = None, 
    email: str | None = None, 
    mode: str = "omega",
    exam_context: str = "ICFES" # 🟢 NEW PARAMETER
) -> Generator[Dict[str, Any], None, None]:
    
    client = get_openai_client()
    cfg = get_model_config(mode)
    
    # 🟢 PASS THE CONTEXT DOWN
    system_text = _build_runtime_signals(user_id, page, name, email, exam_context=exam_context)
    
    api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_text}]}]
    api_input.extend(conversation_input)

    req = {
        "model": cfg.model, "input": api_input, "temperature": cfg.temperature, "top_p": cfg.top_p,
        "text_format": QuizResponse, 
        "tools": [{"type": "code_interpreter", "container": {"type": "auto"}}]
    }
    if cfg.model.startswith("o1"): req.pop("temperature", None); req.pop("top_p", None)

    buffer = ""
    intro_yielded = False
    question_count = 0
    last_checkpoint = None 

    try:
        with client.responses.stream(**{k: v for k, v in req.items() if v is not None}) as stream:
            for event in stream:
                if event.type == "response.output_text.delta":
                    buffer += event.delta
                    
                    if not intro_yielded and '"questions"' in buffer:
                        match = re.search(r'"intro_message"\s*:\s*"(.*?)"', buffer, re.DOTALL)
                        if match:
                            yield {"type": "intro", "text": match.group(1).replace('\\"', '"')}
                            intro_yielded = True
                    
                    q_marker = buffer.find('"questions"')
                    if q_marker != -1:
                        arr_start = buffer.find('[', q_marker)
                        if arr_start != -1:
                            if last_checkpoint is None: last_checkpoint = arr_start
                            cursor = last_checkpoint
                            depth = 0
                            in_str = False
                            escape = False
                            obj_start = -1
                            
                            while cursor < len(buffer):
                                char = buffer[cursor]
                                if not in_str:
                                    if char == '"': in_str = True
                                    elif char == '{':
                                        if depth == 0: obj_start = cursor
                                        depth += 1
                                    elif char == '}':
                                        depth -= 1
                                        if depth == 0:
                                            try:
                                                data = json.loads(buffer[obj_start:cursor+1])
                                                class Wrapper:
                                                    def __init__(self, d): self.d = d
                                                    def dict(self): return self.d
                                                try: q_obj = QuizQuestion(**data)
                                                except: q_obj = Wrapper(data)
                                                yield {"type": "question", "index": question_count, "data": q_obj}
                                                question_count += 1
                                                last_checkpoint = cursor + 1
                                            except: pass
                                    elif char == '\\': escape = True
                                else:
                                    if escape: escape = False
                                    elif char == '\\': escape = True
                                    elif char == '"': in_str = False
                                cursor += 1

            final = stream.get_final_response()
            parsed = getattr(final, 'output_parsed', None) or getattr(final, 'parsed', None) or final
            urls = _handle_generated_files(client, final, folder="quiz_assets")
            if parsed and urls: _assign_urls_to_quiz(parsed, urls)
            yield {"type": "done", "full_response": parsed}

    except Exception as e:
        logger.error(f"Streaming failed: {e}")
        yield {"type": "error", "error": str(e)}