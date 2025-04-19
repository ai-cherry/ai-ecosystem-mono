Step 6: Ensure Codespaces-First Development Workflow
Actions: Adapt development practices and tools so that everything can be done via GitHub Codespaces, optimizing developer productivity in the cloud environment:
Pre-build Dev Container: Consider enabling Codespaces pre-builds for the repository. This will cache the devcontainer image so that launching a new Codespace is fast. Pre-install large dependencies (like LangChain, transformers, etc.) in the Dockerfile to avoid waiting every start.
Running Services in Dev: Use either integrated terminal or VS Code tasks to run the orchestrator. For example, define a VS Code debug configuration for FastAPI (using Uvicorn) so you can press F5 to launch the API in the Codespace. Also, if the orchestrator needs dependent services (Redis, etc.) during dev, there are two approaches:
Local dev services: Leverage Docker in Docker (since Codespace supports Docker) or docker-compose. For instance, include a docker-compose.dev.yml that starts a Redis container and maybe a local Weaviate container for testing. The devcontainer can automatically run docker-compose -f docker-compose.dev.yml up -d on start (specified in postCreateCommand in devcontainer.json). This way, when you start coding, a Redis is already running at localhost:6379 and perhaps a Weaviate at localhost:8080 for vector DB (if chosen). There is also a Firestore emulator provided by Google – you could run the Firestore emulator locally for tests (though using the real Firestore in a test project might be fine for dev).
Use Cloud Dev Resources: Alternatively, point dev to cloud instances. For example, use a development Firebase project’s Firestore, or a shared dev Redis instance. This requires the dev to have credentials. Since Codespaces is cloud, latency to cloud services is low. This approach means you don’t have to run heavy services in the Codespace, but you risk using possibly real data. Often a mix is used: e.g., a sandbox Pinecone index for dev, but a local Redis.
Codespaces Secrets: Store necessary secrets (like service account JSON for dev, or API keys) as Codespaces secrets in the GitHub repo settings. The devcontainer can declare env variables that map to those secrets. For example, in devcontainer.json:
json
Copy
Edit
"secrets": {
   "GCP_SERVICE_ACCOUNT_KEY": {"credential": "GCP_DEV_KEY"},
   "PINECONE_API_KEY": {"credential": "PINECONE_DEV_KEY"}
}
These will be injected as environment variables inside the Codespace container. The Settings(BaseSettings) in our code will then pick them up (since they are env vars).
Development Workflow: Document in the README how to use Codespaces: e.g., "Open repository in Codespace, launch orchestrator with uvicorn app.main:app --reload." Also ensure that when running, the service is accessible – Codespaces will forward the port, and you can use the generated URL to test endpoints in the browser.
Testing in Codespaces: Since we plan to run all tests in CI, also make it easy to run them in dev. If using pytest, ensure it’s installed in devcontainer, and provide a VSCode test integration or simply note pytest can be run.
Git Hooks: Optionally include pre-commit hooks (configured in devcontainer as well) to auto-format code on commit, etc., keeping code quality high.
By doing the above, any contributor just needs to open a Codespace – everything else (from installing deps to running services) is automated. This fosters a cloud-first dev approach consistent with the project’s philosophy (never running locally on personal machines, only in cloud env). Rationale: Embracing Codespaces accelerates setup and ensures every developer runs the code in an identical environment. This is particularly useful when the stack involves cloud services (GCP, etc.), as we can embed the cloud SDK and credentials in the devcontainer. It also means features like IntelliSense and debugging are available out-of-the-box in VSCode’s web or desktop client attached to the Codespace. Our goal is to optimize developer experience while keeping it aligned with production. This step reduces friction in development and ensures dev/prod parity: if it works in Codespaces, it’s very likely to work in Cloud Run, since both run Linux containers with similar config. File/Module Suggestions:
.devcontainer/Dockerfile – Define a custom image: start from e.g. mcr.microsoft.com/devcontainers/python:3.11 and then RUN apt-get install any needed tools (git, gcloud CLI, terraform, redis-tools for testing, etc.).
.devcontainer/devcontainer.json – In addition to basics, define "postCreateCommand": "docker-compose -f docker-compose.dev.yml up -d" to launch local support services, if using. Also map any needed dotfiles or configure git inside container.
docker-compose.dev.yml (at repo root) – Contains definitions for services like redis (using official Redis image), weaviate (using weaviate image with an in-memory or small volume), maybe temporal server for local testing (Temporal provides a Docker image for a test server).
VSCode launch.json (in .vscode/ folder) – Configuration to launch FastAPI with the debugger.
Documentation in README.md – “How to develop using Codespaces” with steps and troubleshooting.
Note: GitHub is actively improving monorepo support in Codespaces​
infoq.com
, allowing multiple devcontainer configs if needed for different services. In our case, one devcontainer is sufficient, but be aware of these features as the project grows (you could have separate devcontainer definitions if, say, one for backend vs one for a future frontend in same repo).
Step 7: Integrate Temporal for Orchestration Workflows (Starter Setup)
Actions: Introduce Temporal to the backend as a workflow orchestrator, which will allow the AI assistant to manage complex, multi-step processes reliably. This is a forward-looking step to support our “modular agent teams” concept with robust control flow. The initial setup involves:
Decide Deployment Approach: For development and even early production, using Temporal Cloud (the hosted service by Temporal) can expedite integration – we won’t have to run our own Temporal server. Alternatively, for local development without cloud dependency, run a Temporal server in Docker inside the Codespace (which is feasible, but uses resources). We can start by signing up for Temporal Cloud trial (if available) and get the necessary connection details (namespace, client certs or API key).
Add Temporal SDK: Install the Temporal Python SDK (pip install temporalio). This gives us the ability to define workflows and activities in Python.
Define a Sample Workflow: In the orchestrator codebase (or a new service folder if we want to separate concerns), create a module for Temporal workflows. For example, orchestrator/workflows/sample.py might contain:
python
Copy
Edit
from temporalio import workflow, activity

@activity.defn
async def sample_task(data: str) -> str:
    # Example activity (could call an LLM or do some I/O)
    return data.upper()

@workflow.defn
class SampleWorkflow:
    @workflow.run
    async def run(self, input_data: str) -> str:
        result = await workflow.execute_activity(sample_task, input_data, schedule_to_close_timeout=timedelta(seconds=30))
        return result
This simplistic workflow just transforms a string, but it shows the pattern: workflows call activities. In the future, our workflows could orchestrate a sequence of agent calls, tool usages, and memory lookups (e.g., one activity might query Pinecone, another call an LLM, etc., all under Temporal’s management).
Set Up a Worker: Temporal requires a worker process to execute activities and workflows. We will create a separate entry point for this. For example, orchestrator/workers/worker_main.py:
python
Copy
Edit
import asyncio
from temporalio.worker import Worker
from orchestrator.workflows import SampleWorkflow, sample_task

async def run_worker():
    client = await Client.connect("<Temporal Namespace address>", namespace="default")
    worker = Worker(client, task_queue="assistant-tq", workflows=[SampleWorkflow], activities=[sample_task])
    await worker.run()

if __name__ == "__main__":
    asyncio.run(run_worker())
This connects to the Temporal server (URL depends on Temporal Cloud setup or local server) and starts polling on a task queue (e.g., "assistant-tq"). We register our workflow and activity with the worker. In dev, we can run this worker in the Codespace to test.
Call Workflow from Orchestrator: To tie it into the orchestrator API, add an endpoint that kicks off a workflow. For example, in process.py (or a new endpoint), instead of directly calling LangChain, we could start a Temporal workflow:
python
Copy
Edit
from temporalio import Client
@router.post("/process_async")
async def process_async(request: RequestModel):
    client = await Client.connect("<Temporal Namespace address>", namespace="default")
    handle = await client.start_workflow(SampleWorkflow.run, request.data, id=f"workflow-{uuid4()}", task_queue="assistant-tq")
    return {"workflow_id": handle.id, "run_id": handle.run_id}
This returns immediately with workflow IDs, while the actual processing happens in the background worker. (Later, we can add another endpoint to query workflow results or status.)
Temporal Configuration: Store Temporal connection settings in the config (e.g., TEMPORAL_HOST_URL, TEMPORAL_NAMESPACE, etc.) and load via env vars. For Temporal Cloud, you’ll have a target host and auth token or certs; for local, it might be localhost:7233 with no auth. Also choose a task queue name and keep it consistent between client and worker.
Deployment considerations: If we are going to use this in production later, we might run the worker as a separate service. For now, in development, the orchestrator and worker can be run separately but from the same codebase. In the monorepo, you could even create a separate folder like worker/ with its own Dockerfile to containerize the worker process. The Docker image would run python orchestrator/workers/worker_main.py. Terraform could later deploy this as another Cloud Run service or on a VM (Temporal workers might better run on a VM or Kubernetes due to long polling connections, but Cloud Run can work if properly configured to not time out on idle).
Rationale: Temporal is a powerful microservices orchestration framework that brings reliability to multi-step workflows. By integrating it early, we set the stage for the orchestrator to coordinate complex tasks across agent teams. Temporal will ensure that if a step (activity) fails, it can retry or resume, and it provides a central place to track workflow state. This is far more robust than trying to manage multi-step processes with manual async code or databases. Temporal + FastAPI is a proven combo for scalable services​
capten.ai
 – FastAPI handles external requests, and Temporal handles internal long-lived workflows. In our case, the orchestrator can offload lengthy or multi-step sequences to Temporal, freeing the FastAPI request thread and improving reliability. Even at this bootstrap phase, a simple workflow (like the sample above) proves out the integration. By using Temporal Cloud or a Temporal server, we are embracing a cloud-native way to do workflow orchestration (versus something like Celery which lacks the durability and clarity of Temporal). It also fits with our architecture of having a single orchestrator service: rather than orchestrator directly calling all agent services synchronously, it can use Temporal to orchestrate calls asynchronously, which will be crucial once multiple agents are involved. Supporting Info: Temporal’s model uses workers that poll the server for tasks and execute them​
capten.ai
. We have set up our worker to listen on a task queue for our workflows/activities. This design allows scaling: we can run multiple workers (in cloud, multiple containers) to parallelize workloads. The FastAPI orchestrator simply submits workflows and doesn’t perform heavy lifting itself – improving scalability of the API. Our setup here is minimal, but it’s enough to demonstrate the concept and be extended later. File/Module Suggestions:
orchestrator/workflows/sample.py – Contains at least one workflow and activity definition (as an example).
orchestrator/workers/worker_main.py – Entry script to start Temporal worker. (If we foresee many workflows, we could have multiple files and import them here.)
orchestrator/app/api/v1/endpoints/process_async.py – New endpoint for kicking off a workflow (as a demonstration of integration).
requirements.txt – Include temporalio SDK.
orchestrator/config.py – Add Temporal config variables (e.g., TEMPORAL_HOST_URL). In development, you might default this to localhost:7233 for local server.
(Optional) If running Temporal locally in Codespaces: include a service in docker-compose.dev.yml for a Temporal test server:
yaml
Copy
Edit
temporal:
  image: temporalio/auto-setup:latest
  ports:
    - "7233:7233"
and adjust config accordingly.
Later, if this proves useful, we will formalize the Temporal worker as its own deployable service in Terraform (with possibly its own CI workflow). For now, it's part o# AI Ecosystem Infrastructure

This document outlines the infrastructure and CI/CD setup for the AI Ecosystem.

## Infrastructure Architecture

The infrastructure is managed using Terraform and deployed on Google Cloud Platform (GCP). It consists of the following components:

### Cloud Services

- **Cloud Run**: Hosts the orchestrator service, providing a scalable and serverless runtime environment.
- **Firestore**: Used for long-term memory storage and structured data.
- **Redis (Memorystore)**: Used for caching and temporary storage.
- **Artifact Registry**: Stores container images for the services.
- **Secret Manager**: Securely stores sensitive credentials (API keys, passwords).
- **VPC Connector**: Enables Cloud Run services to access VPC resources like Redis.

### Memory Components

The system uses three types of memory:

1. **Long-term Memory** (Firestore): Stores conversation history, user data, and other persistent information.
2. **Short-term Memory** (Redis): Caches recent conversations and frequently accessed data.
3. **Vector Memory** (Pinecone): Stores embeddings for semantic search capabilities.

## CI/CD Pipelines

The CI/CD pipelines are implemented using GitHub Actions:

### Testing Pipeline (`ci.yml`)

- Triggered on all pull requests and pushes to main
- Runs linting (flake8, black, isort) and type checking (mypy)
- Executes unit tests and generates coverage reports

### Build Pipeline (`build-and-push.yml`)

- Reusable workflow that builds Docker images and pushes them to Artifact Registry
- Used by other workflows to build specific services

### Deployment Pipelines

- **Orchestrator Deployment (`deploy_orchestrator.yml`)**:
  - Triggered when changes are made to the orchestrator or shared code
  - Builds a new container image and deploys it to Cloud Run

- **Infrastructure Deployment (`terraform.yml`)**:
  - Triggered when changes are made to Terraform configurations
  - Validates and applies infrastructure changes
  - Posts Terraform plans as comments on pull requests

## Infrastructure Management

### Setting up the Infrastructure

1. Ensure your GCP project is set up with appropriate permissions.
2. Set the required secrets in your GitHub repository:
   - `GCP_PROJECT_ID`: Your GCP project ID
   - `GCP_SA_KEY`: Service account key with necessary permissions
   - `GCP_REGION`: The GCP region (e.g., us-central1)
   - `PINECONE_API_KEY`: Your Pinecone API key
   - `OPENAI_API_KEY`: Your OpenAI API key

3. Run the Terraform workflow manually to set up the initial infrastructure:
   - Go to Actions > Terraform Infrastructure > Run workflow

### Updating the Infrastructure

- Make changes to the Terraform files in the `infra/` directory
- Create a pull request to review the changes
- Once merged to main, the Terraform workflow will apply the changes

## Development Workflow

1. Clone the repository
2. Make changes to the code
3. Push to a branch and create a pull request
4. CI pipeline will run tests automatically
5. Once merged to main, the relevant deployment pipeline will be triggered

## Monitoring and Troubleshooting

- Cloud Run services can be monitored through the GCP Console
- Logs are available in Cloud Logging
- Set up alerts for errors or high resource usage

## Security Considerations

- All sensitive data is stored in Secret Manager
- Service accounts follow the principle of least privilege
- Network access is controlled via VPC and firewall rules
