# C-01 UsageTracker + Budgets

## What & Why
As our AI system scales, controlling costs becomes critical. We need a robust way to track token usage across all LLM interactions and enforce budget caps to prevent unexpected cost overruns.

This task involves implementing the `UsageTracker` module which will track tokens used, store usage data in Redis, and enforce daily/monthly caps at both the agent and system level.

## Acceptance Criteria
- [ ] Create `shared/cost/usage_tracker.py` module
- [ ] Implement `UsageTracker` class with these key methods:
  - [ ] `track_usage()` - Records token usage for a completed LLM call
  - [ ] `check_budget()` - Verifies a planned LLM call fits within budget limits
  - [ ] `get_usage_report()` - Generates usage reports for monitoring
- [ ] Configure Redis storage for tracking with keys like `usage:{date}` that increment with usage
- [ ] Integrate with LLM service layer to track all API calls
- [ ] Implement configurable daily caps per agent type
- [ ] Return HTTP 429 (Too Many Requests) when daily cap is reached
- [ ] Add monitoring dashboard or CLI command to check current usage
- [ ] Create unit tests with Redis mocking
- [ ] Ensure multi-tenant isolation for usage tracking

## Implementation Notes
- Use the template from `docs/implementation-templates.md` as a starting point
- Maintain a local cache to reduce Redis calls
- Account for different cost models based on model type (e.g., GPT-4 costs more than GPT-3.5)
- Include a buffer mechanism (e.g., 95% warning) before hitting hard caps
- Reset counts at UTC midnight
- Consider different cap types:
  - Per agent instance
  - Per agent type
  - Per client/tenant
  - System-wide
- Design Redis keys for efficient querying:
  - `usage:{date}:total` - System-wide total
  - `usage:{date}:agent:{agent_id}` - Per agent
  - `usage:{date}:client:{client_id}` - Per client/tenant
  - `usage:{date}:model:{model_name}` - Per model

## Example Usage
```python
from shared.cost.usage_tracker import tracker

# Before making an LLM call
allowed, budget_info = await tracker.check_budget(
    agent_id="lead_research_1",
    estimated_tokens=500,
    model="gpt-4o"
)

if not allowed:
    raise Exception(f"Budget exceeded: {budget_info}")

# After receiving LLM response
await tracker.track_usage(
    tokens=response.usage.total_tokens,
    model="gpt-4o",
    agent_id="lead_research_1",
    operation_id="client_research_2025041901",
    metadata={"client_id": "acme_corp"}
)
```

## Related Files
- Implementation file: `shared/cost/usage_tracker.py`
- Configuration: `shared/config.py` (LLMSettings class)
- Integration point: `shared/services/llm/base_implementation.py`
- Test file: `tests/usage_tracker_test.py`
- Default config: `config/budgets.yaml`
