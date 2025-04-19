🛠️  ROLE
You are “Mono‑Debugger”, an expert Python‑TypeScript troubleshooter familiar with
Temporal, LangChain, Pinecone, and Kubernetes.

🎯  GOAL
Find and explain any runtime, import‑path, or config errors that prevent
ai‑ecosystem‑mono from:
1.  launching the Orchestrator (FastAPI + Temporal Worker)  
2.  running `pytest -m "not e2e"` cleanly  
3.  executing the demo workflow `workflow_demo_lead_to_outreach`

📂  CONTEXT SNAPSHOT
*  Root contains `orchestrator/`, `agents/`, `shared/`, `infra/`, `.devcontainer/`.
*  Dependencies are Poetry‑locked; env vars live in `.env.staging`.
*  Memory stack: Redis on :`6379`, Pinecone index `prd-leads`.

🔎  WHAT YOU CAN DO
1.  **Read files** – ask for any path and I’ll paste the code (≤ 300 lines at a time).  
2.  **Run commands** – request `!bash <cmd>` and I’ll return stdout/stderr.  
3.  **Print env vars** – ask `!env | grep FOO`.  
4.  **Open logs** – `!tail -n 100 orchestrator.log`.

📝  OUTPUT FORMAT
*  **Bug Summary** – 1‑sentence per defect.  
*  **Root Cause** – file : line explanation.  
*  **Fix Patch** – unified diff or Python snippet.  
*  **Retest Step** – exact command to rerun tests / server.  

⚠️  CONSTRAINTS
*  Prefer minimal invasive fixes.  
*  Keep third‑party API keys out of logs.  
*  Highlight any missing secrets with `$VAR_NAME`.

🔁  START
Begin by running the unit‑test suite and listing any failures.
If tests pass, spin up `uvicorn orchestrator.main:app --reload` and catch import errors.

I will supply code snippets and console output as you request.
# 🤖 AI-Ecosystem-Mono Documentation

## Overview

This documentation provides insight into the PayReady multi-agent sales platform architecture, current implementation status, and development roadmap. The repository contains a comprehensive multi-agent system designed to automate various aspects of the sales process with AI agents that collaborate through a shared memory infrastructure.

## Current System Status

The system currently has three major components fully implemented:

1. **PolicyGate for Content Moderation** - A robust guardrails system that enforces content safety, data privacy, and rate limiting
2. **Enhanced Configuration System** - A comprehensive configuration framework using Pydantic with settings for all system components
3. **BuilderAgent Security Sandbox** - A security layer for code generation and execution with static analysis and runtime protection

Several critical components are still pending implementation:

1. 🚧 **Sales Agent Implementations** - The concrete agent classes like LeadResearchAgent need completion
2. 🚧 **LangSmith Tracing** - Observability infrastructure for monitoring AI operations
3. 🚧 **Token Usage Tracking** - Cost control mechanisms for LLM usage
4. 🟠 **Vector Janitor Enhancements** - Memory pruning and optimization is partially implemented

## Documentation Index

| Document | Description |
|----------|-------------|
| [Architecture Overview](architecture-current.md) | Current system architecture with component status |
| [Implementation Summary](implementation-summary.md) | Analysis of implemented components and remaining gaps |
| [Development Roadmap](development-roadmap.md) | Timeline, responsibilities, and acceptance criteria for completing implementations |
| [Implementation Templates](implementation-templates.md) | Skeleton code templates for missing components |
| [Health Check Report](../code_analysis_report.md) | Original health check report identifying gaps and recommendations |

## System Architecture

The system follows a multi-agent architecture pattern:

- **Client Interfaces** - Admin Web UI (Next.js) and VS Code Extension
- **Orchestrator** - FastAPI + Temporal Worker for workflow coordination
- **Agents** - Specialized AI agents for different tasks (Lead Research, Marketing Outreach, etc.)
- **Memory Layer** - Multi-tiered storage (Redis, Firestore, Pinecone, Weaviate)
- **External APIs** - Integration with various third-party services (Salesforce, Slack, etc.)
- **Infrastructure** - Cloud Run deployment with GitHub Actions CI/CD

See the [architecture diagram](architecture-current.md) for a visual representation.

## Getting Started

### Setup Development Environment

```bash
# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Run local development server
make dev
```

### Testing the Implementation

```bash
# Run unit tests
make test

# Run integration tests
make integration-test

# Run linting
make lint
```

## Implementation Priorities

The current implementation priorities are:

1. **Complete Agent Implementations** - These form the core business functionality
2. **Implement LangSmith Tracing** - Critical for debugging and monitoring
3. **Develop Token Usage Tracking** - Important for cost control
4. **Enhance Memory Pruning** - Optimize the VectorJanitor with systematic pruning

See the [development roadmap](development-roadmap.md) for a detailed timeline.

## Using the Templates

The [implementation templates](implementation-templates.md) provide skeleton code that can be used as a starting point for completing the missing components. These templates include:

1. LangSmith Tracer implementation for observability
2. LeadResearchAgent implementation with plan/act methods
3. Token Usage Tracker for cost control

## Contributing

1. Make sure to follow the project's code style and documentation standards
2. Update the architecture diagram and status table as you complete components
3. Add appropriate tests for all new implementations
4. Include docstrings and type hints for all public functions and methods

## Next Steps

1. Implement the first sprint items from the [development roadmap](development-roadmap.md)
2. Update the architecture documentation as components are completed
3. Run comprehensive integration tests to ensure all components work together
