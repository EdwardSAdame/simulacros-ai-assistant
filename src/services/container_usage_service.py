# src/services/container_usage_service.py
from datetime import datetime, timezone
from src.storage.container_usage_table import ContainerUsageTable
from src.utils.logging_utils import log_event

class ContainerUsageService:
    """
    Business logic layer for container usage tracking.
    Ensures we only record once per unique container session.
    """

    def __init__(self):
        self.storage = ContainerUsageTable()

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
                return False # Do not save, it is a free reuse

        # 3. If it is a new container, persist it
        timestamp = datetime.now(timezone.utc).isoformat()

        return self.storage.record_container_usage(
            user_id=user_id,
            timestamp=timestamp,
            session_id=session_id,
            container_id=container_id,
            memory_limit=memory_limit
        )