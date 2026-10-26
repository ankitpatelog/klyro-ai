import secrets
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
    get_public_knowledge_base,
    list_public_knowledge_bases,
    set_public_share_token,
)
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseDetailResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    PublicKnowledgeBaseResponse,
    PublicKnowledgeBaseDirectoryItem,
    PublicShareLinkResponse,
)
from app.services.email_service import send_knowledge_base_created_email, send_knowledge_base_deleted_email


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
    knowledge_base = await create_knowledge_base(db, user_id=current_user.id, **payload.model_dump())
    await send_knowledge_base_created_email(current_user.email, knowledge_base.name)
    return knowledge_base

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
    changes = payload.model_dump(exclude_unset=True)
    # A private base must never retain an active public URL.
    if changes.get("visibility") == "private":
        changes["public_share_token"] = None
    knowledge_base = await update_knowledge_base(db, knowledge_base_id, current_user.id, changes)
    if not knowledge_base:
        raise _not_found()
    return knowledge_base


@router.post("/knowledgebase/{knowledge_base_id}/share-link", response_model=PublicShareLinkResponse)
async def create_or_regenerate_share_link(
    knowledge_base_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    knowledge_base = await get_knowledge_base(db, knowledge_base_id, current_user.id)
    if not knowledge_base:
        raise _not_found()
    if knowledge_base.visibility != "public":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Make this knowledge base public before generating a share link")
    updated = await set_public_share_token(db, knowledge_base_id, current_user.id, secrets.token_urlsafe(24))
    return PublicShareLinkResponse(public_share_token=updated.public_share_token)


@router.delete("/knowledgebase/{knowledge_base_id}/share-link", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share_link(
    knowledge_base_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await set_public_share_token(db, knowledge_base_id, current_user.id, None):
        raise _not_found()


@router.get("/public/{token}", response_model=PublicKnowledgeBaseResponse)
async def get_public_knowledge_base_details(token: str, db: AsyncSession = Depends(get_db)):
    knowledge_base = await get_public_knowledge_base(db, token)
    if not knowledge_base:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This shared knowledge base is unavailable")
    return PublicKnowledgeBaseResponse(name=knowledge_base.name, description=knowledge_base.description)


@router.get("/public", response_model=list[PublicKnowledgeBaseDirectoryItem])
async def list_public_knowledge_base_directory(db: AsyncSession = Depends(get_db)):
    """A public, searchable directory of bases with active share links."""
    return await list_public_knowledge_bases(db)


@router.delete("/knowledgebase/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    knowledge_base_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    knowledge_base = await get_knowledge_base(db, knowledge_base_id, current_user.id)
    if not knowledge_base or not await delete_knowledge_base(db, knowledge_base_id, current_user.id):
        raise _not_found()
    await send_knowledge_base_deleted_email(current_user.email, knowledge_base.name)
