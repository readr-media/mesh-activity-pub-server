from fastapi import APIRouter
from app.api.v1.endpoints import actors, health, mesh, federation, account_mapping

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(actors.router, prefix="/actors", tags=["actors"])
api_router.include_router(mesh.router, prefix="/mesh", tags=["mesh"])
api_router.include_router(federation.router, prefix="/federation", tags=["federation"])
api_router.include_router(account_mapping.router, prefix="/account-mapping", tags=["account-mapping"])
