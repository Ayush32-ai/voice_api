import redis.asyncio as redis
import json
import uuid
from typing import Optional, List
import logging
from datetime import datetime, timedelta

from app.config import settings
from app.schemas import JobResponse
from app.models import JobLog

logger = logging.getLogger(__name__)

class RedisService:
    """Service for Redis operations and caching"""
    
    def __init__(self):
        self.redis_client = None
    
    async def get_redis_client(self):
        """Get Redis client with connection pooling"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                await self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Running without Redis.")
                self.redis_client = None
        return self.redis_client
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    # Job caching methods
    async def cache_job(self, job_id: str, job_data: JobResponse, ttl: int = 3600):
        """Cache job data in Redis"""
        try:
            client = await self.get_redis_client()
            if client is None:
                return  # Skip if Redis is not available
                
            key = f"job:{job_id}"
            
            # Convert job data to JSON
            job_json = job_data.model_dump_json()
            
            await client.setex(key, ttl, job_json)
            logger.debug(f"Cached job {job_id}")
        
        except Exception as e:
            logger.warning(f"Error caching job {job_id}: {str(e)}")
    
    async def get_cached_job(self, job_id: str) -> Optional[JobResponse]:
        """Get cached job data from Redis"""
        try:
            client = await self.get_redis_client()
            key = f"job:{job_id}"
            
            job_json = await client.get(key)
            if job_json:
                job_data = json.loads(job_json)
                return JobResponse(**job_data)
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting cached job {job_id}: {str(e)}")
            return None
    
    async def invalidate_job_cache(self, job_id: str):
        """Remove job from cache"""
        try:
            client = await self.get_redis_client()
            key = f"job:{job_id}"
            await client.delete(key)
        
        except Exception as e:
            logger.error(f"Error invalidating job cache {job_id}: {str(e)}")
    
    # Job progress tracking
    async def set_job_progress(self, job_id: str, progress: float, step: str):
        """Set job progress in Redis for real-time updates"""
        try:
            client = await self.get_redis_client()
            key = f"job:progress:{job_id}"
            
            progress_data = {
                "progress": progress,
                "step": step,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await client.setex(key, 7200, json.dumps(progress_data))  # 2 hour TTL
        
        except Exception as e:
            logger.error(f"Error setting job progress {job_id}: {str(e)}")
    
    async def get_job_progress(self, job_id: str) -> Optional[dict]:
        """Get current job progress from Redis"""
        try:
            client = await self.get_redis_client()
            key = f"job:progress:{job_id}"
            
            progress_json = await client.get(key)
            if progress_json:
                return json.loads(progress_json)
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting job progress {job_id}: {str(e)}")
            return None
    
    # Job logging
    async def cache_job_log(self, job_id: str, log_entry: JobLog, max_logs: int = 100):
        """Cache job log entries in Redis (recent logs only)"""
        try:
            client = await self.get_redis_client()
            key = f"job:logs:{job_id}"
            
            log_data = {
                "id": str(log_entry.id),
                "step": log_entry.step.value,
                "message": log_entry.message,
                "level": log_entry.level,
                "timestamp": log_entry.timestamp.isoformat(),
                "metadata_json": log_entry.metadata_json
            }
            
            # Add to list (left push for newest first)
            await client.lpush(key, json.dumps(log_data))
            
            # Trim to keep only recent logs
            await client.ltrim(key, 0, max_logs - 1)
            
            # Set expiration
            await client.expire(key, 86400)  # 24 hours
        
        except Exception as e:
            logger.error(f"Error caching job log {job_id}: {str(e)}")
    
    async def get_cached_job_logs(self, job_id: str, limit: int = 50) -> List[dict]:
        """Get cached job logs from Redis"""
        try:
            client = await self.get_redis_client()
            key = f"job:logs:{job_id}"
            
            log_entries = await client.lrange(key, 0, limit - 1)
            
            logs = []
            for log_json in log_entries:
                log_data = json.loads(log_json)
                logs.append(log_data)
            
            return logs
        
        except Exception as e:
            logger.error(f"Error getting cached job logs {job_id}: {str(e)}")
            return []
    
    # Rate limiting
    async def check_rate_limit(self, key: str, limit: int, window: int = 3600) -> bool:
        """Check if rate limit is exceeded"""
        try:
            client = await self.get_redis_client()
            
            current_count = await client.get(f"rate_limit:{key}")
            
            if current_count is None:
                await client.setex(f"rate_limit:{key}", window, 1)
                return True
            
            if int(current_count) >= limit:
                return False
            
            await client.incr(f"rate_limit:{key}")
            return True
        
        except Exception as e:
            logger.error(f"Error checking rate limit {key}: {str(e)}")
            return True  # Allow on Redis errors
    
    # Health check
    async def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            client = await self.get_redis_client()
            await client.ping()
            return True
        
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False
    
    # Statistics
    async def increment_counter(self, counter_name: str, ttl: int = 86400):
        """Increment a counter in Redis"""
        try:
            client = await self.get_redis_client()
            key = f"counter:{counter_name}"
            
            count = await client.incr(key)
            if count == 1:  # First increment, set TTL
                await client.expire(key, ttl)
            
            return count
        
        except Exception as e:
            logger.error(f"Error incrementing counter {counter_name}: {str(e)}")
            return 0
    
    async def get_counter(self, counter_name: str) -> int:
        """Get counter value from Redis"""
        try:
            client = await self.get_redis_client()
            key = f"counter:{counter_name}"
            
            count = await client.get(key)
            return int(count) if count else 0
        
        except Exception as e:
            logger.error(f"Error getting counter {counter_name}: {str(e)}")
            return 0

# Global Redis service instance
redis_service = RedisService()