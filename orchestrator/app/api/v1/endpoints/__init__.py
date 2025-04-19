from fastapi import APIRouter
from .process import router as process_router
from .process_async import router as process_async_router
from .builder_team import router as builder_team_router

router = APIRouter()
router.include_router(process_router, prefix="/process", tags=["process"])
router.include_router(process_async_router, prefix="/async", tags=["async"])
router.include_router(builder_team_router, prefix="/builder-team", tags=["builder-team"])
