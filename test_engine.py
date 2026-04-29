"""
Comprehensive test and demo script for the Data Enrichment Pipeline.
Demonstrates all features including concurrency, caching, retries, conflict resolution, and quality scoring.
"""

import asyncio
import json
import sys
from typing import List

from models import UserInput, SourceStatus, SourceResult
from config import EnrichmentConfig, DataSourceConfig
from enrichment_engine import EnrichmentEngine
from data_sources import ClearbitSource, HunterSource, CustomDBSource
from data_fusion import DataFusionEngine


class TestSuite:
    """Test suite for the enrichment engine."""
    
    def __init__(self):
        """Initialize test suite."""
        self.passed = 0
        self.failed = 0
        self.total = 0
    
    def print_header(self, title: str):
        """Print test header."""
        print("\n" + "="*70)
        print(f"  {title}")
        print("="*70 + "\n")
    
    def print_test(self, name: str, passed: bool, message: str = ""):
        """Print test result."""
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  [{status}] {name}")
        if message:
            print(f"       {message}")
        self.total += 1
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print(f"  TEST SUMMARY: {self.passed}/{self.total} passed")
        print("="*70 + "\n")
        return self.failed == 0


async def test_basic_enrichment():
    """Test 1: Basic enrichment with all sources succeeding."""
    print("\n--- Test 1: Basic Enrichment (All Sources Succeeding) ---\n")
    
    engine = EnrichmentEngine()
    user_input = UserInput(email="test@example.com", name="Test User")
    
    profile = await engine.enrich(user_input)
    
    print(f"Quality Score: {profile.overall_quality_score:.2%}")
    print(f"Is Complete: {profile.is_complete}")
    print(f"Processing Time: {profile.processing_time_ms:.1f}ms")
    print(f"\nProfile Data:")
    print(f"  Name: {profile.full_name}")
    print(f"  Email: {profile.email}")
    print(f"  Company: {profile.company_name}")
    print(f"  Job Title: {profile.job_title}")
    
    print(f"\nSource Results:")
    for sr in profile.source_results:
        print(f"  {sr.source_name}: {sr.status.value} ({sr.response_time_ms:.1f}ms)")
    
    return profile.overall_quality_score > 0.3 and len(profile.source_results) == 3


async def test_conflict_resolution():
    """Test 2: Conflict resolution when sources provide different data."""
    print("\n--- Test 2: Conflict Resolution ---\n")
    
    from data_fusion import ConflictResolutionStrategy
    
    conflicting_values = {
        "clearbit": "Acme Corp",
        "hunter": "Acme Corporation",
        "custom_db": "Acme Inc"
    }
    
    source_priorities = {
        "clearbit": 9,
        "hunter": 8,
        "custom_db": 7
    }
    
    value, confidence = ConflictResolutionStrategy.weighted_priority(
        conflicting_values,
        source_priorities
    )
    
    print(f"Conflicting values: {conflicting_values}")
    print(f"Resolution strategy: Weighted Priority")
    print(f"Selected value: {value}")
    print(f"Confidence: {confidence:.2%}")
    print(f"Winner (highest priority): clearbit")
    
    return value == "Acme Corp" and confidence > 0


async def test_caching():
    """Test 3: Caching reduces processing time for duplicate requests."""
    print("\n--- Test 3: Caching ---\n")
    
    engine = EnrichmentEngine()
    user_input = UserInput(email="cache-test@example.com")
    
    start1 = asyncio.get_event_loop().time()
    profile1 = await engine.enrich(user_input)
    time1 = (asyncio.get_event_loop().time() - start1) * 1000
    
    start2 = asyncio.get_event_loop().time()
    profile2 = await engine.enrich(user_input)
    time2 = (asyncio.get_event_loop().time() - start2) * 1000
    
    print(f"First request (no cache): {time1:.1f}ms")
    print(f"Second request (cached): {time2:.1f}ms")
    print(f"Time reduction: {(1 - time2/time1)*100:.1f}%")
    
    cache_stats = engine.cache.get_stats()
    print(f"Cache entries: {cache_stats['entries']}")
    
    return time2 < time1 and profile1.overall_quality_score == profile2.overall_quality_score


async def test_partial_failure():
    """Test 4: Engine continues even if one source fails."""
    print("\n--- Test 4: Partial Failure (Some Sources Unavailable) ---\n")
    
    unreliable_source = ClearbitSource()
    unreliable_source.failure_rate = 0.8
    
    sources = [unreliable_source, HunterSource(), CustomDBSource()]
    engine = EnrichmentEngine(data_sources=sources)
    
    user_input = UserInput(email="partial-test@example.com")
    profile = await engine.enrich(user_input)
    
    print(f"Profile Status: {'Complete' if profile.is_complete else 'Partial'}")
    print(f"Quality Score: {profile.overall_quality_score:.2%}")
    print(f"Processing Time: {profile.processing_time_ms:.1f}ms")
    
    print(f"\nSource Status Summary:")
    successful = 0
    for sr in profile.source_results:
        status_str = sr.status.value
        if sr.status == SourceStatus.SUCCESS:
            successful += 1
        print(f"  {sr.source_name}: {status_str}")
    
    print(f"\nSuccessful sources: {successful}/3")
    
    return profile.full_name is not None or profile.email is not None


async def test_timeout_handling():
    """Test 5: Timeout handling and enforcement."""
    print("\n--- Test 5: Timeout Handling ---\n")
    
    config = EnrichmentConfig(
        total_timeout_ms=500,
        source_timeout_ms=200
    )
    
    engine = EnrichmentEngine(config=config)
    user_input = UserInput(email="timeout-test@example.com")
    
    profile = await engine.enrich(user_input)
    
    print(f"Total timeout limit: {config.total_timeout_ms}ms")
    print(f"Source timeout limit: {config.source_timeout_ms}ms")
    print(f"Actual processing time: {profile.processing_time_ms:.1f}ms")
    print(f"Within limit: {profile.processing_time_ms <= config.total_timeout_ms}")
    
    print(f"\nSource Results:")
    for sr in profile.source_results:
        print(f"  {sr.source_name}: {sr.response_time_ms:.1f}ms - {sr.status.value}")
    
    return profile.processing_time_ms <= config.total_timeout_ms


async def test_quality_scoring():
    """Test 6: Quality scoring and confidence calculation."""
    print("\n--- Test 6: Quality Scoring & Confidence ---\n")
    
    engine = EnrichmentEngine()
    user_input = UserInput(email="quality-test@example.com")
    
    profile = await engine.enrich(user_input)
    
    print(f"Overall Quality Score: {profile.overall_quality_score:.2%}")
    print(f"Profile Completeness: {'Complete' if profile.is_complete else 'Partial'}")
    
    print(f"\nField-Level Confidence Scores:")
    for field_name, confidence in sorted(profile.field_confidence.items(), key=lambda x: x[1], reverse=True):
        value = getattr(profile, field_name)
        if value:
            print(f"  {field_name}: {confidence:.2%} ({value})")
    
    print(f"\nSource Quality Scores:")
    for source_name, score in sorted(profile.quality_scores.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source_name}: {score:.2f}")
    
    return profile.overall_quality_score >= 0.0 and profile.overall_quality_score <= 1.0


async def test_multiple_inputs():
    """Test 7: Multiple different user inputs."""
    print("\n--- Test 7: Multiple User Inputs ---\n")
    
    engine = EnrichmentEngine()
    
    test_cases = [
        UserInput(email="alice@example.com"),
        UserInput(phone="+1-555-0100", name="Bob Smith"),
        UserInput(name="Charlie Brown"),
        UserInput(email="diana@example.com", phone="+1-555-0101"),
    ]
    
    print(f"Processing {len(test_cases)} different user inputs...\n")
    
    results = []
    for i, user_input in enumerate(test_cases, 1):
        profile = await engine.enrich(user_input)
        results.append(profile)
        print(f"  [{i}] {str(user_input)}")
        print(f"      Quality: {profile.overall_quality_score:.2%} | Complete: {profile.is_complete} | Time: {profile.processing_time_ms:.1f}ms")
    
    return all(r.overall_quality_score > 0 for r in results)


async def test_retry_logic():
    """Test 8: Retry logic for failed requests."""
    print("\n--- Test 8: Retry Logic ---\n")
    
    config = EnrichmentConfig(
        enable_retry=True,
        max_retries_per_source=3,
        retry_backoff_ms=50
    )
    
    engine = EnrichmentEngine(config=config)
    user_input = UserInput(email="retry-test@example.com")
    
    profile = await engine.enrich(user_input)
    
    print(f"Retry enabled: {config.enable_retry}")
    print(f"Max retries per source: {config.max_retries_per_source}")
    print(f"Backoff: {config.retry_backoff_ms}ms")
    
    print(f"\nSource Results:")
    successful = 0
    for sr in profile.source_results:
        if sr.status == SourceStatus.SUCCESS:
            successful += 1
        print(f"  {sr.source_name}: {sr.status.value}")
    
    print(f"\nSuccessful after retries: {successful}/3")
    
    return successful > 0


async def test_empty_source_handling():
    """Test 9: Handling of empty or None fields."""
    print("\n--- Test 9: Empty/None Field Handling ---\n")
    
    from data_fusion import ConflictResolutionStrategy
    
    values_with_nones = {
        "clearbit": None,
        "hunter": "",
        "custom_db": "Valid Value"
    }
    
    value, confidence = ConflictResolutionStrategy.weighted_priority(
        values_with_nones,
        {"clearbit": 9, "hunter": 8, "custom_db": 7}
    )
    
    print(f"Input values: {values_with_nones}")
    print(f"Result: {value}")
    print(f"Confidence: {confidence:.2%}")
    print(f"Correctly selected non-None value: {value == 'Valid Value'}")
    
    return value == "Valid Value"


async def test_concurrent_performance():
    """Test 10: Concurrent request handling performance."""
    print("\n--- Test 10: Concurrent Request Performance ---\n")
    
    engine = EnrichmentEngine()
    
    requests = [
        UserInput(email=f"concurrent{i}@example.com") for i in range(5)
    ]
    
    import time
    start = time.time()
    
    profiles = await asyncio.gather(*[
        engine.enrich(req) for req in requests
    ])
    
    elapsed = time.time() - start
    
    print(f"Concurrent requests: {len(requests)}")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Average time per request: {(elapsed/len(requests)):.2f}s")
    
    print(f"\nResults Summary:")
    for i, profile in enumerate(profiles, 1):
        print(f"  Request {i}: Quality {profile.overall_quality_score:.2%} | Complete: {profile.is_complete}")
    
    return all(p.overall_quality_score > 0 for p in profiles)


async def run_all_tests():
    """Run all tests."""
    suite = TestSuite()
    suite.print_header("DATA ENRICHMENT PIPELINE - COMPREHENSIVE TEST SUITE")
    
    tests = [
        ("Basic Enrichment", test_basic_enrichment),
        ("Conflict Resolution", test_conflict_resolution),
        ("Caching", test_caching),
        ("Partial Failure Handling", test_partial_failure),
        ("Timeout Handling", test_timeout_handling),
        ("Quality Scoring", test_quality_scoring),
        ("Multiple Inputs", test_multiple_inputs),
        ("Retry Logic", test_retry_logic),
        ("Empty/None Handling", test_empty_source_handling),
        ("Concurrent Performance", test_concurrent_performance),
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            suite.print_test(test_name, result)
        except Exception as e:
            print(f"\nException in {test_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            suite.print_test(test_name, False, str(e))
    
    success = suite.print_summary()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
