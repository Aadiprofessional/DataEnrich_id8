"""
Main enrichment engine that orchestrates data collection and fusion.
Handles concurrency, timeouts, retries, and caching.
"""
#This is the "brain" that coordinates everything.
import asyncio
import time
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import OrderedDict

from models import SourceResult, SourceStatus, EnrichedProfile, UserInput
from config import EnrichmentConfig, DEFAULT_CONFIG
from data_sources import MockDataSource, ClearbitSource, HunterSource, CustomDBSource
from data_fusion import DataFusionEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize cache.
        
        Args:
            ttl_seconds: Time to live for cache entries
        """
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = OrderedDict()
    
    def _get_key(self, user_input: UserInput) -> str:
        """Generate cache key from user input."""
        key_str = json.dumps({
            "email": user_input.email,
            "phone": user_input.phone,
            "name": user_input.name
        }, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, user_input: UserInput) -> Optional[EnrichedProfile]:
        """
        Get value from cache if not expired.
        
        Args:
            user_input: User input to look up
        
        Returns:
            Cached profile or None if not found/expired
        """
        key = self._get_key(user_input)
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if datetime.now() > entry["expires_at"]:
            del self.cache[key]
            logger.debug(f"Cache entry expired for key {key}")
            return None
        
        logger.debug(f"Cache hit for key {key}")
        return entry["profile"]
    
    def set(self, user_input: UserInput, profile: EnrichedProfile) -> None:
        """
        Set value in cache.
        
        Args:
            user_input: User input (used as key)
            profile: Profile to cache
        """
        key = self._get_key(user_input)
        self.cache[key] = {
            "profile": profile,
            "expires_at": datetime.now() + timedelta(seconds=self.ttl_seconds),
            "created_at": datetime.now()
        }
        logger.debug(f"Cached profile for key {key}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "ttl_seconds": self.ttl_seconds,
            "entries": len(self.cache)
        }


class EnrichmentEngine:
    """Main enrichment engine with concurrent data fetching."""
    
    def __init__(self, config: Optional[EnrichmentConfig] = None,
                 data_sources: Optional[List[MockDataSource]] = None):
        """
        Initialize enrichment engine.
        
        Args:
            config: Enrichment configuration
            data_sources: List of data sources (if None, uses defaults)
        """
        self.config = config or DEFAULT_CONFIG
        self.data_sources = data_sources or [
            ClearbitSource(),
            HunterSource(),
            CustomDBSource()
        ]
        self.fusion_engine = DataFusionEngine(self.config)
        self.cache = SimpleCache(self.config.cache_ttl_seconds) if self.config.enable_caching else None
        self.retry_count = {}
    
    async def enrich(self, user_input: UserInput) -> EnrichedProfile:
        """
        Enrich user profile by fetching from multiple sources.
        
        Args:
            user_input: User input with email, phone, and/or name
        
        Raises:
            Exception: If any source fails
        Returns:
            EnrichedProfile with merged data from all sources
 Main function - the entry point
Check cache first (return if found)
Fetch from all sources concurrently (at the same time)
Merge results using fusion engine
Cache the result
Return the enriched profile

        """
        logger.info(f"Starting enrichment for user: {user_input}")
        start_time = time.time()
        
        if self.cache:
            cached_profile = self.cache.get(user_input)
            if cached_profile:
                logger.info("Returning cached profile")
                return cached_profile
        
        try:
            results = await asyncio.wait_for(
                self._fetch_all_sources(user_input),
                timeout=self.config.total_timeout_ms / 1000.0
            )
        except asyncio.TimeoutError:
            logger.warning("Overall enrichment timed out - returning partial results")
            results = await self._fetch_all_sources(user_input)
        
        profile = self.fusion_engine.merge_results(results, user_input)
        profile.processing_time_ms = (time.time() - start_time) * 1000
        
        if self.cache:
            self.cache.set(user_input, profile)
        
        logger.info(f"Enrichment completed in {profile.processing_time_ms:.1f}ms")
        return profile
    
    async def _fetch_all_sources(self, user_input: UserInput) -> List[SourceResult]:
        #in parallel fetch everything
        """
        Fetch data from all sources concurrently.
        
        Args:
            user_input: User input
        
        Returns:
            List of SourceResult from all sources
        """
        tasks = []
        for source in self.data_sources:
            task = self._fetch_with_retry(
                source,
                email=user_input.email,
                phone=user_input.phone,
                name=user_input.name
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        return results
    
    async def _fetch_with_retry(self, source: MockDataSource, **kwargs) -> SourceResult:
        """
        Fetch from a source with retry logic.
        
        Args:
            source: Data source to fetch from
            **kwargs: Arguments to pass to source.fetch()
        
        Returns:
            SourceResult
        """
        max_retries = self.config.max_retries_per_source if self.config.enable_retry else 1
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                result = await source.fetch(
                    timeout_ms=self.config.source_timeout_ms,
                    **kwargs
                )
                
                if result.status == SourceStatus.SUCCESS:
                    logger.debug(f"Source {source.name} succeeded")
                    return result
                
                if result.status == SourceStatus.TIMEOUT and retry_count < max_retries - 1:
                    logger.debug(f"Source {source.name} timed out, retrying...")
                    retry_count += 1
                    await asyncio.sleep(
                        (self.config.retry_backoff_ms / 1000.0) * (2 ** retry_count)
                    )
                    continue
                
                return result
            
            except Exception as e:
                last_error = e
                logger.error(f"Source {source.name} error: {str(e)}")
                
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(
                        (self.config.retry_backoff_ms / 1000.0) * (2 ** retry_count)
                    )
                else:
                    return SourceResult(
                        source_name=source.name,
                        status=SourceStatus.FAILED,
                        error=str(e),
                        response_time_ms=0
                    )
        
        return SourceResult(
            source_name=source.name,
            status=SourceStatus.FAILED,
            error=str(last_error) if last_error else "Max retries exceeded",
            response_time_ms=0
        )
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        stats = {
            "num_sources": len(self.data_sources),
            "cache_enabled": bool(self.cache),
            "retry_enabled": self.config.enable_retry,
            "max_retries": self.config.max_retries_per_source,
            "total_timeout_ms": self.config.total_timeout_ms,
            "source_timeout_ms": self.config.source_timeout_ms
        }
        
        if self.cache:
            stats["cache_stats"] = self.cache.get_stats()
        
        return stats


async def run_example():
    """Run example enrichment."""
    engine = EnrichmentEngine()
    
    test_cases = [
        UserInput(email="alice@example.com"),
        UserInput(phone="+1-555-0123", name="Bob Smith"),
        UserInput(name="Charlie Brown"),
    ]
    
    print("\n" + "="*70)
    print("DATA ENRICHMENT ENGINE - DEMO")
    print("="*70)
    
    for i, user_input in enumerate(test_cases, 1):
        print(f"\n\n[Test Case {i}]")
        print(f"Input: {user_input}")
        
        try:
            profile = await engine.enrich(user_input)
            print(engine.fusion_engine.get_fusion_report(profile))
        except Exception as e:
            logger.error(f"Enrichment failed: {str(e)}")
            print(f"Error: {str(e)}")
    
    print("\n\nEngine Statistics:")
    print(json.dumps(engine.get_engine_stats(), indent=2))


if __name__ == "__main__":
    asyncio.run(run_example())
