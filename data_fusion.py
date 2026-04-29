"""
Data fusion logic for merging data from multiple sources.
Handles conflicts, missing data, and quality scoring.
"""

from typing import Dict, Any, List, Tuple, Optional
from models import SourceResult, SourceStatus, EnrichedProfile, UserInput
from config import EnrichmentConfig
import logging

logger = logging.getLogger(__name__)


class ConflictResolutionStrategy:
    """Strategies for resolving conflicting data from multiple sources."""
    
    @staticmethod
    def weighted_priority(values: Dict[str, Any], sources: Dict[str, int]) -> Tuple[Any, float]:
        """
        Resolve conflicts using weighted priority scores.
        Higher priority sources win in case of conflict.
        
        Args:
            values: Dict mapping source names to values
            sources: Dict mapping source names to priority scores (0-10)
        
        Returns:
            Tuple of (selected_value, confidence)
        """
        if not values:
            return None, 0.0
        
        valid_values = {k: v for k, v in values.items() if v is not None and v != ""}
        if not valid_values:
            return None, 0.0
        
        if len(valid_values) == 1:
            source_name = list(valid_values.keys())[0]
            priority = sources.get(source_name, 5)
            confidence = min(0.95, (priority / 10.0) * 0.95)
            return list(valid_values.values())[0], confidence
        
        best_source = max(valid_values.keys(), 
                         key=lambda x: sources.get(x, 5))
        best_value = valid_values[best_source]
        best_priority = sources.get(best_source, 5)
        
        unique_values = set(valid_values.values())
        if len(unique_values) == 1:
            confidence = 0.95
        else:
            num_sources = len(valid_values)
            num_agreeing = sum(1 for v in valid_values.values() if v == best_value)
            agreement_ratio = num_agreeing / num_sources
            confidence = (best_priority / 10.0) * agreement_ratio * 0.85
        
        return best_value, confidence
    
    @staticmethod
    def majority_vote(values: Dict[str, Any]) -> Tuple[Any, float]:
        """
        Resolve conflicts using majority voting.
        
        Args:
            values: Dict mapping source names to values
        
        Returns:
            Tuple of (selected_value, confidence)
        """
        if not values:
            return None, 0.0
        
        valid_values = [v for v in values.values() if v is not None and v != ""]
        if not valid_values:
            return None, 0.0
        
        if len(valid_values) == 1:
            return valid_values[0], 0.85
        
        value_counts = {}
        for v in valid_values:
            value_counts[str(v)] = value_counts.get(str(v), 0) + 1
        
        most_common = max(value_counts.items(), key=lambda x: x[1])
        most_common_value = most_common[0]
        count = most_common[1]
        
        for v in valid_values:
            if str(v) == most_common_value:
                most_common_value = v
                break
        
        confidence = (count / len(valid_values)) * 0.95
        return most_common_value, confidence


class DataFusionEngine:
    """Engine for fusing data from multiple sources."""
    
    def __init__(self, config: Optional[EnrichmentConfig] = None):
        """
        Initialize fusion engine.
        
        Args:
            config: Enrichment configuration
        """
        self.config = config or EnrichmentConfig()
        self.source_priorities = self._build_source_priorities()
    
    def _build_source_priorities(self) -> Dict[str, int]:
        """Build a mapping of source names to priority scores."""
        priorities = {}
        for ds_config in self.config.data_sources:
            score = (ds_config.priority * 3) + int(ds_config.reliability_score * 4)
            priorities[ds_config.name] = min(10, score)
        return priorities
    
    def merge_results(self, source_results: List[SourceResult],
                      user_input: UserInput) -> EnrichedProfile:
        """
        Merge results from multiple sources into a single profile.
        
        Args:
            source_results: List of results from different sources
            user_input: Original user input
        
        Returns:
            EnrichedProfile with merged data and quality scores
        """
        profile = EnrichedProfile(user_input=user_input)
        profile.source_results = source_results
        
        field_data = self._organize_by_field(source_results)
        
        for field_name, source_values in field_data.items():
            if not source_values:
                continue
            
            value, confidence = ConflictResolutionStrategy.weighted_priority(
                source_values,
                self.source_priorities
            )
            
            if value is not None:
                setattr(profile, field_name, value)
                profile.field_confidence[field_name] = confidence
        
        self._calculate_quality_scores(profile, source_results)
        
        return profile
    
    def _organize_by_field(self, source_results: List[SourceResult]) -> Dict[str, Dict[str, Any]]:
        """
        Organize source data by field name.
        
        Args:
            source_results: List of source results
        
        Returns:
            Dict mapping field names to dict of {source_name: value}
        """
        field_data = {}
        
        field_mapping = {
            "full_name": ["full_name", "name"],
            "email": ["email"],
            "phone": ["phone"],
            "company_name": ["company_name"],
            "job_title": ["job_title"],
            "city": ["city"],
            "state": ["state"],
            "country": ["country"],
            "postal_code": ["postal_code"],
            "industry": ["industry"],
            "linkedin_url": ["linkedin_url"],
            "twitter_handle": ["twitter_handle"],
            "website": ["website", "url", "web_url"]
        }
        
        for result in source_results:
            if result.status != SourceStatus.SUCCESS or not result.data:
                continue
            
            for canonical_field, source_fields in field_mapping.items():
                for source_field in source_fields:
                    if source_field in result.data:
                        if canonical_field not in field_data:
                            field_data[canonical_field] = {}
                        field_data[canonical_field][result.source_name] = result.data[source_field]
                        break
        
        return field_data
    
    def _calculate_quality_scores(self, profile: EnrichedProfile,
                                  source_results: List[SourceResult]) -> None:
        """
        Calculate quality scores for the enriched profile.
        
        Args:
            profile: EnrichedProfile to score
            source_results: List of source results
        """
        for result in source_results:
            if result.status == SourceStatus.SUCCESS:
                num_fields = len(result.data) if result.data else 0
                score = (num_fields / 8.0) * 0.9
                profile.quality_scores[result.source_name] = min(1.0, score)
            elif result.status == SourceStatus.TIMEOUT:
                profile.quality_scores[result.source_name] = 0.0
            else:
                profile.quality_scores[result.source_name] = 0.0
        
        if not profile.field_confidence:
            profile.overall_quality_score = 0.0
            return
        
        populated_fields = sum(1 for cf in profile.field_confidence.values() if cf > 0)
        possible_fields = len(profile.field_confidence)
        coverage_score = populated_fields / max(1, possible_fields)
        
        avg_confidence = sum(profile.field_confidence.values()) / max(1, len(profile.field_confidence))
        
        successful_sources = sum(1 for r in source_results if r.status == SourceStatus.SUCCESS)
        total_sources = len(source_results)
        source_success_rate = successful_sources / max(1, total_sources)
        
        overall_score = (
            coverage_score * 0.4 +
            avg_confidence * 0.35 +
            source_success_rate * 0.25
        )
        
        profile.overall_quality_score = overall_score
        
        profile.is_complete = profile.overall_quality_score >= self.config.min_quality_threshold
    
    def get_fusion_report(self, profile: EnrichedProfile) -> str:
        """
        Generate a human-readable report of the fusion process.
        
        Args:
            profile: EnrichedProfile to report on
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("\n" + "="*60)
        report.append("DATA FUSION REPORT")
        report.append("="*60)
        
        report.append("\nPROFILE STATUS")
        report.append(f"  Complete: {'Yes' if profile.is_complete else 'No (Partial)'}")
        report.append(f"  Overall Quality: {profile.overall_quality_score:.2%}")
        report.append(f"  Processing Time: {profile.processing_time_ms:.1f}ms")
        
        report.append("\nSOURCE RESULTS")
        for sr in profile.source_results:
            report.append(f"  {sr.source_name.upper()}")
            report.append(f"    Status: {sr.status.value}")
            report.append(f"    Response Time: {sr.response_time_ms:.1f}ms")
            report.append(f"    Quality Score: {profile.quality_scores.get(sr.source_name, 0):.2f}")
            if sr.error:
                report.append(f"    Error: {sr.error}")
        
        report.append("\nMERGED DATA & CONFIDENCE")
        fields_to_show = [
            ("full_name", "Full Name"),
            ("email", "Email"),
            ("phone", "Phone"),
            ("company_name", "Company"),
            ("job_title", "Job Title"),
            ("city", "City"),
            ("state", "State"),
            ("country", "Country"),
            ("linkedin_url", "LinkedIn"),
            ("twitter_handle", "Twitter"),
            ("website", "Website")
        ]
        
        for field_name, display_name in fields_to_show:
            value = getattr(profile, field_name)
            confidence = profile.field_confidence.get(field_name, 0)
            if value:
                report.append(f"  {display_name}: {value} [{confidence:.2%}]")
        
        report.append("\n" + "="*60 + "\n")
        return "\n".join(report)


if __name__ == "__main__":
    from config import DEFAULT_CONFIG
    
    results = [
        SourceResult(
            source_name="clearbit",
            status=SourceStatus.SUCCESS,
            data={"full_name": "Alice Smith", "company_name": "TechCorp", "job_title": "Engineer"},
            response_time_ms=200
        ),
        SourceResult(
            source_name="hunter",
            status=SourceStatus.SUCCESS,
            data={"email": "alice@example.com", "phone": "+1-555-0100", "city": "San Francisco"},
            response_time_ms=150
        ),
        SourceResult(
            source_name="custom_db",
            status=SourceStatus.SUCCESS,
            data={"full_name": "Alice Smith", "website": "alice.dev"},
            response_time_ms=400
        ),
    ]
    
    user_input = UserInput(email="alice@example.com")
    
    engine = DataFusionEngine(DEFAULT_CONFIG)
    profile = engine.merge_results(results, user_input)
    
    print(engine.get_fusion_report(profile))
    print("\nJSON Output:")
    print(profile.to_json())
