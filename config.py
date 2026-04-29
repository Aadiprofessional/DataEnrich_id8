"""
Configuration settings for the enrichment pipeline.
"""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""
    name: str
    enabled: bool = True
    priority: int = 1
    reliability_score: float = 1.0
    timeout_ms: int = 2000
    max_retries: int = 2
    retry_backoff_ms: int = 100


@dataclass
class EnrichmentConfig:
    """Main configuration for enrichment engine."""
    total_timeout_ms: int = 5000
    source_timeout_ms: int = 2000
    
    data_sources: List[DataSourceConfig] = None
    
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    
    enable_retry: bool = True
    max_retries_per_source: int = 2
    retry_backoff_ms: int = 100
    
    min_quality_threshold: float = 0.3
    confidence_weights: dict = None
    
    verbose_logging: bool = True
    
    def __post_init__(self):
        """Initialize default values."""
        if self.data_sources is None:
            self.data_sources = [
                DataSourceConfig(name="clearbit", priority=3, reliability_score=0.95),
                DataSourceConfig(name="hunter", priority=2, reliability_score=0.90),
                DataSourceConfig(name="custom_db", priority=1, reliability_score=0.85),
            ]
        
        if self.confidence_weights is None:
            self.confidence_weights = {
                "full_name": 0.15,
                "email": 0.20,
                "phone": 0.10,
                "company_name": 0.15,
                "job_title": 0.10,
                "location": 0.10,
                "social": 0.05,
                "website": 0.15
            }


DEFAULT_CONFIG = EnrichmentConfig()
