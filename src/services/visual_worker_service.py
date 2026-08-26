# src/services/visual_worker_service.py
import base64
import threading
import queue
import logging
from typing import Dict, Any, Tuple, Optional

from src.config.settings import (
    get_openai_client, 
    get_image_generation_size, 
    get_image_generation_partials,
    get_code_interpreter_memory
)
from src.config.model_config import get_model_config 
from src.config.creative_image_instructions import get_creative_image_system_prompt
from src.config.visual_instructions import build_visual_instructions

from src.services.storage_service import storage_service
from src.services.image_usage_service import ImageUsageService
from src.services.token_usage_service import TokenUsageService
from src.services.container_usage_service import ContainerUsageService
from src.services.ai_assets_service import AiAssetsService

from src.assistant.clients.base_client import BaseAssistantClient

logger = logging.getLogger(__name__)

class VisualWorkerService:
    """
    Manages background threads and queues for generating visual assets 
    (DALL-E images and Matplotlib plots) in parallel with streaming text.
    """
    def __init__(
        self, 
        mode: str, 
        user_id: Optional[str], 
        conversation_id: Optional[str], 
        stream_manager: Any,
        active_container_id: Optional[str] = None
    ):
        self.mode = mode
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.stream_manager = stream_manager
        self.active_container_id = active_container_id
        
        self.image_threads = []
        self.plot_queue = queue.Queue()
        self.plot_worker_thread = None
        
        # Shared state to map back to the final quiz object
        self.image_urls_map: Dict[Tuple[int, Optional[int]], str] = {}

    def _log_token_usage(self, usage_obj: Any):
        if not usage_obj or not self.user_id or not self.conversation_id: 
            return
        try:
            active_config = get_model_config(self.mode)
            usage_dict = BaseAssistantClient.extract_usage_metrics(usage_obj)
            
            TokenUsageService().log_token_usage(
                user_id=self.user_id,
                conversation_id=self.conversation_id, 
                source="quiz",                
                tier=self.mode,   
                engine=active_config.model, 
                input_tokens=usage_dict["input_tokens"],
                output_tokens=usage_dict["output_tokens"],
                total_tokens=usage_dict["total_tokens"],
                reasoning_tokens=usage_dict["reasoning_tokens"],
                cached_tokens=usage_dict["cached_tokens"]
            )
        except Exception as e:
            logger.error(f"Failed to log token usage in background worker: {e}")

    def spawn_image_worker(self, img_prompt: str, q_index: int):
        """Spawns a background thread to generate a DALL-E image."""
        t = threading.Thread(target=self._bg_image_generator, args=(img_prompt, q_index))
        t.start()
        self.image_threads.append(t)

    def enqueue_plot(self, plot_prompt: str, q_index: int, opt_index: Optional[int]):
        """Adds a plot request to the queue for the Code Interpreter thread."""
        self.plot_queue.put((plot_prompt, q_index, opt_index))

    def start_plot_worker(self):
        """Starts the persistent background thread that consumes the plot queue."""
        self.plot_worker_thread = threading.Thread(target=self._plot_worker)
        self.plot_worker_thread.start()

    def shutdown_and_wait(self):
        """Waits for all background visual generation to complete."""
        for t in self.image_threads:
            t.join()
            
        if self.plot_worker_thread:
            self.plot_queue.put(None) # Poison pill
            self.plot_worker_thread.join()

    # -------------------------------------------------------------------------
    # INTERNAL WORKERS
    # -------------------------------------------------------------------------
    def _bg_image_generator(self, img_prompt: str, q_index: int):
        try:
            bg_client = get_openai_client()
            active_config = get_model_config(self.mode) 
            
            base_instruction = "You are an expert AI illustrator for Invicto. Use the image_generation tool to create the requested image.\n\n"
            instructions = base_instruction + get_creative_image_system_prompt()
            
            bg_req = {
                "model": active_config.model, 
                "input": [{"role": "user", "content": f"Generate this image: {img_prompt}"}],
                "tools": [{
                    "type": "image_generation", 
                    "model": active_config.image_model, 
                    "partial_images": get_image_generation_partials(),
                    "size": get_image_generation_size(),         
                    "quality": active_config.image_quality 
                }],
                "instructions": instructions,
                "stream": True
            }
            
            bg_stream = bg_client.responses.create(**bg_req)
            final_url = None
            
            for bg_event in bg_stream:
                event_type = getattr(bg_event, "type", "")
                
                if event_type == "response.completed":
                    resp_obj = getattr(bg_event, "response", bg_event)
                    usage_obj = getattr(resp_obj, "usage", None)
                    self._log_token_usage(usage_obj)
                    
                    # Fix: Extract the final high-resolution image from the completed event
                    outputs = getattr(resp_obj, "output", [])
                    for out in outputs:
                        if getattr(out, "type", "") == "image_generation_call":
                            final_b64 = getattr(out, "result", None)
                            if final_b64:
                                try:
                                    img_bytes = base64.b64decode(final_b64)
                                    s3_url = storage_service.upload_image_from_bytes(img_bytes, "image/png", folder="quiz_assets")
                                    if self.stream_manager:
                                        self.stream_manager.send_partial_image(index=q_index, b64_data=s3_url, opt_index=None)
                                    final_url = s3_url
                                except Exception as upload_err:
                                    logger.warning(f"BG final image upload failed: {upload_err}")

                elif event_type == "response.image_generation_call.partial_image":
                    bg_b64 = getattr(bg_event, "partial_image_b64", "")
                    if bg_b64:
                        try:
                            img_bytes = base64.b64decode(bg_b64)
                            s3_url = storage_service.upload_image_from_bytes(img_bytes, "image/png", folder="quiz_assets")
                            # Creative images are ONLY for the stem, so opt_index is None
                            if self.stream_manager:
                                self.stream_manager.send_partial_image(index=q_index, b64_data=s3_url, opt_index=None)
                        except Exception as upload_err:
                            logger.warning(f"BG image partial upload failed: {upload_err}")
            
            if final_url: 
                self.image_urls_map[(q_index, None)] = final_url
                
                if self.user_id:
                    try:
                        active_session = self.conversation_id if self.conversation_id else f"quiz_bg_{self.user_id[-6:]}"
                        image_tracker = ImageUsageService()
                        image_tracker.log_image_usage(
                            user_id=self.user_id,
                            conversation_id=active_session,
                            source="quiz",  
                            tier=self.mode,
                            engine=active_config.image_model,
                            size=get_image_generation_size(),
                            quality=active_config.image_quality,
                            partials=get_image_generation_partials(),
                            image_count=1,
                            image_url=final_url  
                        )
                    except Exception as tracker_err:
                        logger.error(f"Failed to log background quiz image usage: {tracker_err}")

        except Exception as e:
            logger.error(f"BG image generation failed: {e}")

    def _plot_worker(self):
        bg_client = get_openai_client()
        active_config = get_model_config(self.mode)
        memory_limit = get_code_interpreter_memory()
        
        base_instruction = (
            "You MUST use the 'python' tool (Code Interpreter) to write and execute Python code to generate the requested plot.\n"
            "Do NOT output raw code as text. You must execute it.\n"
            "CRITICAL KERNEL STATE: This is a shared, persistent Python environment. You MUST begin your script EXACTLY with these lines to clear the memory:\n"
            "import matplotlib.pyplot as plt\n"
            "plt.clf()\n"
            "plt.cla()\n"
            "plt.close('all')\n"
            "You MUST use Matplotlib. After building your plot, you MUST display it using `plt.show()`. Do NOT save it to disk. Do NOT use plt.savefig().\n\n"
        )
        instructions = base_instruction + build_visual_instructions()

        current_container_id = self.active_container_id

        while True:
            item = self.plot_queue.get()
            if item is None: 
                break
                
            plot_prompt, q_index, opt_index = item
            try:
                if not plot_prompt or not str(plot_prompt).strip() or str(plot_prompt).lower() == "none":
                    self.plot_queue.task_done()
                    continue

                if current_container_id:
                    container_config = current_container_id
                else:
                    container_config = {"type": "auto", "memory_limit": memory_limit}
                
                bg_req = {
                    "model": active_config.model,
                    "input": [{"role": "user", "content": f"You MUST use the python tool to generate a plot for this mathematical request: {plot_prompt}"}],
                    "tools": [{"type": "code_interpreter", "container": container_config}],
                    "tool_choice": "required",
                    "instructions": instructions
                }
                
                response = bg_client.responses.create(**bg_req)
                
                bg_usage_obj = getattr(response, "usage", None)
                self._log_token_usage(bg_usage_obj)

                if not current_container_id:
                    output_list = getattr(response, "output", []) or []
                    cid = BaseAssistantClient.extract_container_id(output_list)
                    if cid: 
                        current_container_id = cid
                        if self.conversation_id and self.user_id:
                            try:
                                ContainerUsageService().log_container_usage(
                                    user_id=self.user_id,
                                    conversation_id=self.conversation_id, 
                                    container_id=cid,
                                    source="quiz", 
                                    memory_limit=memory_limit
                                )
                            except Exception as e:
                                logger.error(f"Failed to save background container: {e}")
                
                uploaded_map = AiAssetsService.handle_generated_files(bg_client, response, folder="quiz_assets")
                
                if uploaded_map:
                    s3_url = list(uploaded_map.values())[0]
                    if self.stream_manager:
                        self.stream_manager.send_partial_image(index=q_index, b64_data=s3_url, opt_index=opt_index)
                    self.image_urls_map[(q_index, opt_index)] = s3_url

            except Exception as e:
                logger.error(f"BG plot generation failed for index {q_index}, opt {opt_index}: {e}")
            finally:
                self.plot_queue.task_done()