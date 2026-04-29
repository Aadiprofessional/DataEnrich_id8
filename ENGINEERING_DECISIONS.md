# Engineering Thinking

### 1. Scalability: How would you scale this system to handle high volumes (e.g., 1M users/day)?

To scale to 1M users/day (~35 requests/second at peak), I'd implement a distributed architecture with horizontal scaling. First, I'd add a load balancer (nginx or HAProxy) to distribute traffic across multiple enrichment engine instances running in Kubernetes with auto-scaling. Each instance can handle ~50 concurrent requests, so 4-5 instances would cover peak load.

The biggest change would be replacing the in-memory cache with Redis Cluster for distributed caching. This ensures cache hits across all instances and provides horizontal scalability. I'd also implement a message queue (RabbitMQ or Kafka) to buffer incoming requests during traffic spikes, preventing overload.

For the external APIs, I'd implement adaptive rate limiting with exponential backoff to stay within their limits. If one API hits its rate limit, the system continues processing with the remaining sources. With a 70-90% cache hit rate from Redis, actual API calls drop to ~3-5 requests/second, well within typical API limits.

### 2. Bottlenecks: What are the top 2–3 bottlenecks in your design?

**Bottleneck #1: External API Rate Limits**
The primary bottleneck is the rate limits imposed by Clearbit, Hunter, and other external APIs (typically 100-1000 requests/minute). During peak traffic, we can easily exceed these limits, causing 429 errors and failed enrichments. The current retry logic helps but doesn't solve the fundamental constraint. This directly impacts the quality of enrichment results when APIs are throttled.

**Bottleneck #2: In-Memory Cache Scalability**
The current SimpleCache is limited to a single machine's memory. With 1M unique users, the cache would quickly exceed available RAM, leading to high cache miss rates. Cache misses are expensive because they require full API calls to all three sources, dramatically increasing latency and API costs. This also creates inconsistent performance across instances in a scaled deployment.

**Bottleneck #3: Slowest Source Latency**
The concurrent fetch design waits for all three sources to complete (or timeout), so the total response time is bounded by the slowest source. If one API is experiencing delays (network issues, server load, etc.), the entire enrichment request takes longer. The 2-second per-source timeout helps, but doesn't eliminate the impact of consistently slow sources on the 99th percentile latency.

### 3. Cost Optimization: How would you reduce dependency or cost of external APIs?

The most effective cost reduction is implementing aggressive caching. With Redis distributed cache and a 1-hour TTL, I'd expect 70-90% cache hit rates for typical workloads. This alone reduces API costs by 70-90% since cached requests don't hit external APIs at all.

For the remaining API calls, I'd implement smart batching—combining multiple user enrichments into a single API call where supported. This reduces per-request costs by 15-25%. I'd also negotiate volume discounts with API providers; at 1M users/day, we have significant leverage for 20-30% discounts.

Longer-term, I'd build an internal enrichment database. After the first year of operation, we'd have enriched ~365M profiles. Many of these users return (40-50% in typical SaaS), so we can answer their enrichment requests from our internal database instead of calling external APIs. This creates a compounding cost reduction over time.

Finally, I'd implement tiered enrichment based on customer value. High-value customers get full 3-source enrichment, while lower-tier customers get lighter enrichment from fewer sources. This prioritizes API spend where it generates the most revenue.
