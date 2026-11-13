from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import projects, skills, experience, educations, certifications, awards, about as portfolio, auth, user, message, resume
from app.utils.token_cleanup import cleanup_expired_access_tokens
from app.config import settings
from contextlib import asynccontextmanager
from app import websocket as websocket_routes
import asyncio
import logging

logger = logging.getLogger(__name__)

async def periodic_cleanup(interval_minutes: int = 1440):
    """
    Periodically clean up expired tokens from the database.
    Runs every `interval_minutes` minutes (default: 1440 = 24 hours).
    """
    while True:
        try:
            await asyncio.sleep(interval_minutes * 60)  # Convert minutes to seconds
            deleted_count = await cleanup_expired_access_tokens()
            if deleted_count > 0:
                logger.info(f"Periodic cleanup: Removed {deleted_count} expired tokens")
        except asyncio.CancelledError:
            logger.info("Periodic cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup (schema is managed by Alembic: `alembic upgrade head`)
    # Clean up expired tokens on startup
    try:
        deleted_count = await cleanup_expired_access_tokens()
        if deleted_count > 0:
            logger.info(f"Startup cleanup: Removed {deleted_count} expired tokens")
    except Exception as e:
        logger.error(f"Error during startup cleanup: {e}")
    
    # Start periodic cleanup task (runs every 24 hours)
    cleanup_task = asyncio.create_task(periodic_cleanup(interval_minutes=1440))
    
    yield
    
    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

app.include_router(projects.router)
app.include_router(skills.router)
app.include_router(experience.router)
app.include_router(educations.router, prefix="/educations")
app.include_router(certifications.router)
app.include_router(awards.router)
app.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(message.router, prefix="/message")
app.include_router(resume.router, prefix="/resume", tags=["resume"])
app.include_router(websocket_routes.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}