# src/services/arena_service.py
import logging
from typing import List, Dict, Optional, Any
from src.storage import arenas_table

logger = logging.getLogger(__name__)

class ArenaService:
    """
    Business logic for managing Arenas (Chat Folders).
    Acts as the middleman between API Handlers and DynamoDB.
    """

    def create_arena_folder(
        self, 
        user_id: str, 
        title: str, 
        description: str = None, 
        system_instructions: str = None,
        files: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Creates a new Arena.
        """
        logger.info(f"Creating new arena for user {user_id}: {title}")
        
        # 1. Validation (Business Logic)
        if not title or len(title.strip()) < 3:
            raise ValueError("Title must be at least 3 characters long.")

        # 2. Persist to DB
        return arenas_table.create_arena(
            user_id=user_id,
            title=title,
            description=description,
            system_instructions=system_instructions,
            files=files
        )

    def get_user_arenas(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the list of arenas for the sidebar/menu.
        """
        logger.info(f"Fetching arenas for user {user_id}")
        return arenas_table.get_arenas_for_user(user_id)

    def get_arena_context(self, user_id: str, arena_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the specific instructions and files for an Arena.
        Used when initializing a Chat to inject the 'Personality'.
        """
        if not arena_id:
            return None
            
        logger.info(f"Loading context for Arena: {arena_id}")
        return arenas_table.get_arena_details(user_id, arena_id)

    def update_arena_details(self, user_id: str, arena_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates arena configuration (e.g. changing the prompt or adding a file).
        """
        logger.info(f"Updating Arena {arena_id} for user {user_id}")
        return arenas_table.update_arena(user_id, arena_id, updates)

    def delete_arena_folder(self, user_id: str, arena_id: str) -> bool:
        """
        Deletes the arena configuration.
        """
        logger.info(f"Deleting Arena {arena_id}")
        return arenas_table.delete_arena(user_id, arena_id)

# Singleton instance
arena_service = ArenaService()