from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
import logging
import os

logger = logging.getLogger(__name__)

# Create async engine with fallback options
try:
    if settings.database_url and settings.database_url.startswith("postgresql"):
        # Use asyncpg for PostgreSQL on Vercel
        if "+asyncpg" not in settings.database_url:
            db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
        else:
            db_url = settings.database_url
        
        engine = create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
            # Vercel serverless optimizations
            pool_size=5,
            max_overflow=10
        )
        logger.info("Using PostgreSQL database")
    else:
        # Default to SQLite for development/testing
        # Ensure directory exists
        db_path = "/tmp/dubbing_studio.db"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False}
        )
        logger.info("Using SQLite database (temporary)")

except Exception as e:
    logger.warning(f"Database configuration error: {e}")
    # Fallback to in-memory SQLite
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False}
    )
    logger.info("Using in-memory SQLite database (fallback)")

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    """Create database tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        # Don't raise in serverless environment - continue without DB
        return False