from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4

class ProcessingOptions(BaseModel):
    summarize: bool = True
    extract_entities: bool = True
    generate_questions: bool = False
    language: str = "en"

class DocumentRequest(BaseModel):
    content: str
    options: Optional[ProcessingOptions] = Field(default_factory=ProcessingOptions)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class DocumentResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    summary: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
