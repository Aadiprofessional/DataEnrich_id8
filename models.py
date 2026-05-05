"""
Data models and types for the enrichment pipeline.
"""
# shape all the data 
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from enum import Enum
import json


class SourceStatus(Enum):
    """Status of data source call."""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass
class SourceResult:
    """Result from a single data source."""
    source_name: str
    status: SourceStatus
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    response_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_name": self.source_name,
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "response_time_ms": self.response_time_ms
        }


@dataclass
class UserInput:
    """User input to enrich."""
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    
    def __post_init__(self):
        """Validate that at least one identifier is provided."""
        if not any([self.email, self.phone, self.name]):
            raise ValueError("At least one identifier (email, phone, or name) must be provided")


@dataclass
class EnrichedProfile:
    """Final enriched user profile."""
    user_input: UserInput
    
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    industry: Optional[str] = None
    
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    website: Optional[str] = None
    
    source_results: List[SourceResult] = field(default_factory=list)
    quality_scores: Dict[str, float] = field(default_factory=dict)
    overall_quality_score: float = 0.0
    is_complete: bool = False
    processing_time_ms: float = 0.0
    
    field_confidence: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_input": asdict(self.user_input),
            "personal_info": {
                "full_name": self.full_name,
                "email": self.email,
                "phone": self.phone
            },
            "location": {
                "city": self.city,
                "state": self.state,
                "country": self.country,
                "postal_code": self.postal_code
            },
            "company_info": {
                "company_name": self.company_name,
                "job_title": self.job_title,
                "industry": self.industry
            },
            "social_web": {
                "linkedin_url": self.linkedin_url,
                "twitter_handle": self.twitter_handle,
                "website": self.website
            },
            "metadata": {
                "is_complete": self.is_complete,
                "overall_quality_score": round(self.overall_quality_score, 2),
                "field_confidence": {k: round(v, 2) for k, v in self.field_confidence.items()},
                "quality_scores_by_source": {k: round(v, 2) for k, v in self.quality_scores.items()},
                "processing_time_ms": round(self.processing_time_ms, 2),
                "source_results": [sr.to_dict() for sr in self.source_results]
            }
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
