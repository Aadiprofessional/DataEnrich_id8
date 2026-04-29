#!/usr/bin/env python3
"""
Quick demo script for Data Enrichment Pipeline.
Shows basic usage in ~50 lines of code.
"""

import asyncio
from enrichment_engine import EnrichmentEngine
from models import UserInput
from data_fusion import DataFusionEngine


async def demo():
    """Run a quick demo of the enrichment engine."""
    
    print("\n" + "="*70)
    print("  DATA ENRICHMENT PIPELINE - QUICK DEMO")
    print("="*70 + "\n")
    
    engine = EnrichmentEngine()
    
    print("EXAMPLE 1: Basic User Enrichment")
    print("-" * 70)
    
    user = UserInput(email="alice@example.com", name="Alice Smith")
    profile = await engine.enrich(user)
    
    print(f"Input: {user}")
    print(f"\nEnriched Profile:")
    print(f"  Name: {profile.full_name}")
    print(f"  Email: {profile.email}")
    print(f"  Company: {profile.company_name}")
    print(f"  Job Title: {profile.job_title}")
    print(f"  Location: {profile.city}, {profile.state}, {profile.country}")
    print(f"\nQuality Metrics:")
    print(f"  Overall Quality Score: {profile.overall_quality_score:.2%}")
    print(f"  Profile Complete: {profile.is_complete}")
    print(f"  Processing Time: {profile.processing_time_ms:.1f}ms")
    
    print(f"\nSource Contribution:")
    for result in profile.source_results:
        quality = profile.quality_scores.get(result.source_name, 0)
        print(f"  {result.source_name.upper()}: {result.status.value} "
              f"({result.response_time_ms:.1f}ms) - Quality: {quality:.2f}")
    
    print("\n\nEXAMPLE 2: Caching Performance")
    print("-" * 70)
    
    import time
    
    user2 = UserInput(email="bob@example.com")
    
    start = time.time()
    profile2 = await engine.enrich(user2)
    time1 = (time.time() - start) * 1000
    print(f"First request: {time1:.1f}ms (no cache)")
    
    start = time.time()
    profile2_cached = await engine.enrich(user2)
    time2 = (time.time() - start) * 1000
    print(f"Second request: {time2:.1f}ms (from cache)")
    print(f"Speedup: {time1/max(time2, 0.1):.0f}x faster")
    
    print("\n\nEXAMPLE 3: Field-Level Confidence")
    print("-" * 70)
    
    print("Field Confidence Scores for Alice Smith:")
    for field_name, confidence in sorted(profile.field_confidence.items(),
                                        key=lambda x: x[1], reverse=True)[:8]:
        value = getattr(profile, field_name)
        if value:
            print(f"  {field_name:20} {confidence:6.2%}  ({value})")
    
    print("\n\nEXAMPLE 4: Complete JSON Profile")
    print("-" * 70)
    print(profile.to_json(indent=2))
    
    print("\n\nEXAMPLE 5: Engine Statistics")
    print("-" * 70)
    stats = engine.get_engine_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for subkey, subvalue in value.items():
                print(f"  {subkey}: {subvalue}")
        else:
            print(f"{key}: {value}")
    
    print("\n" + "="*70)
    print("  Demo completed successfully!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(demo())
