# src/assistant/clients/mindmap_client.py
import logging
from typing import List, Dict, Any, Generator

from src.config.settings import get_openai_client
from src.config.model_config import get_model_config
from src.schemas.mindmap_schemas import MindMapPayload
from src.config.mindmap_instructions import build_mindmap_instructions
from src.utils.stream_parser import StreamParser

from .base_client import BaseAssistantClient

logger = logging.getLogger(__name__)

class MindMapClient:
    """
    Handles streaming structured mind map generation.
    """

    @staticmethod
    def stream_structured_mindmap(
        conversation_input: List[Dict[str, Any]], 
        mode: str = "omega"
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streams a structured Mind Map generation.
        Yields individual node and edge events as they are parsed from the stream.
        """
        client = get_openai_client()
        cfg = get_model_config(mode)
        
        system_prompt = build_mindmap_instructions()
        
        # Filter out existing system prompts to enforce the mindmap specific instructions
        filtered_conversation = [msg for msg in conversation_input if msg.get("role") != "system"]
        api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_prompt.strip()}]}]
        api_input.extend(filtered_conversation)

        # Note: Mind Maps typically do not require code interpreter or web search tools,
        # so we intentionally omit them here for faster response generation.
        req = BaseAssistantClient.build_request_payload(cfg, api_input, tools=None)
        req["text_format"] = MindMapPayload
        
        try:
            with client.responses.stream(**req) as stream:
                parser_generator = StreamParser.parse_mindmap_stream(stream)
                
                for event in parser_generator:
                    if event["type"] in ["node", "edge"]:
                        yield event
                    
                    elif event["type"] == "done":
                        final_parsed = event["full_response"]
                        
                        if hasattr(stream, 'get_final_response'):
                            final_raw = stream.get_final_response()
                            usage_data = BaseAssistantClient.extract_usage_metrics(getattr(final_raw, "usage", None))
                            if usage_data:
                                yield {"type": "usage_metrics", "data": usage_data}
                            
                        yield {"type": "done", "full_response": final_parsed}
                    else:
                        yield event

        except Exception as e:
            logger.error(f"Mindmap streaming failed: {e}")
            yield {"type": "error", "error": str(e)}