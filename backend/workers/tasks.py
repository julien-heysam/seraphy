from workers.celery_app import celery_app
from core.processor import process_document
from schemas.document import ProcessingOptions
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="process_document_task")
def process_document_task(self, content: str, options_dict: dict):
    """
    Celery task to process documents asynchronously
    
    Args:
        content: Document content to process
        options_dict: Dictionary of processing options
    
    Returns:
        Dictionary with processing results
    """
    try:
        # Convert dict to ProcessingOptions
        options = ProcessingOptions(**options_dict)
        
        # Process document (this would be awaited in an async context)
        # For Celery, we're using the sync version
        result = process_document(content, options)
        
        return {
            "id": result.id,
            "summary": result.summary,
            "analysis": result.analysis,
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise
