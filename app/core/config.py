from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Basic settings
    PROJECT_NAME: str = "READr Mesh ActivityPub Server"
    API_V1_STR: str = "/api/v1"
    
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/readr_mesh"
    
    # GraphQL settings
    GRAPHQL_ENDPOINT: str = "http://localhost:3000/api/graphql"
    GRAPHQL_TOKEN: Optional[str] = None
    
    # ActivityPub settings
    ACTIVITYPUB_DOMAIN: str = "activity.readr.tw"
    ACTIVITYPUB_PROTOCOL: str = "https"
    ACTIVITYPUB_PORT: int = 443
    
    # Key settings
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS settings
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # File upload settings
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Federation settings
    FEDERATION_ENABLED: bool = True
    MAX_FOLLOWERS: int = 10000
    MAX_FOLLOWING: int = 10000
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
