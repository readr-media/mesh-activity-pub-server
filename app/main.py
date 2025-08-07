from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.activitypub import activitypub_router
from app.core.database import init_db

app = FastAPI(
    title="READr Mesh ActivityPub Server",
    description="ActivityPub server for READr Mesh federation",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Include ActivityPub routes
app.include_router(activitypub_router, prefix="/.well-known", tags=["activitypub"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    await init_db()

@app.get("/")
async def root():
    """Root path"""
    return {"message": "READr Mesh ActivityPub Server"}

@app.get("/.well-known/webfinger")
async def webfinger(resource: str):
    """WebFinger endpoint for user discovery"""
    from app.core.activitypub.webfinger import handle_webfinger
    return await handle_webfinger(resource)

@app.get("/.well-known/nodeinfo")
async def nodeinfo():
    """NodeInfo endpoint for instance information"""
    from app.core.activitypub.nodeinfo import get_nodeinfo
    return get_nodeinfo()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
