# src/utils/parsers/mindmap_stream_parser.py
import re
import logging
from typing import Generator, Dict, Any

from .base_stream_parser import BaseStreamParser

logger = logging.getLogger(__name__)

class MindMapStreamParser:
    """
    Consumes the OpenAI stream and yields structured events specifically for Mind Maps.
    Yields individual nodes and edges as they are parsed from the stream.
    """

    @staticmethod
    def parse(stream) -> Generator[Dict[str, Any], None, None]:
        buffer = ""
        last_checkpoint = None
        has_refused = False

        try:
            for event in stream:
                # 1. Handle common events via Base Parser
                event_to_yield, is_refusal, delta = BaseStreamParser.handle_common_events(event)
                
                if event_to_yield:
                    yield event_to_yield
                if is_refusal:
                    has_refused = True
                    continue
                if not delta:
                    continue

                buffer += delta

                # 2. Wait until we see the start of the nodes array safely
                if last_checkpoint is None:
                    match = re.search(r'"nodes"\s*:\s*\[', buffer)
                    if match:
                        last_checkpoint = match.end() - 1

                # 3. Detect and Parse JSON Objects (Nodes & Edges)
                if last_checkpoint is not None:
                    # Delegate the heavy JSON parsing to the Base Parser
                    for data, new_checkpoint in BaseStreamParser.extract_json_objects(buffer, last_checkpoint):
                        
                        # Duck-type the object to decide if it is a node or an edge
                        if "level" in data and "label" in data:
                            yield {"type": "node", "data": data}
                        elif ("from" in data or "source" in data) and "to" in data:
                            yield {"type": "edge", "data": data}
                            
                        last_checkpoint = new_checkpoint

            # 4. Retrieve Final Response
            yield from BaseStreamParser.finalize_stream(stream, has_refused)

        except Exception as e:
            logger.error(f"MindMapStreamParser parsing failed: {e}")
            yield {"type": "error", "error": str(e)}