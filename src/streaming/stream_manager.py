# src/streaming/stream_manager.py
import json
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

class StreamManager:
    """
    Manages real-time data streaming to the WebSocket client via API Gateway.
    Abstracts away the JSON serialization and error handling for connection issues.
    Now supports broadcasting to multiple active connections (multi-window support).
    """

    def __init__(self, connection_ids: Union[str, List[str]], api_gateway_client: Any):
        """
        :param connection_ids: A single WebSocket connection ID, or a list of IDs for the user.
        :param api_gateway_client: Boto3 client for 'apigatewaymanagementapi'.
        """
        # Ensure connection_ids is always a list for consistent iteration
        if isinstance(connection_ids, str):
            self.connection_ids = [connection_ids]
        else:
            self.connection_ids = connection_ids if connection_ids else []
            
        self.client = api_gateway_client
        self.packet_count = 0

    def _send(self, payload: Dict[str, Any]) -> bool:
        """
        Internal helper to send a dictionary as a JSON string to all active clients.
        Returns True if at least one connection successfully received the payload.
        """
        if not self.connection_ids or not self.client:
            return False

        # FIX: ensure_ascii=False forces Python to send pure UTF-8 Spanish characters 
        # instead of \uXXXX escape sequences. This prevents frontend regex corruption!
        payload_str = json.dumps(payload, ensure_ascii=False)
        success_count = 0

        for connection_id in self.connection_ids:
            try:
                self.client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=payload_str
                )
                success_count += 1
            except Exception as e:
                # Handle "GoneException" (User closed the tab/window)
                if "GoneException" in str(e) or "410" in str(e):
                    logger.warning(f"StreamManager: Connection {connection_id} is gone.")
                else:
                    logger.error(f"StreamManager: Failed to send data to {connection_id}: {e}")

        if success_count > 0:
            self.packet_count += 1
            return True
            
        return False

    # ------------------------------------------------------------------
    # 🟢 NEW: INTENT SIGNALING
    # ------------------------------------------------------------------
    def send_intent(self, intent: str):
        """
        Sends an early signal to the frontend to prepare the UI.
        For example, passing "flashcards" sends {"action": "flashcardsMode"}
        """
        payload = {
            "action": f"{intent}Mode"
        }
        self._send(payload)

    def send_status(self, message: str, step: str = "processing"):
        """
        Sends a transient status update (e.g., "Generating question 3...").
        Frontend can use this to show a dynamic spinner/loader label.
        """
        payload = {
            "action": "stream_status",
            "message": message,
            "step": step
        }
        self._send(payload)

    def send_quiz_item(self, question_data: Dict[str, Any], index: int):
        """
        Sends a single completed question to the frontend.
        The Frontend should listen for 'quiz_stream_item' and append it to the UI.
        """
        payload = {
            "action": "quiz_stream_item",
            "index": index,
            "question": question_data
        }
        self._send(payload)

    def send_error(self, error_message: str):
        """
        Sends an error message to the frontend if streaming fails mid-way.
        """
        payload = {
            "action": "stream_error",
            "error": error_message
        }
        self._send(payload)

    # ------------------------------------------------------------------
    # CREATIVE IMAGE STREAMING METHODS
    # ------------------------------------------------------------------
    def send_partial_image(self, index: int, b64_data: str):
        """Streams a partial, incomplete image chunk during generation."""
        payload = {
            "action": "partial_image_stream",
            "index": index,
            "image_b64": b64_data
        }
        self._send(payload)

    def send_final_image(self, b64_data: str, revised_prompt: str = ""):
        """Streams the completed, high-resolution final image."""
        payload = {
            "action": "final_image_stream",
            "image_b64": b64_data,
            "revised_prompt": revised_prompt
        }
        self._send(payload)

    # ------------------------------------------------------------------
    # METRICS METHDOS
    # ------------------------------------------------------------------
    def send_usage_metrics(self, usage_data: Dict[str, Any]):
        """
        Streams the exact token usage metrics to the frontend for visibility.
        """
        payload = {
            "action": "usage_metrics_stream",
            "usage": usage_data
        }
        self._send(payload) 

    # ------------------------------------------------------------------
    # MIND MAP STREAMING METHODS
    # ------------------------------------------------------------------
    def send_mindmap_node(self, node_data: Dict[str, Any]):
        """
        Streams a single completed mind map node to the frontend.
        """
        payload = {
            "action": "mindmap_stream_node",
            "node": node_data
        }
        self._send(payload)

    def send_mindmap_edge(self, edge_data: Dict[str, Any]):
        """
        Streams a single completed mind map edge to the frontend.
        """
        payload = {
            "action": "mindmap_stream_edge",
            "edge": edge_data
        }
        self._send(payload)