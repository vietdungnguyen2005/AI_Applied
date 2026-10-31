# SIMULATED discovery transcript

**Roleplay written by the coding agent on 2026-10-31. No interview occurred. Names, roles and answers below are fictional. They are design hypotheses, not customer testimony or validation.** Source-confirmed behavior is only the F01–F10 register in [problem statement](problem-statement.md).

**Engineer:** Which task should we try first?

**Operator persona:** I would like to find a supplier procedure and understand a new header before I preview a file. I want to see why a mapping was suggested. [Simulated desire D01/D02]

**Engineer:** Would a mapping suggestion authorize an import?

**Operator persona:** No. I would review it, choose the right vendor and use the normal profile and approval process. [Proposed acceptance preference; current code's approval boundaries are F03–F07]

**Supplier A persona:** Our example uses 商品コード, 商品名 and 在庫数 in CP932. A label does not prove the quantity is current. [Synthetic example based on seeded contract, F01/F02; freshness concern A03]

**Supplier B persona:** Our example uses SKU, ProductName and AvailableQuantity in UTF-8. An unfamiliar header should come back for clarification. [Seeded contract plus proposed abstention preference]

**Support persona:** If a job fails, show the observed job/work state and bounded error reasons. Do not tell me to restart a BLOCKED job or claim a timeout rolled back the import. [Simulated D03; recovery behavior must follow F06]

**Security persona:** Keep browser cookies and CSRF out of the AI service. A supplier filter must not be sold as tenant isolation. Recheck permissions whenever a tool runs. [Proposed D04; current boundaries F07/F10]

**Engineer:** What outcome would justify the assistant?

**Operator persona:** Fewer corrections and faster accepted mappings might help, but we have not measured either. Incorrect mappings are worse than an honest no-answer. [Hypothesis; no measured result]

**Engineer:** Who can approve the SOP corpus and independent gold labels?

**Security persona:** That owner has not been identified in this simulation. Keep the corpus synthetic and mark developer-reviewed labels until a real reviewer exists. [Open issue O01]

**Engineer:** We will compare rules and AI using fixed cases. We will keep the existing manual workflow available. This roleplay creates no contractual commitment, security approval or production permission.

## Interpretation

- Confirmed: encoding, profile, receipt and authorization behavior come from source, not these personas.
- Proposed: journey priorities, presentation details and quality targets are engineering choices pending review.
- Unknown: real operator time, real business impact, policy ownership, willingness to adopt and independent human judgments.
