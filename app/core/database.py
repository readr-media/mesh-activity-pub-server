from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import MetaData
from contextlib import asynccontextmanager
from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create base model class
Base = declarative_base()

# Metadata
metadata = MetaData()

async def init_db():
    """Initialize database"""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def get_db():
    """Get database session (usable as FastAPI dependency and async context manager)"""
    async with AsyncSessionLocal() as session:
        yield session
