# Sprint-0 Project Configuration

## Project Details
- **Name**: Sprint-0
- **Description**: Complete the missing pieces for the first sales workflow with guardrails, cost caps, tracing, and vector hygiene.
- **Columns**:
  - Todo
  - In-Prog
  - Review
  - Done

## GitHub CLI Commands

```bash
# Create the project
gh project create "Sprint-0" --description "Complete the missing pieces for the first sales workflow with guardrails, cost caps, tracing, and vector hygiene." --owner "$GITHUB_OWNER"

# Get the project ID
PROJECT_ID=$(gh project list --owner "$GITHUB_OWNER" --format json | jq -r '.projects[] | select(.title=="Sprint-0") | .id')

# Configure project fields
gh project field-create $PROJECT_ID --name "Status" --data-type "single_select" --single-select-options "Todo,In-Prog,Review,Done"

# Add issues to the project
# After creating issues, they can be added with:
# gh project item-add $PROJECT_ID --issue-url $ISSUE_URL
```

## Sprint-0 Timeline
- Start: April 22, 2025
- End: April 30, 2025

## Issue Creation
Run the following commands after creating the project to populate it with the appropriate tickets:

```bash
# Create the Memory tests issue
gh issue create --title "M-01 Memory tests" --body "$(cat .github/sprint-0/issues/m-01-memory-tests.md)" --label "Backend,Priority:High" --milestone "Sprint-0" --assignee "$BACKEND_ENGINEER"

# Create the PolicyGate wiring issue
gh issue create --title "G-01 PolicyGate wiring" --body "$(cat .github/sprint-0/issues/g-01-policygate-wiring.md)" --label "ML Ops,Priority:High" --milestone "Sprint-0" --assignee "$ML_OPS_ENGINEER"

# Create the LangSmith Tracer issue
gh issue create --title "T-01 LangSmithTracer" --body "$(cat .github/sprint-0/issues/t-01-langsmith-tracer.md)" --label "DevOps,Priority:High" --milestone "Sprint-0" --assignee "$DEVOPS_ENGINEER"

# Create the UsageTracker issue
gh issue create --title "C-01 UsageTracker + budgets" --body "$(cat .github/sprint-0/issues/c-01-usage-tracker.md)" --label "ML Ops,Priority:High" --milestone "Sprint-0" --assignee "$ML_OPS_ENGINEER"

# Create the LeadResearchAgent issue
gh issue create --title "A-01 LeadResearchAgent full implementation" --body "$(cat .github/sprint-0/issues/a-01-lead-research-agent.md)" --label "ML Eng,Priority:High" --milestone "Sprint-0" --assignee "$ML_ENGINEER"

# Create the VectorJanitor issue
gh issue create --title "V-01 VectorJanitor nightly workflow" --body "$(cat .github/sprint-0/issues/v-01-vector-janitor.md)" --label "ML Infra,Priority:High" --milestone "Sprint-0" --assignee "$ML_INFRA_ENGINEER"

# Create the Staging smoke-run issue
gh issue create --title "E-01 Staging smoke-run" --body "$(cat .github/sprint-0/issues/e-01-staging-smoke-run.md)" --label "DevOps,Priority:High" --milestone "Sprint-0" --assignee "$DEVOPS_ENGINEER"
