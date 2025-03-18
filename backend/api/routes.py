from fastapi import APIRouter, Depends, HTTPException, status
from schemas.document import DocumentRequest, DocumentResponse
from core.processor import process_document
from utils.auth import get_current_user

router = APIRouter(tags=["documents"])

@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    request: DocumentRequest,
    current_user = Depends(get_current_user)
):
    """
    Process and analyze a document using AI
    """
    try:
        result = await process_document(request.content, request.options)
        return DocumentResponse(
            id=result.id,
            summary=result.summary,
            analysis=result.analysis,
            status="completed"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user = Depends(get_current_user)
):
    """
    Retrieve a processed document
    """
    # Implementation would fetch document from database
    # This is a placeholder
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint not yet implemented"
    )
