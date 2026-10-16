from fastapi import APIRouter

from app.api.v1.endpoints import auth, knowledge_bases



api_router = APIRouter()


# all auth router will start from the /auth 
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["knowledge-bases"])
