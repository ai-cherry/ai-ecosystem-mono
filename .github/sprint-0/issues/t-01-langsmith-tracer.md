# T-01 LangSmithTracer

## What & Why
We need observability into our LLM operations. Implementing the `LangSmithTracer` will provide us with detailed traces for every LLM call, making it possible to debug, optimize, and monitor our AI components.

Currently, we have a configuration for LangSmith but no actual implementation. This task involves creating the tracing middleware and integrating it into our LLM service to capture all model interactions.

## Acceptance Criteria
- [ ] Create `shared/observability/langsmith_tracer.py` module
- [ ] Implement `LangSmithTracer` class with these key methods:
  - [ ] `trace_llm_call()` - Records individual LLM API calls
  - [ ] `start_trace()` - Begins a trace for a complex operation (e.g., agent execution)
  - [ ] `end_trace()` - Completes a trace and records results
- [ ] Integrate tracer with our LLM service layer
- [ ] Ensure all LLM calls emit traces to LangSmith
- [ ] Verify that the LangSmith dashboard shows at least 1 span per agent
- [ ] Include proper error handling for when LangSmith is unreachable
- [ ] Add documentation for how to access and interpret traces
- [ ] Implement cost tracking per workflow type

## Implementation Notes
- Use the template from `docs/implementation-templates.md` as a starting point
- The tracer should be conditionally enabled based on `observability_settings.LANGSMITH_ENABLED`
- Provide a fallback logging mechanism when LangSmith is disabled or unreachable
- Use singleton pattern for easy access throughout the codebase
- Consider implementing as a decorator for easy application to functions
- Spans should include:
  - Model name and parameters
  - Prompt and response text
  - Token counts and estimated costs
  - Duration of calls
  - Relevant metadata (agent ID, operation type, etc.)

## Example Usage
```python
from shared.observability.langsmith_tracer import tracer

# In your LLM client class:
async def generate_text(self, prompt, model, max_tokens):
    # Call the LLM
    response = await self._call_llm_api(prompt, model, max_tokens)
    
    # Trace the call
    await tracer.trace_llm_call(
        prompt=prompt,
        response=response.text,
        model=model,
        tokens_used=response.usage.total_tokens,
        metadata={
            "operation": "text_generation",
            "agent_id": self.agent_id
        }
    )
    
    return response
```

## Related Files
- Implementation file: `shared/observability/langsmith_tracer.py`
- Configuration: `shared/config.py` (ObservabilitySettings class)
- Integration point: `shared/services/llm/base_implementation.py`
- Test file: `tests/langsmith_tracer_test.py`
