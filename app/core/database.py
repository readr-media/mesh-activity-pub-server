"""Deprecated local database module. Kept for backward imports only."""
from contextlib import asynccontextmanager

async def init_db():
    return None

@asynccontextmanager
async def get_db():
    yield None
