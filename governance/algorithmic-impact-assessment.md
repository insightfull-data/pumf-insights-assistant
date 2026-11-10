# Algorithmic impact self-assessment

Preliminary, design stage, November 2026.

The federal [Directive on Automated Decision-Making](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592) applies only to federal institutions using automated systems for administrative decisions about clients ([scope guide](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/guide-scope-directive-automated-decision-making.html)). This assistant is not subject to it. This self-assessment borrows the Algorithmic Impact Assessment's question areas as good practice and as input to the risk assessment the [Ontario directive](https://www.ontario.ca/page/responsible-use-artificial-intelligence-directive) requires (section 6.1).

**This is not an official AIA score.** If a federal institution ever adopts the assistant to inform administrative decisions, complete the official AIA tool.

## Scope test

| Question | Answer |
| --- | --- |
| Does the system make or recommend a decision about a specific person or business? | No. Outputs describe population groups |
| Could an output affect someone's legal rights, privileges or interests? | Not directly. Indirect effects are possible if planning decisions rely on a wrong figure |
| Is personal information processed? | No respondent-identifying data; StatCan anonymizes PUMFs. User sign-in data only |
| Is the system in production? | Not yet (design stage) |

## Impact areas

| Area | Assessment | Rationale |
| --- | --- | --- |
| Rights and freedoms of individuals | Little to none | No individual decisions |
| Health and well-being | Little | Possible indirect effect via misallocated programs; mitigated by review rules |
| Economic interests | Little to moderate | Commercial planning decisions may rely on figures |
| Sustainability of ecosystems | Little | Low compute footprint |
| Reversibility | Reversible | Answers are reproducible and correctable; no automated action |
| Duration | Short | Effects last until a figure is corrected |

## Expected impact level

**Comparable to Level I (little to no impact)** for individuals, with a moderate risk to decision quality that is handled by the controls in the [risk register](risk-register.md). The governance model nonetheless adopts several requirements the directive sets for higher levels, because they are cheap here:

| Practice | Adopted |
| --- | --- |
| Plain-language notice of AI use | Yes |
| Meaningful explanation of each output | Yes, from the stored query spec |
| Testing before production, including bias | Yes, golden set and subgroup review |
| Independent peer review | Yes, independent reviewer at gates G2 and G4 |
| Human involvement in final use | Yes, analyst review before publication |
| Ongoing monitoring and periodic reassessment | Yes, KRIs and annual review |
| Gender-based analysis plus | Yes, as part of the subgroup equity review |

## Reassessment triggers

- Use to inform decisions about specific people, program eligibility, or funding for named organizations.
- Adding data that includes personal information.
- A Major change (new model provider, new survey, new output type).
- Any Sev 1 incident.
