from datetime import datetime
import uuid
from pydantic import BaseModel

class Knowledgebase(BaseModel):
    id : uuid.UUID
    user_id : uuid.UUID
    name : str
    description : str
    status : str
    visibility: str = "private"
    public_share_token: str | None = None
    document_limit : int 
    created_at : datetime
    document_count: int = 0


