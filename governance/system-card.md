# System card: PUMF Insights Assistant

Version 0.1 (design stage), November 2026. Update at every Standard or Major change. This card is the basis for any public AI use-case listing.

## What it does

Answers plain-language questions about Canadian population groups ("How many Ontarians aged 25–44 stream video weekly, by income?") with weighted tables, reliability flags and a short narrative, using Statistics Canada public use microdata.

## Intended users and uses

- **Users:** trained analysts and planners in government, research, media and marketing.
- **Intended uses:** exploring audiences, sizing populations, briefing preparation, checking hypotheses before deeper analysis.

## Out of scope

- Decisions about any individual, client, applicant or employee.
- Geographies finer than PUMFs support (neighbourhoods, most municipalities).
- Causal claims; the data are cross-sectional surveys.
- Publishing figures as official Statistics Canada estimates without analyst review.
- Questions outside the loaded surveys; the assistant should say it cannot answer.

## How it works

1. An LLM parses the question into intent.
2. Hybrid search over a curated variable catalog finds candidate variables; an LLM reranks them, or asks the user to clarify.
3. An LLM writes a JSON query spec, validated against a [schema](../schemas/query-spec.schema.json) and the catalog.
4. A deterministic engine (DuckDB) computes weighted estimates, indexes and variance.
5. A reliability guard suppresses or flags estimates by coefficient of variation and minimum sample size.
6. An LLM writes the narrative from the finished table; a checker confirms every figure matches.

The LLMs never see respondent-level data and never produce numbers.

## Models and data

| Component | AWS deployment | Google Cloud deployment |
| --- | --- | --- |
| Language model | Claude Haiku 5.5, Bedrock Canada cross-Region inference | Gemini 3.5 Flash, Vertex AI Montréal endpoint |
| Embeddings | Titan Text Embeddings V2 | Vertex AI text embeddings |
| Data | CIUS PUMF (2022, 2020, 2018); Census 2021 PUMF | Same |

Model versions are pinned; changes follow the change-control rules in [ai-governance.md](../docs/ai-governance.md#8-change-control).

## Evaluation

| Measure | Target before pilot | Result |
| --- | --- | --- |
| Exact spec match, golden set | At least 90% | To be measured at gate G2 |
| Variable-selection recall | At least 95% | To be measured |
| Numeric correctness | 100% (engine-computed) | To be measured |
| Narratives carrying required caution flags | 100% | To be measured |
| Subgroup suppression review | Completed | Pending |

## Known limitations

- Variable mapping can still be wrong when a concept is ambiguous; the spec and labels are always shown so users can check.
- CIUS and Census are separate samples; cross-survey sizing is model-based and labelled.
- Question wording changes between survey cycles; trend answers depend on steward-approved comparability notes.
- Smaller population groups are more often suppressed for reliability, which can reduce their visibility.

## Oversight and contact

Every answer is a draft for analyst review; caution-flagged figures need acknowledgement before export, and any external publication needs analyst sign-off. Questions, corrections and complaints go to the AI system owner (contact to be named at deployment).
