# AWS architecture

Region: ca-central-1 (Montréal). Production account, VPC across two Availability Zones, private subnets.

```mermaid
flowchart TB
  U([Planners and analysts]) --> EDGE
  subgraph REGION[AWS ca-central-1]
    EDGE[Edge and identity<br/>CloudFront + AWS WAF<br/>Cognito<br/>API Gateway HTTP API] --> ORCH
    ORCH[Runtime orchestration<br/>Step Functions Express<br/>Lambda step functions 0.5 GB<br/>Lambda tabulation: Python + DuckDB, 6 GB,<br/>provisioned concurrency]
    ORCH --> AI[Amazon Bedrock<br/>Claude Haiku 5.5, Canada CRIS<br/>Titan Text Embeddings V2<br/>Bedrock Guardrails]
    ORCH --> CAT[(Variable catalog<br/>Aurora PostgreSQL Serverless v2<br/>+ pgvector)]
    ORCH --> LAKE[(Data lake S3, KMS per zone<br/>landing > raw > curated > analytic)]
    ORCH --> CACHE[(DynamoDB result cache<br/>Answer log on S3 + Athena)]
    ING[Release ingestion<br/>S3 event > EventBridge > Step Functions Standard<br/>Glue jobs, Glue Data Quality, Glue Data Catalog<br/>Lake Formation, steward approval] --> CAT
    ING --> LAKE
  end
  SEC[Security and operations<br/>VPC interface endpoints, KMS, Secrets Manager, IAM least privilege<br/>CloudTrail, GuardDuty, Security Hub, Config, CloudWatch, X-Ray]
  classDef llm fill:#EEF2FF,stroke:#6366F1;
  class AI llm;
```

## Notes

- Claude Haiku 5.5 through Bedrock's Canada cross-Region inference keeps prompts in Canada (ca-central-1 / ca-west-1).
- Seven interface endpoints across two Availability Zones cost about CAD 160/month regardless of volume; they replace a NAT gateway and keep traffic private.
- Aurora Serverless v2 is the largest fixed cost. Dev and test clusters should use auto-pause (0 ACU).
- Provisioned concurrency keeps the 6 GB tabulation function warm so DuckDB answers in under 3 seconds.

Full detail: [data-architecture.md](data-architecture.md). Costs: [cost-estimate.md](cost-estimate.md).
