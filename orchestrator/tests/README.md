# Multi-Agent Integration Tests

This directory contains comprehensive integration tests that simulate the end-to-end flow through the various components of the AI ecosystem:

1. Async API → 
2. Temporal Workflow → 
3. Memory Systems → 
4. LLM Services

The tests validate:
- Success paths
- Failure and fallback paths
- Memory persistence
- Multi-turn conversations

## Test Structure

- `test_integration.py`: Basic mock implementations and component tests
- `test_enhanced_workflow.py`: End-to-end workflow tests using enhanced implementations

## Running the Tests

To run all integration tests:

```bash
cd orchestrator
python -m pytest tests/ -v
```

To run a specific test file:

```bash
cd orchestrator
python -m pytest tests/test_enhanced_workflow.py -v
```

To run a specific test function:

```bash
cd orchestrator
python -m pytest tests/test_enhanced_workflow.py::test_enhanced_workflow_success -v
```

## Test Environment Requirements

The tests use extensive mocking to avoid requiring actual running services. However, the following packages are required:

- pytest
- pytest-asyncio
- fastapi
- uvicorn
- temporalio
- redis (mock implementation used in tests)
- langchain (mock implementation used in tests)

These dependencies are already included in the `requirements.txt` file.

## Test Coverage

The integration tests cover the following key scenarios:

1. **Success Path**: Complete flow from API request to LLM processing and result storage
2. **Failure Handling**: LLM service failures with proper fallback mechanisms
3. **Memory Persistence**: Verifying that conversation history is correctly maintained
4. **Workflow Retry Logic**: Testing retry behavior for transient failures
5. **Multi-turn Conversations**: Testing the persistence of context across multiple interactions

## Mock Implementations

To facilitate testing without external dependencies, the tests include the following mock implementations:

- **MockTemporalClient**: Simulates the Temporal workflow engine
- **MockMemory**: In-memory implementation of the memory interfaces
- **MockLLMService**: Controlled LLM service simulation for testing various scenarios
