import json
from collections import OrderedDict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, Image, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from cost_model import summarize, TIERS, FX, EVAL_Q

S = summarize()
INK = colors.HexColor("#1F2328")
MUTED = colors.HexColor("#5B6370")
RULE = colors.HexColor("#D0D5DD")
AWS_C = colors.HexColor("#C2410C")
GCP_C = colors.HexColor("#1D4ED8")
AI_FILL = colors.HexColor("#EEF2FF")
AI_LINE = colors.HexColor("#6366F1")
LIGHT = colors.HexColor("#F6F7F9")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=17, textColor=INK, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=INK, spaceBefore=10, spaceAfter=6)
B = ParagraphStyle("B", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=6)
SM = ParagraphStyle("SM", parent=B, fontSize=8, leading=10.5, textColor=MUTED)
CELL = ParagraphStyle("CELL", parent=B, fontSize=8, leading=10, spaceAfter=0)
CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold")
TITLE = ParagraphStyle("TITLE", parent=H1, fontSize=24, leading=29, spaceAfter=6)


def cad(x, d=0):
    return f"${x:,.{d}f}"


def tbl(data, widths, header=True, zebra=True, bold_last=False, align_right_from=None):
    rows = [[Paragraph(str(c), CELLB if (header and i == 0) or (bold_last and i == len(data) - 1) else CELL)
             if not isinstance(c, Paragraph) else c for c in r] for i, r in enumerate(data)]
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
          ("LINEBELOW", (0, 1), (-1, -1), 0.25, RULE),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if bold_last:
        st.append(("LINEABOVE", (0, -1), (-1, -1), 0.8, INK))
    t.setStyle(TableStyle(st))
    return t


def money_cell(x, bold=False):
    return Paragraph(cad(x), ParagraphStyle("r", parent=CELLB if bold else CELL, alignment=2))


# ---------------- architecture diagram ----------------
def box(d, x, y, w, h, title, lines=(), fill=colors.white, stroke=RULE, sw=0.8, tsize=8.5):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill, strokeColor=stroke, strokeWidth=sw))
    d.add(String(x + 6, y + h - 12, title, fontName="Helvetica-Bold", fontSize=tsize, fillColor=INK))
    for i, ln in enumerate(lines):
        d.add(String(x + 6, y + h - 24 - i * 10, ln, fontName="Helvetica", fontSize=7, fillColor=MUTED))


def arrow(d, x1, y1, x2, y2, c=MUTED):
    d.add(Line(x1, y1, x2, y2, strokeColor=c, strokeWidth=0.9))
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    L = 5
    p1 = (x2 - L * math.cos(a - 0.4), y2 - L * math.sin(a - 0.4))
    p2 = (x2 - L * math.cos(a + 0.4), y2 - L * math.sin(a + 0.4))
    d.add(Polygon([x2, y2, p1[0], p1[1], p2[0], p2[1]], fillColor=c, strokeColor=c))


def arch(cloud):
    W, H = 540, 470
    d = Drawing(W, H)
    accent = AWS_C if cloud == "AWS" else GCP_C
    if cloud == "AWS":
        region = "AWS ca-central-1 (Montreal)  |  prod account, VPC across 2 AZs, private subnets"
        edge = ("Edge and identity", ["CloudFront + AWS WAF", "Cognito user pool (SSO-ready)", "API Gateway HTTP API"])
        orch = ("Runtime orchestration", ["Step Functions Express, 1 run per question",
                                          "Lambda: intent, resolver, planner, guard,",
                                          "narrator, number checker (0.5 GB)",
                                          "Lambda tabulation: Python + DuckDB, 6 GB,",
                                          "provisioned concurrency"])
        ai = ("Amazon Bedrock", ["Claude Haiku 5.5 via Canada", "cross-Region inference", "(ca-central-1 / ca-west-1 only)",
                                 "Titan Text Embeddings V2", "Bedrock Guardrails"])
        cat = ("Variable catalog", ["Aurora PostgreSQL Serverless v2", "+ pgvector, HNSW index"])
        lake = ("Data lake (S3, KMS per zone)", ["landing > raw > curated > analytic", "Parquet, partition = release"])
        cache = ("Cache and logs", ["DynamoDB result cache", "Answer log on S3 + Athena"])
        ingest = ("Release ingestion", ["S3 event > EventBridge > Step Functions Standard",
                                        "Glue Python/DuckDB jobs, Glue Data Quality, Glue Data Catalog",
                                        "Lake Formation grants, steward approval task token"])
        sec = ("Security and operations", ["VPC interface endpoints (no NAT), KMS, Secrets Manager, IAM least privilege",
                                           "CloudTrail org trail, GuardDuty, Security Hub, Config, CloudWatch, X-Ray"])
        ai_note = "Inference stays in Canada"
    else:
        region = "Google Cloud northamerica-northeast2 (Toronto)  |  prod project, Shared VPC"
        edge = ("Edge and identity", ["External HTTPS load balancer", "Cloud Armor", "Identity Platform / IAP"])
        orch = ("Runtime orchestration", ["Workflows, 1 execution per question",
                                          "Cloud Run services: intent, resolver,",
                                          "planner, guard, narrator, checker",
                                          "Cloud Run tabulation: Python + DuckDB,",
                                          "2 vCPU / 8 GiB, min instances"])
        ai = ("Vertex AI (Montreal endpoint)", ["Gemini 3.5 Flash, regional", "northamerica-northeast1",
                                               "ML processing in Canada", "Vertex text embeddings",
                                               "Model Armor / safety filters"])
        cat = ("Variable catalog", ["Cloud SQL for PostgreSQL", "+ pgvector, HNSW index"])
        lake = ("Data lake (Cloud Storage, CMEK)", ["landing > raw > curated > analytic", "Parquet, partition = release"])
        cache = ("Cache and logs", ["Firestore result cache", "Answer log in BigQuery"])
        ingest = ("Release ingestion", ["Storage event > Eventarc > Workflows",
                                        "Cloud Run jobs (Python/DuckDB), Dataplex data quality + catalog",
                                        "BigLake tables for analysts, steward approval callback"])
        sec = ("Security and operations", ["Direct VPC egress + Private Google Access, VPC Service Controls, Cloud KMS",
                                           "Secret Manager, Cloud Audit Logs, Security Command Center, Cloud Logging/Trace"])
        ai_note = "Calls cross to Montreal, still in Canada"

    # region container
    d.add(Rect(10, 70, W - 20, H - 92, rx=8, ry=8, fillColor=None, strokeColor=accent, strokeWidth=1, strokeDashArray=[4, 3]))
    d.add(String(120, H - 34, region, fontName="Helvetica-Bold", fontSize=8, fillColor=accent))
    # users
    box(d, 10, H - 18 - 0, 90, 16, "Planners and analysts", (), fill=LIGHT, tsize=7)
    # edge
    box(d, 22, 318, 150, 70, *edge)
    arrow(d, 55, H - 18, 70, 390)
    # orchestration
    box(d, 190, 298, 175, 90, *orch, fill=LIGHT)
    arrow(d, 172, 353, 188, 353)
    # AI
    box(d, 383, 298, 140, 90, *ai, fill=AI_FILL, stroke=AI_LINE, sw=1.2)
    arrow(d, 365, 343, 381, 343, AI_LINE)
    d.add(String(383, 287, ai_note, fontName="Helvetica-Oblique", fontSize=6.5, fillColor=AI_LINE))
    # data row
    box(d, 22, 190, 150, 60, *cat)
    box(d, 190, 190, 175, 60, *lake)
    box(d, 383, 190, 140, 60, *cache)
    arrow(d, 230, 298, 120, 252)
    arrow(d, 300, 298, 280, 252)
    arrow(d, 340, 298, 430, 252)
    d.add(String(300, 175, "Only the tabulation service reads the lake",
                 fontName="Helvetica-Oblique", fontSize=6.5, fillColor=MUTED))
    # ingestion
    box(d, 22, 105, 501, 62, *ingest, fill=colors.white)
    arrow(d, 280, 167, 280, 188)
    arrow(d, 100, 167, 100, 188)
    # security band
    box(d, 10, 8, W - 20, 52, *sec, fill=LIGHT)
    return d


# ---------------- chart ----------------
def chart(path):
    layers = ["AI", "Compute", "Data", "Edge & identity", "Network & security", "Operations", "Environments"]
    cols = ["#6366F1", "#0EA5E9", "#14B8A6", "#A3A3A3", "#F59E0B", "#94A3B8", "#E2E8F0"]
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.9), sharey=False)
    for ax, tier in zip(axes, TIERS):
        bottoms = [0, 0]
        for li, layer in enumerate(layers):
            vals = [sum(l["cad"] for l in S[tier][c]["lines"] if l["layer"] == layer) for c in ("AWS", "GCP")]
            ax.bar(["AWS", "Google Cloud"], vals, bottom=bottoms, color=cols[li], width=0.6,
                   label=layer if tier == "Pilot" else None, edgecolor="white", linewidth=0.5)
            bottoms = [b + v for b, v in zip(bottoms, vals)]
        for i, b in enumerate(bottoms):
            ax.text(i, b * 1.02, f"${b:,.0f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
        ax.set_title(f"{tier}  ({TIERS[tier]['q']:,} questions/mo)", fontsize=8.5)
        ax.set_ylim(0, max(bottoms) * 1.18)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=7.5)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"${v:,.0f}"))
    axes[0].set_ylabel("CAD per month", fontsize=8)
    fig.legend(loc="lower center", ncol=7, fontsize=6.8, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, dpi=220)
    plt.close(fig)


# ---------------- document ----------------
def build(out):
    chart("cost_chart.png")
    doc = SimpleDocTemplate(out, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            title="PUMF Insights Assistant: AWS and Google Cloud Architecture and Costs",
                            author="Donald Williams")
    f = []
    f.append(Paragraph("PUMF Insights Assistant", TITLE))
    f.append(Paragraph("Reference architecture on AWS and Google Cloud, with estimated monthly costs in CAD", H2))
    f.append(Paragraph("Prepared November 9, 2026. Canadian regions: AWS ca-central-1 and Google Cloud "
                       "northamerica-northeast2 (Toronto). Prices are list prices converted at "
                       f"USD 1 = CAD {FX:.2f}.", SM))
    f.append(Spacer(1, 8))

    f.append(Paragraph("Summary", H2))
    p, pr, sc = (S[t] for t in TIERS)
    f.append(Paragraph(
        f"Both clouds run the same design: an LLM translates a planner's question into a validated query spec, and a "
        f"deterministic DuckDB service computes weighted estimates from StatCan PUMFs. At production volume "
        f"(20,000 questions a month) the estimate is <b>{cad(pr['AWS']['cad'])}/month on AWS</b> and "
        f"<b>{cad(pr['GCP']['cad'])}/month on Google Cloud</b>, all-in including dev and test.", B))
    f.append(Paragraph(
        "The gap is driven by the model, not the infrastructure. Keeping inference in Canada limits each cloud to one "
        "model family today: Claude Haiku 5.5 through Bedrock's Canada cross-Region inference, or Gemini 3.5 Flash on "
        "Vertex AI's Montreal endpoint. Haiku 5.5 costs roughly a tenth as much per token. At pilot volume, fixed "
        "infrastructure dominates and Google Cloud is cheaper; from production volume upward, model tokens dominate "
        "and AWS is cheaper.", B))
    rows = [["Tier", "Questions/mo", "Users", "AWS CAD/mo", "Google Cloud CAD/mo", "AWS per question", "GCP per question"]]
    for t in TIERS:
        rows.append([t, f"{TIERS[t]['q']:,}", f"{TIERS[t]['users']:,}",
                     cad(S[t]["AWS"]["cad"]), cad(S[t]["GCP"]["cad"]),
                     cad(S[t]["AWS"]["per_q_cad"], 3), cad(S[t]["GCP"]["per_q_cad"], 3)])
    f.append(tbl(rows, [0.9 * inch, 0.95 * inch, 0.6 * inch, 0.95 * inch, 1.25 * inch, 1.05 * inch, 1.05 * inch]))
    f.append(Spacer(1, 6))
    f.append(Image("cost_chart.png", width=7.0 * inch, height=7.0 * inch * 2.9 / 7.4))
    f.append(Paragraph("Monthly cost by layer. Per-question figures divide the total by user questions only; "
                       f"{EVAL_Q:,} evaluation-set runs a month are included in every tier's costs.", SM))

    f.append(Paragraph("Workload assumptions", H2))
    rows = [["Assumption", "Pilot", "Production", "Scale"],
            ["User questions per month", "1,000", "20,000", "200,000"],
            ["Active users", "25", "200", "2,000"],
            ["Evaluation-set runs per month", "1,000", "1,000", "1,000"],
            ["Result-cache hit rate (skips tabulation)", "15%", "30%", "40%"],
            ["Tokens per question (4 LLM calls, +10% clarify)", "~16k in / ~2k out", "same", "same"],
            ["Warm tabulation instances", "1", "2", "5"],
            ["Catalog database", "1 ACU / 1 vCPU, no HA", "2 ACU + reader / 2 vCPU HA", "4 ACU + 2 readers / 4 vCPU HA + replica"],
            ["Dev + test environments", "30% of prod infra", "25%", "15%"]]
    f.append(tbl(rows, [2.6 * inch, 1.3 * inch, 1.5 * inch, 1.6 * inch]))
    f.append(Spacer(1, 10))

    # mapping
    f.append(Paragraph("Service mapping", H1))
    f.append(Paragraph("Each logical component has a direct equivalent on both clouds, so the application code "
                       "(Python, DuckDB, PostgreSQL with pgvector, JSON query specs) is portable. Only orchestration "
                       "definitions, IAM and the model client differ.", B))
    m = [["Component", "AWS (ca-central-1)", "Google Cloud (Toronto)"],
         ["Edge, WAF", "CloudFront, AWS WAF", "External HTTPS load balancer, Cloud Armor"],
         ["Identity", "Cognito (federate to Entra ID / Okta)", "Identity Platform or IAP"],
         ["API", "API Gateway HTTP API", "Load balancer to Cloud Run"],
         ["Orchestration (runtime)", "Step Functions Express", "Workflows"],
         ["Step logic", "Lambda (Python)", "Cloud Run services (Python)"],
         ["Tabulation engine", "Lambda container, DuckDB, provisioned concurrency", "Cloud Run, DuckDB, min instances"],
         ["LLM", "Bedrock: Claude Haiku 5.5, Canada inference profile", "Vertex AI: Gemini 3.5 Flash, Montreal endpoint"],
         ["Embeddings", "Titan Text Embeddings V2", "Vertex AI text embeddings"],
         ["Variable catalog", "Aurora PostgreSQL Serverless v2 + pgvector", "Cloud SQL PostgreSQL + pgvector"],
         ["Data lake zones", "S3 + SSE-KMS, Object Lock on landing", "Cloud Storage + CMEK, retention lock"],
         ["Physical catalog", "Glue Data Catalog, Lake Formation", "Dataplex Universal Catalog, BigLake"],
         ["Ingestion", "EventBridge, Step Functions Standard, Glue", "Eventarc, Workflows, Cloud Run jobs"],
         ["Data quality", "Glue Data Quality", "Dataplex data quality"],
         ["Result cache", "DynamoDB on-demand", "Firestore"],
         ["Analyst SQL, answer log", "Athena over S3", "BigQuery"],
         ["Private networking", "VPC interface endpoints (no NAT)", "Direct VPC egress, Private Google Access, VPC-SC"],
         ["Keys and secrets", "KMS, Secrets Manager", "Cloud KMS, Secret Manager"],
         ["Audit, threat detection", "CloudTrail, GuardDuty, Security Hub, Config", "Cloud Audit Logs, Security Command Center"],
         ["Observability", "CloudWatch, X-Ray", "Cloud Logging, Monitoring, Trace"]]
    f.append(tbl(m, [1.6 * inch, 2.7 * inch, 2.7 * inch]))
    f.append(Spacer(1, 6))
    f.append(Paragraph("Design constants on both clouds", H2))
    for s in ["The LLM never produces a number: it emits a JSON query spec validated against the catalog; DuckDB computes every estimate.",
              "No identity that calls the LLM can read microdata; the model sees catalog metadata and finished, reliability-checked tables only.",
              "Releases are immutable and versioned; reliability rules from each user guide run before the narrator; all data and inference stay in Canada."]:
        f.append(Paragraph("- " + s, B))
    f.append(PageBreak())

    for cloud, name in (("AWS", "AWS architecture"), ("GCP", "Google Cloud architecture")):
        f.append(Paragraph(name, H1))
        f.append(arch(cloud))
        f.append(Spacer(1, 8))
        if cloud == "AWS":
            notes = ["Bedrock's Canada cross-Region inference for Claude Haiku 5.5 routes only between ca-central-1 and "
                     "ca-west-1, so prompts never leave Canada. Larger Claude models are reachable from ca-central-1 only "
                     "through US or global routing.",
                     "Seven interface endpoints across two Availability Zones cost about CAD 160/month regardless of volume; "
                     "they replace a NAT gateway and keep traffic private.",
                     "Aurora Serverless v2 is the largest fixed cost. Dev and test clusters should use auto-pause (0 ACU).",
                     "Provisioned concurrency keeps the 6 GB tabulation function warm so DuckDB answers in under 3 seconds."]
        else:
            notes = ["Gemini 3.x models are offered on global, US and EU endpoints; Gemini 3.5 Flash is listed with ML "
                     "processing in northamerica-northeast1 (Montreal). The Toronto workloads call the Montreal endpoint, "
                     "so inference still stays in Canada.",
                     "Toronto is a Tier 2 region for Cloud Run, about 40% above Tier 1 prices; compute is still a small share.",
                     "Direct VPC egress and Private Google Access remove the per-endpoint hourly fees AWS charges.",
                     "Cloud SQL has no scale-to-zero; the pilot uses a 1 vCPU instance without HA, adding HA at production."]
        for n in notes:
            f.append(Paragraph("- " + n, B))
        f.append(PageBreak())

    # cost detail tables
    f.append(Paragraph("Cost detail", H1))
    f.append(Paragraph("CAD per month, production account plus dev and test. Basis: S = unit price confirmed from a "
                       "November 2026 source; L = published US list price, scaled by a stated regional factor; "
                       "A = planning allowance.", SM))
    for cloud, name in (("AWS", "AWS"), ("GCP", "Google Cloud")):
        f.append(Paragraph(name, H2))
        rows = [["Layer", "Service", "Basis", "Pilot", "Production", "Scale"]]
        n = len(S["Pilot"][cloud]["lines"])
        for i in range(n):
            l0 = S["Pilot"][cloud]["lines"][i]
            rows.append([l0["layer"], l0["service"], l0["basis"],
                         money_cell(S["Pilot"][cloud]["lines"][i]["cad"]),
                         money_cell(S["Production"][cloud]["lines"][i]["cad"]),
                         money_cell(S["Scale"][cloud]["lines"][i]["cad"])])
        rows.append(["Total", "", "", money_cell(S["Pilot"][cloud]["cad"], True),
                     money_cell(S["Production"][cloud]["cad"], True), money_cell(S["Scale"][cloud]["cad"], True)])
        f.append(tbl(rows, [1.05 * inch, 2.9 * inch, 0.55 * inch, 0.8 * inch, 0.85 * inch, 0.85 * inch], bold_last=True))
        if cloud == "AWS":
            f.append(PageBreak())

    f.append(Spacer(1, 8))
    f.append(Paragraph("Model choice is the biggest lever", H2))
    f.append(Paragraph("LLM cost alone, CAD per month, for the same token volumes. Options marked 'leaves Canada' "
                       "send prompts to US or global endpoints.", B))
    rows = [["Model option", "Residency", "Pilot", "Production", "Scale"]]
    opts = [("Claude Haiku 5.5, all four calls (costed)", "Canada", "aws_haiku_canada"),
            ("Haiku 5.5 + Claude Sonnet 5.5 for planner and narrator", "Leaves Canada", "aws_sonnet_global_for_planner_narrator"),
            ("Gemini 3.5 Flash, Montreal (costed)", "Canada", "gcp_gemini35_montreal"),
            ("Gemini 3.8 Flash, global, 2027 standard rate", "Leaves Canada", "gcp_gemini38_global_2027")]
    for label, res, k in opts:
        rows.append([label, res] + [money_cell(S[t]["sensitivity"][k]) for t in TIERS])
    f.append(tbl(rows, [3.0 * inch, 1.0 * inch, 0.95 * inch, 1.0 * inch, 1.05 * inch]))
    f.append(PageBreak())

    f.append(Paragraph("Risks, levers and open questions", H1))
    items = [("Model quality on Haiku 5.5", "The AWS estimate assumes Haiku 5.5 handles query planning well. Run the "
              "golden question set before committing; if planning accuracy falls short, routing only the planner to a "
              "larger model changes residency and roughly ten-folds LLM cost."),
             ("Regional and promotional pricing", "Canada inference-profile pricing is assumed at the 10% geographic premium "
              "reported for Bedrock regional endpoints. Gemini prices on regional endpoints and any 2027 changes should be "
              "confirmed with Google."),
             ("Unverified list prices", "Lines marked L use published US list prices with a 10% regional factor (40% for "
              "Cloud Run Tier 2). Validate them in the AWS Pricing Calculator and Google Cloud Pricing Calculator before "
              "budgeting."),
             ("Commitments", "Database Savings Plans (AWS) and committed use discounts for Cloud SQL and Cloud Run (Google) "
              "typically cut the fixed infrastructure lines by 20 to 50% at production volume."),
             ("Prompt caching", "The intent, rerank and planner prompts share long, stable instructions and catalog context. "
              "Prompt or context caching on either cloud can cut input-token cost substantially; not included here."),
             ("Excluded", "Staff time, support plans, egress beyond free tiers, taxes, domain and certificate costs, and "
              "statistical matching work for a fused CIUS-Census file.")]
    for h, txt in items:
        f.append(Paragraph(f"<b>{h}.</b> {txt}", B))

    f.append(Paragraph("Sources", H2))
    srcs = [("Amazon Bedrock now offers Canada cross-Region inference for Claude Haiku 5.5 (Oct 30, 2026)",
             "https://aws-news.com/article/2026-10-30-amazon-bedrock-now-offers-canada-cross-region-inference-for-claude-haiku-55"),
            ("AWS Bedrock pricing 2026, CloudForecast (Haiku 5.5, Sonnet 5.5 rates)", "https://www.cloudforecast.io/blog/aws-bedrock-pricing/"),
            ("AWS Bedrock pricing 2026, Economize (regional endpoints +10%)", "https://www.economize.cloud/blog/aws-bedrock-pricing/"),
            ("Claude in Amazon Bedrock: endpoint types by region", "https://platform.claude.com/docs/build-with-claude/claude-in-amazon-bedrock"),
            ("Aurora Serverless v2 pricing guide 2026, usage.ai", "https://www.usage.ai/blogs/aws/rds/aurora-serverless-v2/"),
            ("Aurora Serverless v2 supported regions (Canada Central)", "https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.Aurora_Fea_Regions_DB-eng.Feature.ServerlessV2.html"),
            ("Gemini API pricing, May 2026 (Gemini 3.5 Flash rate)", "https://www.metacto.com/blogs/the-true-cost-of-google-gemini-a-guide-to-api-pricing-and-integration"),
            ("Gemini API pricing 2026 (Gemini 3.8 Flash and 2027 rates)", "https://aibusinessweekly.net/p/gemini-api-pricing"),
            ("Google developer forum: Canada ML processing for Gemini 3.5 Flash", "https://discuss.google.dev/t/live-api-ml-processing-in-northamerica-northeast1-canada-for-gemini-live-2-5-flash-native-audio/405391"),
            ("Cloud Run locations and pricing tiers", "https://docs.cloud.google.com/run/docs/locations"),
            ("Cloud SQL pricing", "https://cloud.google.com/sql/pricing"),
            ("Cloud SQL C4A regional prices, Spare Cores (Toronto vs Iowa)", "https://sparecores.com/database/gcp/db-c4a-highmem-2"),
            ("Bank of Canada daily exchange rates", "https://www.bankofcanada.ca/rates/exchange/daily-exchange-rates/")]
    for label, url in srcs:
        f.append(Paragraph(f'<a href="{url}" color="#1D4ED8">{label}</a>', SM))

    def footer(c, d):
        c.saveState()
        c.setFont("Helvetica", 7)
        c.setFillColor(MUTED)
        c.drawString(0.75 * inch, 0.45 * inch, "PUMF Insights Assistant - AWS and Google Cloud architecture and cost estimate - Nov 2026")
        c.drawRightString(letter[0] - 0.75 * inch, 0.45 * inch, f"Page {d.page}")
        c.restoreState()

    doc.build(f, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build("../pdf/PUMF_Assistant_AWS_GCP_Architecture_Costs.pdf")
    print("ok")
