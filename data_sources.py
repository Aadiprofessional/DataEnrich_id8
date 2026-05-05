"""
Mock data sources that simulate real-world API behavior.
Includes realistic delays, failures, and varying data quality.
"""
#mock data souces
import asyncio
import random
from typing import Dict, Any, Optional
from models import SourceResult, SourceStatus
import logging

logger = logging.getLogger(__name__)


class MockDataSource:
    """Base class for mock data sources."""
    
    def __init__(self, name: str, failure_rate: float = 0.1, min_delay_ms: int = 100, 
                 max_delay_ms: int = 500):
        """
        Initialize mock data source.
        
        Args:
            name: Name of the source
            failure_rate: Probability of failure (0.0 to 1.0)
            min_delay_ms: Minimum response time in milliseconds
            max_delay_ms: Maximum response time in milliseconds
        """
        self.name = name
        self.failure_rate = failure_rate
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
    
    async def fetch(self, email: Optional[str] = None, phone: Optional[str] = None,
                    name: Optional[str] = None, timeout_ms: int = 2000) -> SourceResult:
        """
        Simulate fetching data from this source.
        
        Args:
            email: User email
            phone: User phone
            name: User name
            timeout_ms: Timeout in milliseconds
        
        Returns:
            SourceResult with status and data
        """
        import time
        start_time = time.time()
        
        try:
            delay_seconds = random.uniform(
                self.min_delay_ms / 1000.0,
                self.max_delay_ms / 1000.0
            )
            await asyncio.sleep(delay_seconds)
            
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms > timeout_ms:
                return SourceResult(
                    source_name=self.name,
                    status=SourceStatus.TIMEOUT,
                    error=f"Request timed out after {elapsed_ms:.0f}ms",
                    response_time_ms=elapsed_ms
                )
            
            if random.random() < self.failure_rate:
                return SourceResult(
                    source_name=self.name,
                    status=SourceStatus.FAILED,
                    error=f"API returned error: {random.choice(['Rate limit exceeded', 'Service unavailable', 'Invalid request'])}",
                    response_time_ms=(time.time() - start_time) * 1000
                )
            
            data = self._get_data(email, phone, name)
            response_time_ms = (time.time() - start_time) * 1000
            
            return SourceResult(
                source_name=self.name,
                status=SourceStatus.SUCCESS,
                data=data,
                response_time_ms=response_time_ms
            )
        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            return SourceResult(
                source_name=self.name,
                status=SourceStatus.TIMEOUT,
                error="Request timed out",
                response_time_ms=elapsed_ms
            )
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return SourceResult(
                source_name=self.name,
                status=SourceStatus.FAILED,
                error=str(e),
                response_time_ms=elapsed_ms
            )
    
    def _get_data(self, email: Optional[str], phone: Optional[str],
                  name: Optional[str]) -> Dict[str, Any]:
        """Override in subclass to return source-specific data."""
        raise NotImplementedError


class ClearbitSource(MockDataSource):
    """Mock Clearbit source - focuses on company info and professional data."""
    
    def __init__(self):
        super().__init__(
            name="clearbit",
            failure_rate=0.05,
            min_delay_ms=150,
            max_delay_ms=400
        )
    
    def _get_data(self, email: Optional[str], phone: Optional[str],
                  name: Optional[str]) -> Dict[str, Any]:
        """Return mock company and professional data."""
        companies = [
            {"name": "Acme Corp", "industry": "Technology", "url": "acme.com"},
            {"name": "Tech Solutions Inc", "industry": "Software", "url": "techsol.io"},
            {"name": "Digital Innovations", "industry": "Consulting", "url": "diginnovate.com"},
        ]
        titles = ["Senior Software Engineer", "Product Manager", "Data Scientist",
                  "Engineering Manager", "Solutions Architect"]
        
        company = random.choice(companies)
        
        return {
            "email": email or "john.doe@company.com",
            "full_name": name or "John Doe",
            "company_name": company["name"],
            "job_title": random.choice(titles),
            "industry": company["industry"],
            "website": company["url"],
            "linkedin_url": f"linkedin.com/in/{name.lower().replace(' ', '-')}" if name else "linkedin.com/in/john-doe"
        }


class HunterSource(MockDataSource):
    """Mock Hunter.io source - focuses on email and contact info."""
    
    def __init__(self):
        super().__init__(
            name="hunter",
            failure_rate=0.08,
            min_delay_ms=100,
            max_delay_ms=350
        )
    
    def _get_data(self, email: Optional[str], phone: Optional[str],
                  name: Optional[str]) -> Dict[str, Any]:
        """Return mock email and contact data."""
        cities = ["San Francisco", "New York", "Austin", "Seattle", "Boston"]
        states = ["CA", "NY", "TX", "WA", "MA"]
        
        idx = random.randint(0, len(cities) - 1)
        city = cities[idx]
        state = states[idx]
        
        return {
            "email": email or f"{name.lower().replace(' ', '.')}@company.com" if name else "contact@company.com",
            "full_name": name or "John Doe",
            "phone": phone or f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}",
            "city": city,
            "state": state,
            "country": "United States",
            "postal_code": f"{random.randint(10000, 99999)}"
        }


class CustomDBSource(MockDataSource):
    """Mock custom internal database source - slower but comprehensive."""
    
    def __init__(self):
        super().__init__(
            name="custom_db",
            failure_rate=0.10,
            min_delay_ms=300,
            max_delay_ms=600
        )
    
    def _get_data(self, email: Optional[str], phone: Optional[str],
                  name: Optional[str]) -> Dict[str, Any]:
        """Return mock internal database data."""
        handles = ["@john_d", "@johndoe", "@j_doe", "@jdoe2024"]
        
        return {
            "full_name": name or "John Doe",
            "email": email or "john@example.com",
            "twitter_handle": random.choice(handles),
            "company_name": random.choice(["TechCorp", "DataInc", "CloudBase"]),
            "job_title": random.choice(["Engineer", "Analyst", "Developer"]),
            "city": random.choice(["San Francisco", "New York", "Chicago"]),
            "state": random.choice(["CA", "NY", "IL"]),
            "country": "United States",
            "website": f"https://{random.choice(['example.com', 'portfolio.dev', 'mysite.io'])}"
        }


async def test_sources():
    """Test all mock sources."""
    sources = [ClearbitSource(), HunterSource(), CustomDBSource()]
    
    test_input = {
        "email": "test@example.com",
        "phone": "+1-555-0100",
        "name": "Alice Smith"
    }
    
    print("Testing Mock Data Sources\n" + "="*50)
    
    for source in sources:
        print(f"\nTesting {source.name}...")
        result = await source.fetch(**test_input)
        print(f"  Status: {result.status.value}")
        print(f"  Response Time: {result.response_time_ms:.1f}ms")
        if result.status == SourceStatus.SUCCESS:
            for key, value in result.data.items():
                print(f"  {key}: {value}")
        else:
            print(f"  Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(test_sources())
