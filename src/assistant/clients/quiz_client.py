# src/assistant/clients/quiz_client.py
import logging
from typing import List, Dict, Any, Tuple, Generator

from src.config.settings import get_openai_client
from src.config.model_config import get_model_config
from src.schemas.quiz_schemas import QuizResponse

from src.services.signal_service import build_runtime_signals
from src.assistant.artifact_handler import handle_generated_files, assign_urls_to_quiz
from src.utils.stream_parser import StreamParser

from .base_client import BaseAssistantClient

logger = logging.getLogger(__name__)

class QuizClient:
    """
    Handles standard and streaming quiz generation using OpenAI Structured Outputs.
    """

    @staticmethod
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
            BaseAssistantClient.inject_pdf_inputs(api_input, pdf_urls)

        tools = BaseAssistantClient.configure_tools(
            vector_store_ids, requires_visuals, requires_creative_images, pdf_urls, web_search_config, user_location, cfg
        )

        req = BaseAssistantClient.build_request_payload(cfg, api_input, tools=tools)
        req["text_format"] = QuizResponse
        
        try:
            resp = client.responses.parse(**req)
            quiz = resp.output_parsed
            
            generated_urls = handle_generated_files(client, resp, folder="quiz_assets")
            assign_urls_to_quiz(quiz, generated_urls)
            
            usage_data = BaseAssistantClient.extract_usage_metrics(getattr(resp, "usage", None))

            return (quiz, usage_data)
        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            raise e


    @staticmethod
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
            BaseAssistantClient.inject_pdf_inputs(api_input, pdf_urls)

        tools = BaseAssistantClient.configure_tools(
            vector_store_ids, requires_visuals, requires_creative_images, pdf_urls, web_search_config, user_location, cfg
        )

        req = BaseAssistantClient.build_request_payload(cfg, api_input, tools=tools)
        req["text_format"] = QuizResponse
        
        streamed_questions = []

        try:
            with client.responses.stream(**req) as stream:
                parser_generator = StreamParser.parse_quiz_stream(stream)
                
                for event in parser_generator:
                    if event["type"] == "question":
                        q_obj = event["data"]
                        streamed_questions.append(q_obj)
                        yield event
                    
                    elif event["type"] == "done":
                        final_parsed = event["full_response"]
                        
                        generated_urls = []
                        if hasattr(stream, 'get_final_response'):
                            final_raw = stream.get_final_response()
                            generated_urls = handle_generated_files(client, final_raw, folder="quiz_assets")
                            
                            usage_data = BaseAssistantClient.extract_usage_metrics(getattr(final_raw, "usage", None))
                            if usage_data:
                                yield {"type": "usage_metrics", "data": usage_data}
                        
                        if final_parsed and hasattr(final_parsed, 'questions') and streamed_questions:
                            if len(final_parsed.questions) == len(streamed_questions):
                                final_parsed.questions = streamed_questions 

                        if final_parsed and generated_urls:
                            assign_urls_to_quiz(final_parsed, generated_urls)

                        yield {"type": "done", "full_response": final_parsed}
                        
                    else:
                        yield event

        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield {"type": "error", "error": str(e)}