from fastapi import APIRouter

from app.api.v1.endpoints import auth, document, knowledge_bases, rag, webscoket



api_router = APIRouter()


# all auth router will start from the /auth 
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["knowledge-bases"])
api_router.include_router(document.router, prefix="/documents", tags=["documents"])
api_router.include_router(document.knowledge_base_router, prefix="/knowledge-bases", tags=["documents"])
api_router.include_router(webscoket.router, tags=["websocket"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
