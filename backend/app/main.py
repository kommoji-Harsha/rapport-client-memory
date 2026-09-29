"""
Main FastAPI application entry point for Rapport backend.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router, get_memory_backend
from backend.app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize DB tables on startup
    init_db()

    # Initialize memory bank if available
    memory = get_memory_backend()
    try:
        await memory.initialize_bank()
    except Exception:
        pass

    yield

    # Cleanup memory client on shutdown
    try:
        await memory.close()
    except Exception:
        pass


app = FastAPI(
    title="Rapport Backend API",
    description="Client-memory agent for freelancers & consultants powered by Hindsight",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes under /api
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
