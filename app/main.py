from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
import uvicorn

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.activitypub import users_router, well_known_router
# 完全改用 GraphQL，不依賴本地資料庫
from app.core.graphql_client import GraphQLClient
import httpx

app = FastAPI(
    title="READr Mesh ActivityPub Server",
    description="ActivityPub server for READr Mesh federation",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    default_response_class=ORJSONResponse,
)

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enable gzip compression for large responses
app.add_middleware(GZipMiddleware, minimum_size=500)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Include ActivityPub routes
# /.well-known 只提供發現端點
app.include_router(well_known_router, prefix="/.well-known", tags=["activitypub"])
# 其餘 ActivityPub 端點掛在根目錄
app.include_router(users_router, tags=["activitypub"])

@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup"""
    # 完全改用 GraphQL，不初始化本地資料庫
    # 建立共享 httpx AsyncClient（HTTP/2、連線池、逾時）
    GraphQLClient.set_shared_client(
        httpx.AsyncClient(
            http2=True,
            timeout=httpx.Timeout(10.0, read=20.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=100),
            headers={"User-Agent": "readr-mesh-ap/1.0"},
        )
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown"""
    client = GraphQLClient.shared_client
    if client is not None:
        await client.aclose()
    GraphQLClient.set_shared_client(None)

@app.get("/")
async def root():
    """Root path"""
    return {"message": "READr Mesh ActivityPub Server"}

# 已由 well_known_router 提供 /.well-known/webfinger 與 /.well-known/nodeinfo

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
