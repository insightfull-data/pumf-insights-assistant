# Service mapping: AWS and Google Cloud

Each logical component has a direct equivalent on both clouds, so the application code (Python, DuckDB, PostgreSQL with pgvector, JSON query specs) is portable. Only orchestration definitions, IAM and the model client differ.

| Component | AWS (ca-central-1) | Google Cloud (northamerica-northeast2, Toronto) |
| --- | --- | --- |
| Edge, WAF | CloudFront, AWS WAF | External HTTPS load balancer, Cloud Armor |
| Identity | Cognito (federate to Entra ID / Okta) | Identity Platform or IAP |
| API | API Gateway HTTP API | Load balancer to Cloud Run |
| Orchestration (runtime) | Step Functions Express | Workflows |
| Step logic | Lambda (Python) | Cloud Run services (Python) |
| Tabulation engine | Lambda container, DuckDB, provisioned concurrency | Cloud Run, DuckDB, min instances |
| LLM | Bedrock: Claude Haiku 5.5, Canada cross-Region inference | Vertex AI: Gemini 3.5 Flash, Montréal regional endpoint |
| Embeddings | Titan Text Embeddings V2 | Vertex AI text embeddings |
| Variable catalog | Aurora PostgreSQL Serverless v2 + pgvector | Cloud SQL for PostgreSQL + pgvector |
| Data lake zones | S3 + SSE-KMS, Object Lock on landing | Cloud Storage + CMEK, retention lock |
| Physical catalog | Glue Data Catalog, Lake Formation | Dataplex Universal Catalog, BigLake |
| Ingestion | EventBridge, Step Functions Standard, Glue | Eventarc, Workflows, Cloud Run jobs |
| Data quality | Glue Data Quality | Dataplex data quality |
| Result cache | DynamoDB on-demand | Firestore |
| Analyst SQL, answer log | Athena over S3 | BigQuery |
| Private networking | VPC interface endpoints (no NAT) | Direct VPC egress, Private Google Access, VPC Service Controls |
| Keys and secrets | KMS, Secrets Manager | Cloud KMS, Secret Manager |
| Audit, threat detection | CloudTrail, GuardDuty, Security Hub, Config | Cloud Audit Logs, Security Command Center |
| Observability | CloudWatch, X-Ray | Cloud Logging, Monitoring, Trace |

## Data residency for the LLM (as of November 2026)

- **AWS:** Bedrock's Canada cross-Region inference for Claude Haiku 5.5 routes only between ca-central-1 and ca-west-1 ([announcement](https://aws-news.com/article/2026-10-30-amazon-bedrock-now-offers-canada-cross-region-inference-for-claude-haiku-55)). Larger Claude models are reachable from ca-central-1 through US or global routing only ([regions](https://platform.claude.com/docs/build-with-claude/claude-in-amazon-bedrock)).
- **Google Cloud:** Gemini 3.x models are offered on global, US and EU endpoints; Gemini 3.5 Flash is listed with ML processing in northamerica-northeast1 (Montréal) ([forum thread](https://discuss.google.dev/t/live-api-ml-processing-in-northamerica-northeast1-canada-for-gemini-live-2-5-flash-native-audio/405391)). The Toronto workloads call the Montréal endpoint, so inference stays in Canada.

Both are moving targets; recheck before committing.
