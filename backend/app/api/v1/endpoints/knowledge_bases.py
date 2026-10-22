import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.document import list_documents_for_knowledge_base
from app.repositories.knowledge_bases import (
    create_knowledge_base,
    delete_knowledge_base,
    get_knowledge_base,
    list_knowledge_bases,
    update_knowledge_base,
)
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseDetailResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)


router = APIRouter()


def _not_found() -> HTTPException:
    # Deliberately use the same response for missing and non-owned resources.
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

# create knowledge base 
@router.post("/knowledgebase", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create(
    payload: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_knowledge_base(db, user_id=current_user.id, **payload.model_dump())

# get all knowledge base 
@router.get("/knowledgebase", response_model=list[KnowledgeBaseResponse])
async def list_all(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await list_knowledge_bases(db, current_user.id)


@router.get("/knowledgebase/{knowledge_base_id}", response_model=KnowledgeBaseDetailResponse)
async def get_one(
    knowledge_base_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    knowledge_base = await get_knowledge_base(db, knowledge_base_id, current_user.id)
    if not knowledge_base:
        raise _not_found()
    documents = await list_documents_for_knowledge_base(db, knowledge_base_id, current_user.id)
    return {**knowledge_base.model_dump(), "documents": documents}


@router.patch("/knowledgebase/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
async def update(
    knowledge_base_id: uuid.UUID,
    payload: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    knowledge_base = await update_knowledge_base(
        db, knowledge_base_id, current_user.id, payload.model_dump(exclude_unset=True)
    )
    if not knowledge_base:
        raise _not_found()
    return knowledge_base


@router.delete("/knowledgebase/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    knowledge_base_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await delete_knowledge_base(db, knowledge_base_id, current_user.id):
        raise _not_found()
