# AI governance model

November 2026

This model governs the PUMF Insights Assistant across its life cycle and maps every control to four frameworks: the NIST AI Risk Management Framework, ISO/IEC 42001, Ontario's Responsible Use of Artificial Intelligence Directive, and the federal Directive on Automated Decision-Making with its Algorithmic Impact Assessment.

Supporting artifacts live in [`../governance/`](../governance/):

- [Risk register](../governance/risk-register.md) ([CSV](../governance/risk-register.csv))
- [System card](../governance/system-card.md)
- [Algorithmic impact self-assessment](../governance/algorithmic-impact-assessment.md)

## 1. System classification

| Attribute | Classification |
| --- | --- |
| Purpose | Decision support for media, marketing and policy planners: answers questions about Canadian population groups |
| Decisions about individuals | None. Outputs describe population groups, never a person, client or applicant |
| Data | Statistics Canada public use microdata (anonymized by StatCan before release); no personal information collected from users beyond sign-in |
| AI techniques | LLMs for intent parsing, variable selection, query planning and narration; deterministic statistics for all figures |
| Autonomy | The assistant proposes; a human decides what to use. No action is taken in any other system |
| Users | Trained analysts and planners, not the public |
| Overall risk tier | **Moderate**: low harm to individuals, but a real risk of misinformed planning decisions if a wrong or unreliable figure is used |

## 2. Which frameworks bind, and when

| Framework | Status | How this model uses it |
| --- | --- | --- |
| [NIST AI RMF 1.0](https://www.nist.gov/itl/ai-risk-management-framework) and the [Generative AI Profile (NIST AI 600-1)](https://www.nist.gov/itl/ai-risk-management-framework) | Voluntary. Version 1.0 (Jan 2023) is being revised; the GenAI profile dates from July 2024 | Organizing structure (Govern, Map, Measure, Manage) and the GenAI risk categories used in the risk register |
| ISO/IEC 42001:2023 | Voluntary, certifiable management-system standard | Management-system clauses (context, leadership, planning, support, operation, evaluation, improvement) and Annex A control objectives |
| [Ontario Responsible Use of AI Directive](https://www.ontario.ca/page/responsible-use-artificial-intelligence-directive) | **Binding** on Ontario ministries and provincial agencies since December 1, 2024 | Mandatory if a ministry or agency deploys the assistant: risk management, annual reporting, public use-case listing, disclosure |
| [Enhancing Digital Security and Trust Act, 2024](https://www.ontario.ca/page/enhancing-digital-security-and-trust-act) | AI duties not in force; they wait for a regulation ([summary](https://www.fruggr.io/en/ontario-bill-194-ai-public-sector-rules-2026/)) | Watched; the controls below already cover disclosure, accountability, risk management and oversight |
| [Directive on Automated Decision-Making](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592) and AIA | Binding only on federal institutions making administrative decisions ([scope guide](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/guide-scope-directive-automated-decision-making.html)) | Not legally applicable; used voluntarily as a benchmark for impact assessment, explanation, testing and peer review |

The non-binding [IPC and OHRC principles for responsible AI](https://www.ipc.on.ca/en/media/6141/download) (January 2026) are also reflected, since Ontario's regulators have said they will use them in assessments.

## 3. Principles

The six principles of the Ontario directive (section 5) are adopted as the system's principles, each tied to concrete controls in this model.

| Ontario principle | What it means here | Main controls |
| --- | --- | --- |
| 5.1 Benefits outweigh risks | Faster, consistent access to official survey data, with documented risks | Risk register; gate G1 |
| 5.2 Justified, proportionate, reliable and valid | Figures come from a deterministic engine; LLM use limited to translation and narration | Number checker; evaluation set; reliability guard |
| 5.3 Safe, secure, privacy-protective | No microdata reaches an LLM; Canadian residency; least privilege | Role separation; PIA/TRA; residency checks |
| 5.4 Human rights affirming, non-discriminatory | Small groups are not silently dropped or overstated | Subgroup suppression monitoring; bias review |
| 5.5 Transparent and explainable | Every answer shows its spec, source, release and reliability flags | Answer explanation panel; public use-case listing |
| 5.6 Accountable, with ongoing human oversight | Named owners; humans decide what to publish | RACI; oversight rules; kill switch |

## 4. Roles and accountability

| Role | Who | Accountable for |
| --- | --- | --- |
| Accountable executive | Deputy minister or agency head (public deployment), or product owner (commercial deployment) | Risk acceptance, go-live approval, directive compliance |
| AI system owner | Product or program lead | Day-to-day governance, this document, annual reporting |
| Data steward | Statistician or survey methodologist | Catalog quality, release approval, reliability rules, golden questions |
| Independent model risk reviewer | Someone outside the build team | Gate reviews, evaluation sign-off, peer review |
| Privacy and security | Privacy office, CISO delegate | PIA, threat risk assessment, incident response |
| Equity and human rights reviewer | Policy or human rights advisor | Bias review of subgroup outputs and narratives |
| Platform engineering | Cloud and ML engineers | Controls in code, monitoring, change execution |
| Users | Trained analysts and planners | Reviewing outputs before use; flagging errors |

**RACI** (R responsible, A accountable, C consulted, I informed)

| Activity | Exec | Owner | Steward | Reviewer | Privacy/Sec | Equity | Eng |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| Use-case intake and classification | I | A/R | C | C | C | C | I |
| Risk assessment and register | A | R | C | C | C | C | C |
| Impact assessment (AIA-style) | A | R | C | C | C | C | I |
| PIA and threat risk assessment | I | A | I | I | R | I | C |
| Evaluation set and thresholds | I | A | R | C | I | C | C |
| Go-live and gate approvals | A | R | C | C | C | C | I |
| Model or prompt change | I | A | C | R | C | I | R |
| New PUMF release | I | A | R | C | I | I | R |
| Monitoring and KRIs | I | A | C | C | C | C | R |
| Incident response | I | A | C | C | R | C | R |
| Annual reporting and public listing | A | R | C | I | C | I | I |

## 5. Life cycle and gates

No gate passes without its evidence filed in the governance record.

| Gate | When | Evidence required | Approver |
| --- | --- | --- | --- |
| G0 Intake | Before design | Use-case description, classification (section 1), applicable frameworks | AI system owner |
| G1 Design review | Before build | Risk register v1, impact self-assessment, PIA and TRA screening, data licence check, residency confirmation | Accountable executive, after reviewer and privacy input |
| G2 Pre-pilot | Before any user sees it | Evaluation results meeting thresholds (section 7), red-team results, system card draft, user notice text | Independent reviewer, then executive |
| G3 Production | After pilot | Pilot findings, KRIs within thresholds for 30 days, training complete, public listing and disclosure ready | Accountable executive |
| G4 Change | Any model, prompt, catalog-logic or release change | Change class (section 8), regression evaluation, updated system card | Per change class |
| G5 Retirement | When replaced or no longer justified | Data and log retention plan, user notice, listing updated | AI system owner |

Gates G1 to G3 map to ISO/IEC 42001 clause 8 (operation) and Annex A.6 (life cycle), to NIST MAP and MEASURE, and to the Ontario directive's risk-management process in section 6.1.

## 6. Human oversight

The assistant supports human judgment; it does not replace it.

1. **Every answer is a draft.** The interface labels outputs as AI-assisted and shows the query spec, data source, release and reliability flags beside the narrative.
2. **Caution-flagged estimates** (CV 16.6% to 33.3%, or as the release guide sets) cannot be exported without the user acknowledging the flag.
3. **Model-based sizing** (CIUS rate × Census count) is always labelled as such and never presented as an official StatCan estimate.
4. **External publication** of any figure (a report, a briefing note, a client deliverable) requires an analyst to check it against the table and spec. The answer log records who exported what.
5. **Users can correct or flag** any answer; flags go to the steward's weekly triage.
6. **Kill switch:** the AI system owner or CISO delegate can disable the LLM steps in minutes, leaving the manual crosstab tool available.

## 7. Monitoring and key risk indicators

| Indicator | Threshold | Action when breached |
| --- | --- | --- |
| Golden-set exact spec match | At least 90% (set at G2) | Block release or change; investigate |
| Variable-selection recall on golden set | At least 95% | Block; improve catalog or prompts |
| Number-checker failures reaching a user | 0 | Sev 1 incident |
| Narratives omitting a required caution flag | 0 in weekly sample | Sev 2; fix narrator prompt |
| Clarify-question rate | Within ±50% of 4-week baseline | Investigate catalog or intent drift |
| Suppression rate for subgroup questions | Reviewed monthly by subgroup | Equity review if one group's rate rises sharply |
| User-flagged wrong answers | Under 1% of answers | Root-cause review |
| Inference outside Canada | 0 requests | Sev 1; disable LLM steps |
| Vendor model deprecation notice | Any | Open change; plan re-evaluation |
| Cost per answered question | Within 25% of budget | Review routing and caching |

Monitoring maps to NIST MEASURE 3 and MANAGE 4, ISO/IEC 42001 clause 9 (performance evaluation), and the Ontario directive's requirement to monitor and update risk assessments (section 6.1).

## 8. Change control

| Change class | Examples | Minimum testing | Approver |
| --- | --- | --- | --- |
| Major | New model or model provider; new survey; new output type; residency or routing change | Full golden set, red-team, bias review, updated impact assessment and system card | Accountable executive, after independent review |
| Standard | Prompt change; retrieval logic change; new PUMF release of an existing survey | Full golden set; release quality rules | Independent reviewer and data steward |
| Minor | Label wording, synonyms, UI text | Spot check of affected golden questions | Data steward |
| Emergency | Kill switch; reverting to the last approved model or prompt | Post-change golden set within 2 business days | AI system owner, ratified at next review |

Every change records the before and after versions in the answer log so any past answer can be reproduced.

## 9. Incident management

| Severity | Definition | Response target |
| --- | --- | --- |
| Sev 1 | A wrong figure reached a user or was published; inference left Canada; data exposure | Contain within 4 hours (kill switch if needed); notify executive and privacy/security; correct affected outputs |
| Sev 2 | A required caution or label missing; repeatable wrong variable mapping | Fix within 5 business days; notify affected users |
| Sev 3 | Degraded quality within thresholds; isolated user flags | Triage weekly |

Security incidents follow the organization's CISO process. Under the Ontario directive the CISO may block activities posing imminent security risk (section 7). Each Sev 1 or Sev 2 gets a post-incident review whose findings feed the risk register and golden set.

## 10. Transparency

- **In the product:** an AI-use notice at sign-in, labels on every AI-written narrative, and an "how this answer was made" panel (question interpretation, variables chosen, release, weights, reliability flags).
- **Public:** when an Ontario ministry or agency deploys it, the use case is reported annually and published in the government's AI use-case list (directive section 6.2), with an accessible contact for questions. The system card is the basis for that listing.
- **Explanations:** because every figure comes from a stored query spec, any answer can be re-run and explained exactly, which meets the DADM's meaningful-explanation expectation even though the directive does not apply.

## 11. Data and third parties

- **Data:** PUMF licence terms are recorded per release; only StatCan-anonymized microdata is used; narrow cells are suppressed by the reliability guard, which also limits disclosure risk from combinations.
- **Model providers:** contracts confirm prompts and outputs are not used for training, retention periods, and Canadian processing (Bedrock Canada inference profile or Vertex AI Montréal endpoint). Provider model cards and deprecation schedules are tracked.
- **Residency check:** an automated daily test confirms the configured inference profile or endpoint is Canada-only.

## 12. Competence and training

Users complete a short course before access: reading CVs and reliability flags, the limits of PUMF geography, model-based versus direct estimates, and the oversight rules in section 6. Stewards and reviewers get the evaluation and change-control procedures. Completion is recorded, which supports ISO/IEC 42001 clause 7.2.

## 13. Framework crosswalk

| Control area | NIST AI RMF (function, category) | ISO/IEC 42001 | Ontario directive | DADM / AIA (voluntary) |
| --- | --- | --- | --- | --- |
| Policy, principles, legal context | GOVERN 1 | Cl. 5.2; A.2 | s.5 principles; s.4 scope | Policy objectives |
| Roles and accountability | GOVERN 2 | Cl. 5.3; A.3 | s.7 roles | Assistant deputy minister accountability (federal) |
| Use-case intake and classification | MAP 1, MAP 3 | Cl. 4.1–4.3; A.5 | s.6.1 context | Scope test; AIA questionnaire |
| Risk assessment and register | MAP 4, MAP 5; GOVERN 4 | Cl. 6.1; 8.2 | s.6.1 risk process | AIA impact level |
| Impact assessment | MAP 5 | A.5 | s.6.1 | AIA |
| Data quality, provenance, licence | MAP 2; MEASURE 2 | A.7 | s.5.2 reliability | Data quality requirements |
| Evaluation and testing | MEASURE 1, MEASURE 2 | Cl. 8.3; A.6 | s.5.2 | Testing before production |
| Bias and equity review | MEASURE 2; MAP 2 | A.5; A.6 | s.5.4 | Gender-based analysis plus, bias testing |
| Independent review | GOVERN 4; MEASURE 4 | Cl. 9.2 internal audit | s.6.1 validation by IT and digital governance | Peer review |
| Human oversight | GOVERN 3; MANAGE 2 | A.9 | s.5.6 | Human intervention |
| Transparency and notice | GOVERN 4; MAP 1 | A.8 | s.6.2 disclosure and public listing | Notice and explanation |
| Monitoring and KRIs | MEASURE 3; MANAGE 4 | Cl. 9.1 | s.6.1 monitor and update | Ongoing monitoring |
| Change control | MANAGE 2; GOVERN 1 | Cl. 8.1; A.6 | s.6.1 | Reassess on significant modification |
| Incident management | MANAGE 4 | Cl. 10.2 | s.7 CISO powers | Recourse |
| Third-party models and vendors | GOVERN 6; MANAGE 3 | A.10 | Procurement through I&IT governance | Procurement and licence requirements |
| Training and competence | GOVERN 2 | Cl. 7.2, 7.3 | s.7 training support | Employee training |
| Reporting and records | GOVERN 1; MANAGE 4 | Cl. 7.5; 9.3 | s.6.2 annual reporting | Publication of AIA results |
| Continual improvement | MANAGE 4 | Cl. 10.1 | s.6.1 | Periodic review |

NIST cells cite categories rather than subcategories because AI RMF 1.0 is under revision. Ontario section numbers refer to the directive as published on ontario.ca (updated January 7, 2026).

## 14. Review cycle

This model is reviewed at least annually and after any Major change or Sev 1 incident. The Ontario directive itself is reviewed at least every two years, so check for updates at each review.
