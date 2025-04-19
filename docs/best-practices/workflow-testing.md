# Workflow & Testing Best Practices

This guide documents the enhancements made to the workflow and testing pipelines in the AI Ecosystem. These improvements focus on dependency hygiene, test coverage, observability, deterministic testing, and memory consistency.

## 1. Dependency Hygiene

We've migrated from `requirements.txt` to Poetry for better dependency management:

- Added `pyproject.toml` files to each component (orchestrator, shared, agents)
- Dependencies are locked with exact versions via Poetry
- Added `Makefile` with `deps` target to re-lock dependencies and verify upstream compatibility
- Nightly CI job checks for broken upstream releases

### Usage

```bash
# Re-lock dependencies for all components
make deps

# Re-lock dependencies for a specific component
make deps-orchestrator
```

## 2. Test Matrix & Coverage

Implemented a comprehensive test strategy with multiple layers:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components
- **End-to-End Tests**: Test complete workflows
- **Contract Tests**: Test against real services (Redis, Pinecone) instead of mocks

GitHub Actions workflows now run these tests with path-filtering to only test changed components.

### Coverage Requirements

- Minimum 80% code coverage required for all components
- Coverage badges are automatically generated in CI
- PRs include coverage reports as comments

## 3. LangSmith & Temporal Trace Observability

Enhanced observability for LLM operations and workflow executions:

- All LLM calls are automatically traced with LangSmith (`LANGCHAIN_TRACING_V2="true"`)
- Temporal Web UI is available on port 8233 in development environments
- Admin UI includes "view trace" buttons for quick access to LangSmith and Temporal traces

### Environment Setup

```
# Add to .env file
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_API_KEY="your_langsmith_api_key"
LANGCHAIN_PROJECT="ai-ecosystem"
```

## 4. Deterministic LLM Testing

Implemented strategies for reliable LLM testing:

- **Seeded Models**: Pass seed values to supported models like GPT-4o and Claude 3
- **Snapshot Testing**: Store canonical outputs for reproducible tests
- **Structure-Only Assertions**: Validate response structure rather than exact content for non-seedable models
- **Cosine Similarity**: Compare embedding vectors instead of raw text

### Example: Seeded Model Test

```python
from orchestrator.app.services.llm.base import LLMService

def test_deterministic_response():
    # Create service with fixed seed
    llm_service = LLMService(seed=42)
    
    # Both calls should return identical responses
    result1 = llm_service.process("Tell me a joke")
    result2 = llm_service.process("Tell me a joke")
    
    assert result1["content"] == result2["content"]
```

## 5. Synthetic Load & Chaos Testing

Added load testing and chaos engineering:

- Grafana k6 script for load testing the API endpoints
- Chaos tests that simulate Redis failures during operation
- SLO alerts for latency and error rates

### Running Load Tests

```bash
# Run basic load test
k6 run orchestrator/tests/load/basic_load_test.js

# Run with environment variables
k6 run --env BASE_URL=http://localhost:8000 orchestrator/tests/load/basic_load_test.js
```

## 6. Memory Consistency Audits

Implemented memory system integrity checks:

- Nightly workflow audits Redis, Firestore, and Vector store consistency
- Detects orphaned vectors, missing embeddings, and expired sessions
- Auto-cleanup of expired sessions

### Running Memory Audits

```python
from temporalio.client import Client
from orchestrator.workflows.memory_audit import start_memory_audit

async def run_memory_audit():
    client = await Client.connect("localhost:7233")
    handle = await start_memory_audit(client, perform_cleanup=True)
    result = await handle.result()
    print(f"Audit complete: {result['health_status']}")
    if result['issues']:
        print("Issues found:")
        for issue in result['issues']:
            print(f"- {issue}")
```

## Developer Quick-Start Guide

1. Clone the repository
2. Install dependencies with Poetry:
   ```bash
   cd orchestrator && poetry install --no-root
   cd ../shared && poetry install --no-root
   cd ../agents && poetry install --no-root
   ```
3. Set up environment variables in `.env` files
4. Run tests:
   ```bash
   make test
   ```
5. Start the development server:
   ```bash
   cd orchestrator && poetry run uvicorn app.main:app --reload
   ```
6. In a separate terminal, start Temporal worker:
   ```bash
   cd orchestrator && poetry run python workers/worker_main.py
   ```
7. Access Temporal Web UI at http://localhost:8233
