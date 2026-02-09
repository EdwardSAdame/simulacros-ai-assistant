# src/services/arena_service.py
import logging
from typing import List, Dict, Optional, Any
from src.storage import arenas_table
from src.assistant.vector_store_manager import vector_store_manager

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
        If files are provided, creates an OpenAI Vector Store and links it.
        """
        logger.info(f"Creating new arena for user {user_id}: {title}")
        
        # 1. Validation
        if not title or len(title.strip()) < 3:
            raise ValueError("Title must be at least 3 characters long.")

        # 2. Vector Store Creation (If files exist)
        vector_store_id = None
        if files:
            # Extract just the URLs from the file objects
            # Assumes file structure: {'name': 'foo.pdf', 'url': 'https://...', 'type': 'pdf'}
            file_urls = [f.get('url') for f in files if f.get('url')]
            
            if file_urls:
                try:
                    vector_store_id = vector_store_manager.create_arena_knowledge_base(
                        arena_name=title,
                        file_urls=file_urls
                    )
                except Exception as e:
                    logger.error(f"Failed to create vector store during arena creation: {e}")
                    # We proceed to create the arena anyway, just without the store (fail open)

        # 3. Persist to DB
        return arenas_table.create_arena(
            user_id=user_id,
            title=title,
            description=description,
            system_instructions=system_instructions,
            files=files,
            vector_store_id=vector_store_id
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
        Updates arena configuration. 
        """
        logger.info(f"Updating Arena {arena_id} for user {user_id}")
        
        # NOTE: If we wanted to support ADDING files to an existing arena, 
        # we would check for 'files' in `updates`, calculate the difference, 
        # and call vector_store_manager.add_files_to_arena().
        # For this step, we are keeping it simple (Creation Only).
        
        return arenas_table.update_arena(user_id, arena_id, updates)

    def delete_arena_folder(self, user_id: str, arena_id: str) -> bool:
        """
        Deletes the arena configuration and cleans up the Vector Store from OpenAI.
        """
        logger.info(f"Deleting Arena {arena_id}")
        
        # 1. Fetch the arena FIRST to see if it has a Vector Store
        try:
            arena = self.get_arena_context(user_id, arena_id)
            if arena:
                vector_store_id = arena.get("VectorStoreId")
                if vector_store_id:
                    logger.info(f"Found associated Vector Store: {vector_store_id}. Deleting...")
                    
                    # 2. Delete from OpenAI
                    success = vector_store_manager.delete_vector_store(vector_store_id)
                    
                    if success:
                        logger.info(f"Successfully deleted vector store {vector_store_id}")
                    else:
                        logger.warning(f"Could not delete vector store {vector_store_id} (it might be already gone)")
        except Exception as e:
            # We catch errors here so the DB deletion still happens (preventing zombies in the app)
            logger.error(f"Error while trying to cleanup vector store for arena {arena_id}: {e}")

        # 3. Delete from DynamoDB
        return arenas_table.delete_arena(user_id, arena_id)

# Singleton instance
arena_service = ArenaService()