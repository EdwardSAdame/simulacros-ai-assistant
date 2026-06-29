# src/assistant/assistant_client.py
import logging

# Import the newly refactored domain clients
from src.assistant.clients.visual_client import VisualClient
from src.assistant.clients.chat_client import ChatClient
from src.assistant.clients.quiz_client import QuizClient
from src.assistant.clients.mindmap_client import MindMapClient

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# FACADE EXPORTS
# ------------------------------------------------------------------
# By mapping these directly, we guarantee that all existing imports 
# across your application (like in quiz_service.py and chat_service.py) 
# will continue to work perfectly without requiring any modifications.

# --- VISUAL (PLOT) GENERATION ---
generate_plot_blueprint = VisualClient.generate_plot_blueprint
execute_plot_generation = VisualClient.execute_plot_generation

# --- CHAT INTERACTION ---
send_message_to_assistant = ChatClient.send_message_to_assistant
stream_chat_response = ChatClient.stream_chat_response

# --- QUIZ GENERATION ---
generate_structured_quiz = QuizClient.generate_structured_quiz
stream_structured_quiz = QuizClient.stream_structured_quiz

# --- MIND MAP GENERATION ---
stream_structured_mindmap = MindMapClient.stream_structured_mindmap