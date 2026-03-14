# src/streaming/stream_manager.py
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class StreamManager:
    """
    Manages real-time data streaming to the WebSocket client via API Gateway.
    Abstracts away the JSON serialization and error handling for connection issues.
    """

    def __init__(self, connection_id: str, api_gateway_client: Any):
        """
        :param connection_id: The WebSocket connection ID of the user.
        :param api_gateway_client: Boto3 client for 'apigatewaymanagementapi'.
        """
        self.connection_id = connection_id
        self.client = api_gateway_client
        self.packet_count = 0

    def _send(self, payload: Dict[str, Any]) -> bool:
        """
        Internal helper to send a dictionary as a JSON string to the client.
        Returns True if successful, False if the connection is gone or failed.
        """
        if not self.connection_id or not self.client:
            return False

        try:
            self.client.post_to_connection(
                ConnectionId=self.connection_id,
                Data=json.dumps(payload)
            )
            self.packet_count += 1
            return True
        except Exception as e:
            # Handle "GoneException" (User closed the tab)
            # We check string for robustness since specific Exception classes vary by boto3 setup
            if "GoneException" in str(e) or "410" in str(e):
                logger.warning(f"StreamManager: Connection {self.connection_id} is gone.")
            else:
                logger.error(f"StreamManager: Failed to send data: {e}")
            return False

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
    # NEW: CREATIVE IMAGE STREAMING METHODS
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