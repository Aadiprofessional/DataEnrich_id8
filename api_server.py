"""
FastAPI server for Data Enrichment Pipeline.
Provides REST API endpoints for profile enrichment.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import asyncio
from datetime import datetime

from enrichment_engine import EnrichmentEngine
from models import UserInput, EnrichedProfile
from config import EnrichmentConfig

app = FastAPI(
    title="Data Enrichment API",
    description="API for enriching user profiles from multiple data sources",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = EnrichmentEngine()


class EnrichmentRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?[\d\s\-()]+$')
    name: Optional[str] = Field(None, min_length=1, max_length=100)

    class Config:
        schema_extra = {
            "example": {
                "email": "alice@example.com",
                "name": "Alice Smith"
            }
        }


class EnrichmentResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    processing_time_ms: float
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    cache_stats: dict


@app.get("/")
async def root():
    return {
        "message": "Data Enrichment API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "enrich": "/api/v1/enrich",
            "batch_enrich": "/api/v1/batch-enrich",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    stats = engine.get_engine_stats()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "cache_stats": stats.get("cache_stats", {})
    }


@app.post("/api/v1/enrich", response_model=EnrichmentResponse)
async def enrich_profile(request: EnrichmentRequest):
    try:
        user_input = UserInput(
            email=request.email,
            phone=request.phone,
            name=request.name
        )
        
        profile = await engine.enrich(user_input)
        
        return EnrichmentResponse(
            success=True,
            data=profile.to_dict(),
            error=None,
            processing_time_ms=profile.processing_time_ms,
            timestamp=datetime.utcnow().isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")


@app.post("/api/v1/batch-enrich", response_model=List[EnrichmentResponse])
async def batch_enrich(requests: List[EnrichmentRequest]):
    try:
        user_inputs = [
            UserInput(email=r.email, phone=r.phone, name=r.name)
            for r in requests
        ]
        
        profiles = await asyncio.gather(*[
            engine.enrich(user) for user in user_inputs
        ])
        
        return [
            EnrichmentResponse(
                success=True,
                data=profile.to_dict(),
                error=None,
                processing_time_ms=profile.processing_time_ms,
                timestamp=datetime.utcnow().isoformat()
            )
            for profile in profiles
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch enrichment failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
