# 📐 AI‑Ecosystem‑Mono — Current Architecture (2025‑04‑19)

## ✅ / 🚧 Component Status
| Component | Status | Notes |
|-----------|:------:|-------|
| Policy Gate | ✅ | Moderation + PII + rate‑limiting |
| Config System | ✅ | Pydantic, env driven |
| Builder Sandbox | ✅ | AST checks + PR workflow |
| Sales Agents (Lead, Mktg, Coach, Coll) | 🚧 | `plan()` & `act()` still TODO |
| LangSmith Tracing | 🚧 | Middleware scaffold missing |
| Token Cost Caps | 🚧 | UsageTracker to build |
| Vector Janitor 2.0 | 🟠 | Duplicate/orphan sweep WIP |

---

## 🗺️ System‑level Schematic
```mermaid
%% ------------------------------------------------------------
%% AI‑Ecosystem‑Mono  –  Current State
%% ------------------------------------------------------------
flowchart LR
  %% === Client Interfaces ===
  subgraph Client‑Facing
    UI[Admin Web UI<br/>(Next.js)]
    VS[Roo VS Code Ext]
    UI -.REST/WS .-> APIGW[(Ingress /API Gateway)]
    VS -.HTTP .-> APIGW
  end

  %% === Orchestrator ===
  APIGW --> ORCH[Orchestrator<br/>(FastAPI + Temporal Worker)]

  %% === Agents ===
  subgraph Agents
    direction TB
    Lead[LeadResearchAgent]
    Mktg[MarketingOutreachAgent]
    Coach[SalesCoachAgent]
    Coll[CollectionsScoringAgent]
    Builder[BuilderAgent]
    Policy[PolicyGate]
    Janitor[VectorJanitor]
    Secrets[SecretsSyncAgent]
  end
  ORCH -->|spawn&nbsp;/&nbsp;await| Agents
  Agents -->|read / write| MM[MemoryManager]

  %% === Memory Fabric ===
  subgraph Memory Layer
    Redis[(Redis – cache)]
    Firestore[(Firestore – structured)]
    Pinecone[(Pinecone – vectors)]
    Weaviate[(Weaviate "Forge" – code+graph)]
    MM --uses--> Redis & Firestore & Pinecone & Weaviate
  end

  %% === External Services ===
  subgraph External APIs
    SF[(Salesforce)]
    Slack[(Slack)]
    Apollo[(Apollo.io)]
    PBuster[(PhantomBuster)]
    Gong[(Gong.io)]
    LLM[(Requesty → GPT‑4o / Claude 3.5)]
  end
  Agents --LangChain tools--> SF
  Agents --SlackNotify--> Slack
  Agents --> Apollo & PBuster
  Coach  --> Gong
  Agents -.OpenAI‑compat.-> LLM

  %% === Infra Agents ===
  Secrets --> Redis
  Janitor --> Pinecone

  %% === CI / CD ===
  subgraph CI/CD
    GH[GitHub Actions]
    CR[Cloud Run (staging&nbsp;/ prod)]
    GH --> CR
    Builder -.opens PRs .-> GH
  end
  ORCH --> CR

  %% === Styling ===
  classDef yellow fill:#ffe9d6,stroke:#e08d36,color:#000;
  classDef blue   fill:#e9f6ff,stroke:#3993d2,color:#000;
  classDef gray   fill:#f0f0f0,stroke:#888,color:#000;
  classDef green  fill:#e8ffe8,stroke:#5baf5b,color:#000;
  classDef purple fill:#fdf4ff,stroke:#b26ccf,color:#000;

  class Agents yellow;
  class Memory\ Layer blue;
  class External\ APIs gray;
  class Client‑Facing green;
  class CI/CD purple;
```
