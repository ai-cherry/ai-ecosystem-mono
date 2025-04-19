# A-01 LeadResearchAgent Full Implementation

## What & Why
The `LeadResearchAgent` is a core component in our sales workflow, responsible for gathering, analyzing, and synthesizing information about potential leads. While the agent class exists, it's currently just a skeleton without the actual implementation of the required methods.

This task requires implementing the complete `LeadResearchAgent` with working `plan()` and `act()` methods that can process input from Apollo and LinkedIn, analyze the information, and produce a structured lead profile.

## Acceptance Criteria
- [ ] Implement `plan()` method in `LeadResearchAgent` class that creates a structured research plan
- [ ] Implement `act()` method that executes the plan and gathers lead information
- [ ] Create unit tests with mock HTML data from Apollo and LinkedIn
- [ ] Tests should verify the agent returns a populated `LeadProfile` object
- [ ] Ensure the agent extracts key information:
  - [ ] Company details (size, industry, funding)
  - [ ] Contact information
  - [ ] Decision makers
  - [ ] Recent company news/developments
  - [ ] Potential pain points
- [ ] Add proper error handling for malformed inputs
- [ ] Agent should use memory for context and to store results
- [ ] All tests must pass when run with pytest

## Implementation Notes
- Use the template from `docs/implementation-templates.md` as a starting point
- Leverage the existing `BaseSalesAgent` class for core functionality
- Use Agno for reasoning rather than direct LangChain agents
- Consider implementing these tools:
  - Apollo data extractor
  - LinkedIn profile parser
  - Company website scraper
  - News aggregator
- The implementation should follow the pattern in the implementation summary document
- Pay special attention to error handling for cases where:
  - LinkedIn or Apollo data is unavailable
  - Company information is sparse
  - Multiple potential matches exist

## Example Structure for LeadProfile
```python
class LeadProfile:
    """Structured data about a sales lead."""
    company_name: str
    industry: str
    size: str  # e.g., "50-200 employees"
    location: str
    founded_year: Optional[int]
    funding: Optional[str]
    
    # Key people
    ceo: Optional[str]
    decision_makers: List[Dict[str, str]]  # [{name, title, contact}]
    
    # Contact info
    website: str
    phone: Optional[str]
    email: Optional[str]
    
    # Business intelligence
    recent_news: List[str]
    technologies_used: List[str]
    competitors: List[str]
    pain_points: List[str]
    opportunities: List[str]
    
    # Agent analysis
    summary: str
    engagement_strategy: str
    estimated_deal_size: str
    probability: float  # 0.0 to 1.0
```

## Related Files
- Main implementation: `agents/sales/lead_research.py`
- Base class: `agents/base/sales_agent_base.py`
- Test file: `tests/lead_research_agent_test.py`
- Mock data: `tests/fixtures/apollo_response.html`, `tests/fixtures/linkedin_profile.html`
