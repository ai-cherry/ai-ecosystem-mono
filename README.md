# AI Ecosystem Monorepo

This repository contains a cloud-native AI orchestration system that manages interactions between various AI components. The system is built with a focus on reliability, scalability, and developer experience.

## Development with GitHub Codespaces

This project is designed for a Codespaces-first development workflow, making it easy to get started without setting up local environments.

### Getting Started

1. **Open in Codespaces**: Click the "Code" button on the repository page, then select "Open with Codespaces" and "New codespace".

2. **Wait for Setup**: The Codespace will automatically set up the development environment, including:
   - Installing dependencies
   - Starting development services (Redis, Firestore emulator, Temporal)
   - Configuring VS Code extensions

3. **Run the Services**:
   - Press F5 or use Run > Start Debugging to launch the orchestrator API
   - To run the Temporal worker, select the "Run Temporal Worker" configuration from the Run and Debug view

4. **Access the Services**:
   - The FastAPI interface will be available at a forwarded port (usually 8000)
   - Temporal Web UI is available at port 8088

### Local Development Services

The following services are available in the development environment:

- **Redis**: Running on `localhost:6379` with password `devpassword`
- **Firestore Emulator**: Running on `localhost:8080`
- **Temporal Server**: Running on `localhost:7233`
- **Temporal Web UI**: Running on `localhost:8088`

### Configuration

Configuration is managed through environment variables, which can be set in the `.env` file or through Codespaces secrets for sensitive values.

Required secrets for development:
- `GCP_SERVICE_ACCOUNT_KEY`: For GCP service authentication
- `PINECONE_API_KEY`: For vector database access
- `OPENAI_API_KEY`: For LLM and embeddings

## Project Structure

- `orchestrator/`: FastAPI application for the central orchestrator service
- `shared/`: Shared modules used across different services
- `infra/`: Terraform configuration for GCP infrastructure
- `.github/workflows/`: CI/CD pipelines for testing and deployment
- `docs/`: Project documentation and best practices

## Memory Systems

The project includes three types of memory systems:

1. **Document Storage** (Firestore): For structured data and conversation history
2. **Cache** (Redis): For short-term memory and message queuing
3. **Vector Store** (Pinecone): For semantic search and similarity retrieval

## Temporal Workflow Integration

Temporal is used for reliable orchestration of multi-step AI processes:

### Sample Workflow

A sample workflow is provided in `orchestrator/workflows/sample.py` that demonstrates the basic pattern:

```python
@activity.defn
async def sample_task(data: str) -> str:
    return data.upper()

@workflow.defn
class SampleWorkflow:
    @workflow.run
    async def run(self, input_data: str) -> Dict[str, Any]:
        result = await workflow.execute_activity(sample_task, input_data)
        return {"status": "completed", "result": result}
```

### API Endpoints

Asynchronous processing is available through the following endpoints:

- `POST /api/v1/async/process_async`: Start a new workflow
- `GET /api/v1/async/workflow/{workflow_id}`: Check workflow status and results

## Running Tests

Tests can be run using the VS Code testing interface or via the command line:

```bash
pytest
```

## Infrastructure

The infrastructure is managed with Terraform and deployed on Google Cloud Platform. See `docs/infrastructure.md` for details.

## CI/CD

CI/CD pipelines are implemented with GitHub Actions:

- **CI**: Runs on all PRs to validate code quality and tests
- **Build and Deploy**: Builds containers and deploys to Cloud Run on merges to main
- **Infrastructure**: Manages Terraform-based infrastructure changes
