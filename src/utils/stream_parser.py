# src/utils/stream_parser.py
import logging
from typing import Generator, Dict, Any

# Import our newly refactored domain-specific parsers
from src.utils.parsers.quiz_stream_parser import QuizStreamParser
from src.utils.parsers.mindmap_stream_parser import MindMapStreamParser
from src.utils.parsers.flashcard_stream_parser import FlashcardStreamParser

logger = logging.getLogger(__name__)

class StreamParser:
    """
    Facade for stream parsing.
    Delegates the low-level text stream parsing to domain-specific parsers
    to extract structured items progressively so the UI can stream them in real-time.
    """

    @staticmethod
    def parse_quiz_stream(stream) -> Generator[Dict[str, Any], None, None]:
        """
        Consumes the OpenAI stream and yields structured events for Quizzes.
        """
        yield from QuizStreamParser.parse(stream)

    @staticmethod
    def parse_mindmap_stream(stream) -> Generator[Dict[str, Any], None, None]:
        """
        Consumes the OpenAI stream and yields structured events for Mind Maps.
        """
        yield from MindMapStreamParser.parse(stream)

    @staticmethod
    def parse_flashcard_stream(stream) -> Generator[Dict[str, Any], None, None]:
        """
        Consumes the OpenAI stream and yields structured events for Flashcards.
        """
        yield from FlashcardStreamParser.parse(stream)