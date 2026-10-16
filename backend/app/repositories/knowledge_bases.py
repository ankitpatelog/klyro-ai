import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import Knowledgebase


_FIELDS = "id, user_id, name, description, status, document_limit, created_at"


async def create_knowledge_base(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    description: str,
    status: str,
    document_limit: int,
) -> Knowledgebase:
    result = await db.execute(
        text(f"""
            INSERT INTO knowledgebases ({_FIELDS})
            VALUES (:id, :user_id, :name, :description, :status, :document_limit, NOW())
            RETURNING {_FIELDS}
        """),
        {
            "id": str(uuid.uuid4()),
            "user_id": str(user_id),
            "name": name,
            "description": description,
            "status": status,
            "document_limit": document_limit,
        },
    )
    await db.commit()
    return Knowledgebase(**result.mappings().one())


async def list_knowledge_bases(db: AsyncSession, user_id: uuid.UUID) -> list[Knowledgebase]:
    result = await db.execute(
        text(f"""
            SELECT {_FIELDS}
            FROM knowledgebases
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """),
        {"user_id": str(user_id)},
    )
    return [Knowledgebase(**row) for row in result.mappings().all()]


async def get_knowledge_base(
    db: AsyncSession, knowledge_base_id: uuid.UUID, user_id: uuid.UUID
) -> Knowledgebase | None:
    result = await db.execute(
        text(f"""
            SELECT {_FIELDS}
            FROM knowledgebases
            WHERE id = :id AND user_id = :user_id
        """),
        {"id": str(knowledge_base_id), "user_id": str(user_id)},
    )
    row = result.mappings().first()
    return Knowledgebase(**row) if row else None


async def update_knowledge_base(
    db: AsyncSession,
    knowledge_base_id: uuid.UUID,
    user_id: uuid.UUID,
    changes: dict[str, object],
) -> Knowledgebase | None:
    if not changes:
        return await get_knowledge_base(db, knowledge_base_id, user_id)

    assignments = ", ".join(f"{field} = :{field}" for field in changes)
    params = {**changes, "id": str(knowledge_base_id), "user_id": str(user_id)}
    result = await db.execute(
        text(f"""
            UPDATE knowledgebases
            SET {assignments}
            WHERE id = :id AND user_id = :user_id
            RETURNING {_FIELDS}
        """),
        params,
    )
    row = result.mappings().first()
    if row:
        await db.commit()
        return Knowledgebase(**row)
    await db.rollback()
    return None


async def delete_knowledge_base(
    db: AsyncSession, knowledge_base_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    result = await db.execute(
        text("""
            DELETE FROM knowledgebases
            WHERE id = :id AND user_id = :user_id
        """),
        {"id": str(knowledge_base_id), "user_id": str(user_id)},
    )
    if result.rowcount:
        await db.commit()
        return True
    await db.rollback()
    return False
