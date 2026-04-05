# src/services/container_usage_service.py
from datetime import datetime, timezone
from src.storage.container_usage_table import ContainerUsageTable
from src.utils.logging_utils import log_event

class ContainerUsageService:
    """
    Business logic layer for container usage tracking.
    Ensures we only record once per unique container session and allows container reuse.
    """

    def __init__(self):
        self.storage = ContainerUsageTable()

    def get_active_container_for_session(self, session_id: str) -> str | None:
        """
        Retrieves the most recently used container ID for a given session,
        ensuring it has not expired (OpenAI containers expire after ~20 mins).
        """
        if not session_id:
            return None
            
        existing_containers = self.storage.get_session_containers(session_id)
        if not existing_containers:
            return None
            
        try:
            # Sort by Timestamp descending so the newest container is first
            sorted_containers = sorted(
                existing_containers, 
                key=lambda x: x.get("Timestamp", ""), 
                reverse=True
            )
            latest_record = sorted_containers[0]
            
            # Check if the container is still alive (less than 15 minutes old to be safe)
            timestamp_str = latest_record.get("Timestamp")
            if timestamp_str:
                # Handle ISO format strings safely
                created_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                current_time = datetime.now(timezone.utc)
                age_in_seconds = (current_time - created_time).total_seconds()
                
                if age_in_seconds < (15 * 60):  # 15 minutes
                    return latest_record.get("ContainerId")
                else:
                    log_event("container_expired", {"session_id": session_id, "age_seconds": age_in_seconds})
                    return None
            
            return latest_record.get("ContainerId")
            
        except Exception as e:
            log_event(
                event_type="container_sort_failed",
                details={"session_id": session_id, "error": str(e)},
                level="error"
            )
            return None

    def log_container_usage(
        self,
        user_id: str,
        session_id: str,
        container_id: str,
        memory_limit: str = "1g"
    ) -> bool:
        """
        Validates and processes container usage. 
        Prevents duplicate records by checking if the container was already recorded.
        """
        if not user_id or not session_id or not container_id:
            log_event(
                event_type="container_logging_missing_fields", 
                details={
                    "user_id": user_id, 
                    "session_id": session_id, 
                    "container_id": container_id
                }, 
                level="warning"
            )
            return False

        # 1. Query the Global Secondary Index to get all containers for this session
        existing_containers = self.storage.get_session_containers(session_id)
        
        # 2. Check if this specific container has already been recorded
        for record in existing_containers:
            if record.get("ContainerId") == container_id:
                log_event(
                    event_type="container_already_recorded",
                    details={
                        "user_id": user_id, 
                        "session_id": session_id, 
                        "container_id": container_id
                    }
                )
                return False

        # 3. If it is a new container, persist it
        timestamp = datetime.now(timezone.utc).isoformat()

        return self.storage.record_container_usage(
            user_id=user_id,
            timestamp=timestamp,
            session_id=session_id,
            container_id=container_id,
            memory_limit=memory_limit
        )