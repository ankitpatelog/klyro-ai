from datetime import datetime
import uuid
from pydantic import BaseModel

class Knowledgebase(BaseModel):
    id : uuid.UUID
    user_id : uuid.UUID
    name : str
    description : str
    status : str
    document_limit : int 
    created_at : datetime


