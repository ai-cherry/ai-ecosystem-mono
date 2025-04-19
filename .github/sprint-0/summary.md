# Sprint-0 Summary & Implementation Plan

This document provides a comprehensive overview of the Sprint-0 deliverables that have been created to address the project's needs for the first sales workflow in staging.

## 1. Project Overview

The Sprint-0 focuses on completing the crucial missing pieces so that our first sales workflow can run in staging with:
- Guardrails
- Cost caps
- LangSmith tracing
- Nightly vector hygiene

## 2. Created Components

### 2.1 Project Management Resources
- GitHub Project configuration (Sprint-0)
- PR template for standardized pull request review
- 7 detailed issue descriptions for key tickets

### 2.2 Implementation Skeletons
- Memory test implementation framework
- PolicyGate wiring with banned words detection
- LangSmithTracer for observability
- UsageTracker for token budget management
- LeadResearchAgent full implementation
- VectorJanitor nightly workflow
- Staging smoke test harness

### 2.3 Configuration Files
- `config/budgets.yaml` with default token limits
- Test fixtures for smoketest

## 3. GitHub CLI Commands to Setup Sprint-0

Create the project and issues with the following commands:

```bash
# Variables (set these first)
GITHUB_OWNER="your-org-name"
BACKEND_ENGINEER="backend-engineer-username"
ML_OPS_ENGINEER="ml-ops-engineer-username"
DEVOPS_ENGINEER="devops-engineer-username"
ML_ENGINEER="ml-engineer-username"
ML_INFRA_ENGINEER="ml-infra-engineer-username"

# Create the project
gh project create "Sprint-0" --description "Complete the missing pieces for the first sales workflow with guardrails, cost caps, tracing, and vector hygiene." --owner "$GITHUB_OWNER"

# Get the project ID
PROJECT_ID=$(gh project list --owner "$GITHUB_OWNER" --format json | jq -r '.projects[] | select(.title=="Sprint-0") | .id')

# Configure project fields
gh project field-create $PROJECT_ID --name "Status" --data-type "single_select" --single-select-options "Todo,In-Prog,Review,Done"

# Create the issues
gh issue create --title "M-01 Memory tests" --body "$(cat .github/sprint-0/issues/m-01-memory-tests.md)" --label "Backend,Priority:High" --milestone "Sprint-0" --assignee "$BACKEND_ENGINEER"

gh issue create --title "G-01 PolicyGate wiring" --body "$(cat .github/sprint-0/issues/g-01-policygate-wiring.md)" --label "ML Ops,Priority:High" --milestone "Sprint-0" --assignee "$ML_OPS_ENGINEER"

gh issue create --title "T-01 LangSmithTracer" --body "$(cat .github/sprint-0/issues/t-01-langsmith-tracer.md)" --label "DevOps,Priority:High" --milestone "Sprint-0" --assignee "$DEVOPS_ENGINEER"

gh issue create --title "C-01 UsageTracker + budgets" --body "$(cat .github/sprint-0/issues/c-01-usage-tracker.md)" --label "ML Ops,Priority:High" --milestone "Sprint-0" --assignee "$ML_OPS_ENGINEER"

gh issue create --title "A-01 LeadResearchAgent full implementation" --body "$(cat .github/sprint-0/issues/a-01-lead-research-agent.md)" --label "ML Eng,Priority:High" --milestone "Sprint-0" --assignee "$ML_ENGINEER"

gh issue create --title "V-01 VectorJanitor nightly workflow" --body "$(cat .github/sprint-0/issues/v-01-vector-janitor.md)" --label "ML Infra,Priority:High" --milestone "Sprint-0" --assignee "$ML_INFRA_ENGINEER"

gh issue create --title "E-01 Staging smoke-run" --body "$(cat .github/sprint-0/issues/e-01-staging-smoke-run.md)" --label "DevOps,Priority:High" --milestone "Sprint-0" --assignee "$DEVOPS_ENGINEER"

# Add issues to the project and set status to "Todo"
for ISSUE in $(gh issue list --state open --label "Priority:High" --milestone "Sprint-0" --json number --jq '.[].number'); do
  gh project item-add $PROJECT_ID --issue-url "$GITHUB_OWNER/$REPO_NAME#$ISSUE"
  gh project item-edit --field Status --value "Todo" $PROJECT_ID --id "$(gh project item-list $PROJECT_ID --json id,content --jq '.items[] | select(.content.number=='$ISSUE') | .id')"
done
```

## 4. Unified Diffs for All Tickets

### M-01 Memory tests
```diff
# New file: tests/memory_manager_test/test_memory_manager.py
+ """
+ Tests for the MemoryManager component.
+ 
+ This test suite validates the functionality of the MemoryManager class,
+ ensuring that all memory operations work correctly across Redis, Firestore,
+ Pinecone, and Weaviate storage layers.
+ """
+ 
+ import asyncio
+ import datetime
+ import json
+ import os
+ import pytest
+ import uuid
+ from unittest.mock import AsyncMock, MagicMock, patch
+ 
+ from shared.memory.memory_manager import MemoryManager, MemoryItem, MemoryItemType
+ 
+ # Add comprehensive test implementations with mocks for Redis, Firestore, etc.
+ # TODO: Implement all test cases to reach 90% branch coverage
```

### G-01 PolicyGate wiring
```diff
# New file: shared/guardrails/banned_words.py
+ """
+ Banned words list for the PolicyGate.
+ 
+ This module provides a list of banned words that will be automatically
+ blocked by the PolicyGate when found in outgoing messages.
+ """
+ 
+ # Categories of banned words with associated terms
+ BANNED_CATEGORIES = {
+     "profanity": [
+         # Common profanity would be listed here
+         # Placeholder entries for development/testing
+         "profanity_placeholder_1",
+         "profanity_placeholder_2",
+     ],
+     # Additional categories and lists...
+ }
+ 
+ # Test placeholders and helper functions
+ # TODO: Wire this into PolicyGate enforcement in BaseAgent.send()
```

### T-01 LangSmithTracer
```diff
# New file: shared/observability/langsmith_tracer.py
+ """
+ LangSmith tracer for monitoring and debugging LLM operations.
+ 
+ This module provides integration with LangSmith for tracing LLM calls,
+ enabling detailed monitoring, debugging, and cost tracking for AI operations.
+ """
+ 
+ import logging
+ import time
+ import uuid
+ from typing import Any, Dict, List, Optional, Union
+ 
+ # Conditional import for LangSmith
+ try:
+     from langsmith import Client
+     LANGSMITH_AVAILABLE = True
+ except ImportError:
+     LANGSMITH_AVAILABLE = False
+ 
+ from shared.config import observability_settings
+ 
+ # Initialize logger
+ logger = logging.getLogger(__name__)
+ 
+ 
+ class LangSmithTracer:
+     """Middleware for tracing LLM operations to LangSmith."""
+     
+     # Implementation of tracing methods
+     # TODO: Hook into LLM service layer
```

### C-01 UsageTracker + budgets
```diff
# New file: shared/cost/usage_tracker.py
+ """
+ Token usage tracker for managing LLM costs.
+ 
+ This module provides tools for tracking, limiting, and reporting on token usage
+ across the application, helping to control costs and ensure budget compliance.
+ """
+ 
+ import logging
+ import time
+ from collections import defaultdict
+ from datetime import datetime, timedelta
+ from typing import Any, Dict, List, Optional, Tuple, Union
+ 
+ # For type hints only
+ from typing import TYPE_CHECKING
+ if TYPE_CHECKING:
+     import aioredis
+ 
+ from shared.config import llm_settings
+ 
+ # Initialize logger
+ logger = logging.getLogger(__name__)
+ 
+ 
+ class UsageTracker:
+     """
+     Tracks and limits token usage across LLM interactions.
+     """
+     
+     # Implementation of usage tracking and budget enforcement
+     # TODO: Connect to Redis for persistent storage and integrate with LLM calls
```

### A-01 LeadResearchAgent full implementation
```diff
# Updated file: agents/sales/lead_research.py
+ """
+ LeadResearchAgent implementation for researching sales leads.
+ 
+ This agent is responsible for gathering information about potential leads,
+ analyzing their profile, and providing insights to the sales team.
+ """
+ 
+ import logging
+ from typing import Any, Dict, List, Optional, Union
+ from pydantic import BaseModel, Field
+ 
+ from agents.base.sales_agent_base import BaseSalesAgent, AgentTask, AgentPlan, AgentResult, AgentStep
+ from shared.memory.memory_manager import MemoryManager
+ 
+ # Initialize logger
+ logger = logging.getLogger(__name__)
+ 
+ 
+ class LeadProfile(BaseModel):
+     """Structured data about a sales lead."""
+     company_name: str
+     industry: str = Field(default="")
+     # Additional fields...
+ 
+ 
+ class LeadResearchAgent(BaseSalesAgent):
+     """
+     Agent that researches potential leads for sales opportunities.
+     """
+     
+     # Implementation of plan() and act() methods
+     # TODO: Complete all tool integrations and test with mock data
```

### V-01 VectorJanitor nightly workflow
```diff
# New file: shared/memory/vector_janitor.py
+ """
+ VectorJanitor for maintaining vector database health.
+ 
+ This module provides utilities for detecting and removing duplicate and orphaned
+ vectors from our vector databases, ensuring optimal performance and storage efficiency.
+ """
+ 
+ import asyncio
+ import logging
+ import time
+ from datetime import datetime
+ from typing import Any, Dict, List, Optional, Set, Tuple, Union
+ 
+ import numpy as np
+ 
+ from shared.memory.memory_manager import MemoryManager
+ from shared.memory.vectorstore import VectorStore
+ from shared.memory.firestore import FirestoreMemory
+ 
+ # Initialize logger
+ logger = logging.getLogger(__name__)
+ 
+ class VectorJanitor:
+     """
+     Maintains the health and efficiency of vector databases.
+     """
+     
+     # Implementation of vector store maintenance methods
+     # TODO: Finish temporal workflow integration and slack notifications
```

### E-01 Staging smoke-run
```diff
# New file: tests/smoke_test.py
+ #!/usr/bin/env python
+ """
+ End-to-end smoke test for lead-to-outreach workflow.
+ 
+ This script runs a complete test of the sales workflow in the staging environment,
+ validating that all components work together correctly:
+ 1. LeadResearchAgent
+ 2. LangSmith Tracing
+ 3. Token Usage Tracking
+ 4. Memory & Vector Storage
+ 5. PolicyGate
+ 6. Integration with external services (Slack, Salesforce)
+ """
+ 
+ import argparse
+ import asyncio
+ import json
+ import logging
+ import os
+ import sys
+ import time
+ import uuid
+ from datetime import datetime
+ from pathlib import Path
+ from typing import Any, Dict, List, Optional
+ 
+ # Complete implementation of the smoke test harness
+ # TODO: Connect to all component endpoints and verify execution
```

## 5. Follow-up Manual Steps

Before the Sprint-0 implementation can be deployed to staging, the following environment variables and configurations need to be set up:

### 5.1 API Keys
- `LANGSMITH_API_KEY` - For LangSmith tracing
- `OPENAI_API_KEY` - For LLM access
- `PINECONE_API_KEY` - For vector operations
- `SLACK_API_TOKEN` - For notifications

### 5.2 Configuration
- Configure Redis instance for UsageTracker
- Set up Temporal workflow server for VectorJanitor
- Configure Firestore credentials
- Verify proper VPC access from staging environment

### 5.3 CI/CD Integration
- Update GitHub Actions workflow to include memory test coverage check
- Configure staging deployment pipeline
- Set up LangSmith project

## 6. Decision Check-In Results
Using default values from the planning document:
- Prod daily token cap per agent: **1 M tokens**
- LangSmith plan: **Free (5 k traces/mo)**
- Embedding refresh cadence: **manual**

## 7. Stretch Goals for Week 2
If all Sprint-0 tickets are completed early, the following stretch goals can be pursued:

1. Implement **MarketingOutreachAgent** following the LeadResearchAgent pattern
2. Hook token-usage metrics into Cloud Monitoring dashboards
3. Add **coverage gate** in CI ≥ 80%
4. Auto-label PRs touching `guardrails/` or `security_sandbox/` with `needs-policy-review`

## 8. Next Steps
1. Review all ticket skeletons for completeness and accuracy
2. Assign tickets to team members
3. Set up the GitHub project using the commands above
4. Begin implementation of each ticket
5. Schedule daily stand-ups to track progress
6. Plan for a demo at the end of the sprint
