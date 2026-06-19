from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
import logging
import os

logger = logging.getLogger(__name__)

# Create async engine - compatible with PostgreSQL for production
if settings.database_url.startswith("sqlite"):
    engine = create_async_engine(
        settings.database_url.replace("sqlite://", "sqlite+aiosqlite://"),
        echo=False,
        connect_args={"check_same_thread": False}
    )
elif settings.database_url.startswith("postgresql"):
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
else:
    # Default to SQLite for development
    engine = create_async_engine(
        "sqlite+aiosqlite:///./dubbing_studio.db",
        echo=False,
        connect_args={"check_same_thread": False}
    )

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
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        # Don't raise in serverless environment
        pass