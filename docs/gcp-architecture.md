# Google Cloud architecture

Region: northamerica-northeast2 (Toronto), with LLM calls to the Vertex AI endpoint in northamerica-northeast1 (Montréal). Production project in a Shared VPC.

```mermaid
flowchart TB
  U([Planners and analysts]) --> EDGE
  subgraph REGION[Google Cloud northamerica-northeast2, Toronto]
    EDGE[Edge and identity<br/>External HTTPS load balancer<br/>Cloud Armor<br/>Identity Platform / IAP] --> ORCH
    ORCH[Runtime orchestration<br/>Workflows<br/>Cloud Run step services<br/>Cloud Run tabulation: Python + DuckDB,<br/>2 vCPU / 8 GiB, min instances]
    ORCH --> CAT[(Variable catalog<br/>Cloud SQL for PostgreSQL<br/>+ pgvector)]
    ORCH --> LAKE[(Data lake Cloud Storage, CMEK<br/>landing > raw > curated > analytic)]
    ORCH --> CACHE[(Firestore result cache<br/>Answer log in BigQuery)]
    ING[Release ingestion<br/>Storage event > Eventarc > Workflows<br/>Cloud Run jobs, Dataplex data quality + catalog<br/>BigLake tables, steward approval] --> CAT
    ING --> LAKE
  end
  subgraph MTL[northamerica-northeast1, Montréal]
    AI[Vertex AI<br/>Gemini 3.5 Flash, regional<br/>Vertex text embeddings]
  end
  ORCH --> AI
  SEC[Security and operations<br/>Direct VPC egress, Private Google Access, VPC Service Controls, Cloud KMS<br/>Secret Manager, Cloud Audit Logs, Security Command Center, Cloud Logging/Trace]
  classDef llm fill:#EEF2FF,stroke:#6366F1;
  class AI llm;
```

## Notes

- Gemini 3.5 Flash is listed with ML processing in Montréal; calls cross from Toronto to Montréal but stay in Canada.
- Toronto is a Tier 2 region for Cloud Run, about 40% above Tier 1 prices; compute is still a small share of cost.
- Direct VPC egress and Private Google Access avoid the per-endpoint hourly fees AWS charges.
- Cloud SQL has no scale-to-zero; the pilot uses a 1 vCPU instance without HA, adding HA at production.

Full detail: [data-architecture.md](data-architecture.md). Costs: [cost-estimate.md](cost-estimate.md).
