from fastapi import APIRouter

from app.api.v1.endpoints import auth



api_router = APIRouter()


# all auth router will start from the /auth 
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])