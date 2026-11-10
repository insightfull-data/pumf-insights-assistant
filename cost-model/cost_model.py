"""Monthly cost model: PUMF Insights Assistant on AWS (ca-central-1) and Google Cloud (Toronto + Montreal).

All unit prices are USD list prices; totals are converted to CAD at FX.
basis: 'S' = price confirmed from a source gathered Nov 2026;
       'L' = published US-region list price (not re-checked this session) x regional factor;
       'A' = allowance (planning estimate, not a list price).
"""
import json

FX = 1.41          # Bank of Canada USD/CAD, 2026-11-06: 1.4113
HOURS = 730
SECS = HOURS * 3600
AWS_REG = 1.10     # assumed ca-central-1 premium over us-east-1 where not confirmed
GCP_REG = 1.10     # Toronto vs us-central1 (Cloud SQL C4A: 0.2141 vs 0.1946 = 1.10)
GCP_T2 = 1.40      # Cloud Run Tier 2 (Toronto) vs Tier 1 (ratio in Cloud Run functions tier table)

TIERS = {
    "Pilot":      dict(q=1_000,   users=25,    cache=0.15, storage_gb=20,  log_gb=3,
                       aurora_acu=1.0, aurora_readers=0, pc=1, sql="pilot",  envs=0.30),
    "Production": dict(q=20_000,  users=200,   cache=0.30, storage_gb=50,  log_gb=10,
                       aurora_acu=2.0, aurora_readers=1, pc=2, sql="prod",   envs=0.25),
    "Scale":      dict(q=200_000, users=2_000, cache=0.40, storage_gb=150, log_gb=60,
                       aurora_acu=4.0, aurora_readers=2, pc=5, sql="scale",  envs=0.15),
}
EVAL_Q = 1_000        # golden-set runs per month (200 questions x ~5 runs)

# Tokens per question across 4 LLM calls (intent, rerank, planner, narrator), +10% clarify overhead
TOK_IN, TOK_OUT, OVERHEAD = 14_500, 1_900, 1.10
SPLIT_IN = {"small": 7_500, "large": 7_000}   # intent+rerank vs planner+narrator
SPLIT_OUT = {"small": 700, "large": 1_200}

# --- LLM prices (USD per 1M tokens)
HAIKU55_CA = (0.11, 0.55)    # Canada CRIS; global $0.10/$0.50, geo endpoints +10%  (S)
SONNET55_GLOBAL = (2.00, 10.00)  # global/US routing only from ca-central-1 (S)
GEM35_FLASH = (1.50, 9.00)   # Gemini 3.5 Flash; Canada ML processing in northamerica-northeast1 (S)
GEM38_FLASH_2027 = (1.50, 7.50)  # Gemini 3.8 Flash standard rate from 2027-01-01, global only (S)


def llm_cost(q, price_small, price_large=None):
    price_large = price_large or price_small
    per_q = (SPLIT_IN["small"] * price_small[0] + SPLIT_OUT["small"] * price_small[1]
             + SPLIT_IN["large"] * price_large[0] + SPLIT_OUT["large"] * price_large[1]) / 1e6
    return per_q * OVERHEAD * q


def aws(tier):
    t = TIERS[tier]
    Q = t["q"] + EVAL_Q
    nc = Q * (1 - t["cache"])
    L = []  # (layer, service, basis, usd, note)

    L.append(("AI", "Bedrock: Claude Haiku 5.5, Canada cross-Region inference", "S",
              llm_cost(Q, HAIKU55_CA), f"{Q:,} questions x ~16k tokens"))
    L.append(("AI", "Bedrock: Titan Text Embeddings V2 (queries + re-embeds)", "L",
              (Q * 300 + 3_000_000) / 1e6 * 0.02 * AWS_REG, "Small"))

    # Lambda: orchestration steps incl. waiting on LLM (~14 s at 0.5 GB) + tabulation (2 s at 6 GB) for non-cached
    gbs = Q * 14 * 0.5 + nc * 2 * 6
    L.append(("Compute", "Lambda: orchestration + tabulation", "L",
              (gbs * 0.0000166667 + Q * 10 * 0.20 / 1e6), f"{gbs:,.0f} GB-s"))
    pc_gbs = t["pc"] * 6 * SECS
    L.append(("Compute", f"Lambda provisioned concurrency ({t['pc']} x 6 GB)", "L",
              pc_gbs * 0.0000041667, "Avoids cold starts on tabulation"))
    L.append(("Compute", "Step Functions Express (runtime) + Standard (ingest)", "L",
              Q / 1e6 * 1.00 + Q * 20 * 0.064 * 0.00001667 + 3_000 * 0.025 / 1_000, ""))
    L.append(("Compute", "Glue jobs + Data Quality (ingest, amortized)", "L",
              8 * 0.44 * AWS_REG, "~8 DPU-hours/month"))

    acu_h = (t["aurora_acu"] + t["aurora_readers"] * max(1.0, t["aurora_acu"] / 2)) * HOURS
    L.append(("Data", "Aurora PostgreSQL Serverless v2 + pgvector", "S",
              acu_h * 0.12 * AWS_REG + 10 * 0.10 * AWS_REG + 50 * 0.20 * AWS_REG,
              f"{acu_h/HOURS:.1f} avg ACU; $0.12/ACU-h us-east-1 x1.10"))
    L.append(("Data", "S3: landing, raw, curated, analytic, exports", "L",
              t["storage_gb"] * 0.025 + Q * 30 / 1_000 * 0.0004, f"{t['storage_gb']} GB"))
    L.append(("Data", "DynamoDB on-demand: result cache", "L",
              (Q * 2 * 0.125 + nc * 0.625) / 1e6 * AWS_REG + 1 * 0.25, ""))
    L.append(("Data", "Athena: analyst SQL + answer-log queries", "L",
              max(0.2, Q / 20_000) * 5.0 * AWS_REG, "TB scanned"))

    L.append(("Edge & identity", "CloudFront + API Gateway HTTP API", "L",
              Q * 5 / 1e6 * 1.00 * AWS_REG, "CloudFront within free 1 TB"))
    L.append(("Edge & identity", "AWS WAF (1 web ACL, 5 rules)", "L",
              5 + 5 + Q * 6 / 1e6 * 0.60, ""))
    L.append(("Edge & identity", "Cognito user pool", "L",
              0.0 if t["users"] <= 10_000 else 0, f"{t['users']} MAU, within free tier"))

    endpoints = 7 * 2 * HOURS * 0.01 * AWS_REG
    L.append(("Network & security", "VPC interface endpoints (7 x 2 AZ)", "L",
              endpoints + 5 * 0.01, "Bedrock, Glue, KMS, STS, Secrets, Logs, SFN"))
    L.append(("Network & security", "KMS (5 keys) + Secrets Manager (6)", "L",
              5 * 1 + 6 * 0.40 + Q * 20 / 10_000 * 0.03, ""))
    L.append(("Network & security", "GuardDuty, Security Hub, Config, CloudTrail", "A",
              {"Pilot": 40, "Production": 90, "Scale": 250}[tier], "Allowance"))
    L.append(("Operations", "CloudWatch logs, metrics, alarms; X-Ray", "L",
              t["log_gb"] * 0.50 * AWS_REG + 30 * 0.30 + 10 * 0.10 + Q * 10 / 1e6 * 5.0, ""))

    prod = sum(x[3] for x in L)
    nonai = sum(x[3] for x in L if x[0] != "AI")
    L.append(("Environments", f"Dev + test accounts ({int(t['envs']*100)}% of non-AI prod)", "A",
              nonai * t["envs"], "Aurora auto-pause, no provisioned concurrency"))
    return L


def gcp(tier):
    t = TIERS[tier]
    Q = t["q"] + EVAL_Q
    nc = Q * (1 - t["cache"])
    L = []
    L.append(("AI", "Vertex AI: Gemini 3.5 Flash, Montreal regional endpoint", "S",
              llm_cost(Q, GEM35_FLASH), f"{Q:,} questions x ~16k tokens"))
    L.append(("AI", "Vertex AI: text embeddings (queries + re-embeds)", "A",
              (Q * 300 + 3_000_000) / 1e6 * 0.15, "Small"))

    # Cloud Run request-based, Tier 2: CPU 1.4x $0.000024, mem 1.4x $0.0000025
    cpu_s = Q * 14 * 1 + nc * 2 * 2
    mem_s = Q * 14 * 0.5 + nc * 2 * 8
    L.append(("Compute", "Cloud Run services: orchestration + tabulation", "L",
              cpu_s * 0.000024 * GCP_T2 + mem_s * 0.0000025 * GCP_T2 + Q * 10 * 0.40 / 1e6,
              "Tier 2 pricing"))
    # Min instances for tabulation (idle rate: CPU ~0.1x, mem 1x) approximated with instance-based Tier 2
    mi = t["pc"] * (2 * 0.0000025 + 8 * 0.0000025) * GCP_T2 * SECS
    L.append(("Compute", f"Cloud Run min instances ({t['pc']} x 2 vCPU/8 GiB, idle)", "L",
              mi, "Warm tabulation"))
    L.append(("Compute", "Workflows (runtime + ingest)", "L",
              max(0, Q * 20 - 5_000) / 1_000 * 0.01 + Q * 6 / 1_000 * 0.025, ""))
    L.append(("Compute", "Cloud Run jobs + Dataplex data quality (ingest)", "L",
              8 * 0.10 * GCP_T2 + 5, "Amortized"))

    sql = {"pilot": (1, 3.75, False, 0), "prod": (2, 8, True, 0), "scale": (4, 16, True, 1)}[t["sql"]]
    vcpu, mem, ha, replicas = sql
    hourly = (vcpu * 0.0413 + mem * 0.007) * GCP_REG
    inst = hourly * (2 if ha else 1) + hourly * replicas
    L.append(("Data", f"Cloud SQL PostgreSQL + pgvector ({vcpu} vCPU/{mem:g} GiB{', HA' if ha else ''})", "S",
              inst * HOURS + 20 * 0.17 * GCP_REG * (2 if ha else 1), "Enterprise edition"))
    L.append(("Data", "Cloud Storage: landing, raw, curated, analytic, exports", "L",
              t["storage_gb"] * 0.023 + Q * 30 / 1e4 * 0.005, f"{t['storage_gb']} GB"))
    L.append(("Data", "Firestore: result cache", "L",
              (Q * 2 * 0.06 / 1e5 + nc * 0.18 / 1e5) * GCP_REG, ""))
    L.append(("Data", "BigQuery: analyst SQL + answer log", "L",
              max(0, Q / 20_000 - 1) * 6.25, "First 1 TB/month free"))

    L.append(("Edge & identity", "External HTTPS load balancer", "L",
              0.025 * HOURS * GCP_REG + Q * 0.0002 * 0.008, ""))
    L.append(("Edge & identity", "Cloud Armor (1 policy, 5 rules)", "L",
              5 + 5 + Q * 6 / 1e6 * 0.75, ""))
    L.append(("Edge & identity", "Identity Platform / IAP", "L", 0.0, f"{t['users']} MAU, within free tier"))

    L.append(("Network & security", "Direct VPC egress + Private Google Access", "L", 0.0,
              "No connector or endpoint fee"))
    L.append(("Network & security", "Cloud KMS (5 keys) + Secret Manager (6)", "L",
              5 * 0.06 + 6 * 0.06 + Q * 20 / 10_000 * 0.03, ""))
    L.append(("Network & security", "Security Command Center, audit logs, Org Policy", "A",
              {"Pilot": 15, "Production": 40, "Scale": 150}[tier], "Allowance"))
    L.append(("Operations", "Cloud Logging, Monitoring, Trace", "L",
              max(0, t["log_gb"] - 50) * 0.50 + 10, ""))

    nonai = sum(x[3] for x in L if x[0] != "AI")
    L.append(("Environments", f"Dev + test projects ({int(t['envs']*100)}% of non-AI prod)", "A",
              nonai * t["envs"], "Smaller Cloud SQL, no min instances"))
    return L


def summarize():
    out = {}
    for tier in TIERS:
        for cloud, fn in (("AWS", aws), ("GCP", gcp)):
            lines = fn(tier)
            usd = sum(x[3] for x in lines)
            out.setdefault(tier, {})[cloud] = dict(
                lines=[dict(layer=a, service=b, basis=c, usd=round(d, 2), cad=round(d * FX, 2), note=e)
                       for a, b, c, d, e in lines],
                usd=round(usd, 2), cad=round(usd * FX, 2),
                per_q_cad=round(usd * FX / TIERS[tier]["q"], 4),
            )
        # LLM sensitivity: alternative model choices
        Q = TIERS[tier]["q"] + EVAL_Q
        out[tier]["sensitivity"] = {
            "aws_sonnet_global_for_planner_narrator": round(llm_cost(Q, HAIKU55_CA, SONNET55_GLOBAL) * FX, 2),
            "aws_haiku_canada": round(llm_cost(Q, HAIKU55_CA) * FX, 2),
            "gcp_gemini35_montreal": round(llm_cost(Q, GEM35_FLASH) * FX, 2),
            "gcp_gemini38_global_2027": round(llm_cost(Q, GEM38_FLASH_2027) * FX, 2),
        }
    return out


if __name__ == "__main__":
    s = summarize()
    json.dump(s, open("costs.json", "w"), indent=1)
    for tier, v in s.items():
        print(f"\n== {tier} ==")
        for cloud in ("AWS", "GCP"):
            print(f" {cloud}: CAD {v[cloud]['cad']:>10,.0f}/mo   per question CAD {v[cloud]['per_q_cad']:.3f}")
            for l in v[cloud]["lines"]:
                print(f"    {l['layer'][:12]:12} {l['service'][:62]:62} {l['basis']} {l['cad']:>9,.2f}")
        print("  sensitivity", v["sensitivity"])
