# M-01 Memory Tests

## What & Why
Our `MemoryManager` implementation is critical to the entire system's functionality, supporting all agents with its multi-layer memory operations. We need comprehensive test coverage to ensure reliability.

Currently, we have stubs for memory tests, but they are not implemented. This task requires implementing these tests to reach ≥90% branch coverage for `shared/memory/memory_manager.py` and related memory components.

Good test coverage will prevent regressions, validate the core functionality of our memory system, and ensure all memory layers (Redis, Firestore, Pinecone, Weaviate) are working correctly together.

## Acceptance Criteria
- [ ] Implement comprehensive tests for `memory_manager.py` reaching ≥90% branch coverage
- [ ] Tests must cover all key methods:
  - [ ] `retrieve()`
  - [ ] `store()`
  - [ ] `summarize_and_archive()`
  - [ ] `prune_old()`
  - [ ] `score_importance()`
- [ ] Include mocking for all external dependencies (Redis, Firestore, Pinecone, Weaviate)
- [ ] Tests run successfully in CI pipeline
- [ ] Ensure tests validate multi-tenant isolation with `client_id` separation
- [ ] Add tests for error handling and edge cases

## Implementation Notes
- Use pytest fixtures for dependency injection
- Consider using pytest-asyncio for testing async methods
- Use unittest.mock for mocking external dependencies
- Implement both unit tests and integration tests
- Add test for the multi-layer operations (e.g., testing that `store()` correctly writes to all appropriate layers)

## Related Files
- Main implementation: `shared/memory/memory_manager.py`
- Test file location: `tests/memory_manager_test.py`
- Other related files:
  - `shared/memory/redis.py`
  - `shared/memory/firestore.py`
  - `shared/memory/vectorstore.py`
  - `shared/memory/interfaces.py`
