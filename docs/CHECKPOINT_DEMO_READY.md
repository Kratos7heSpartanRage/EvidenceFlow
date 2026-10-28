# EvidenceFlow checkpoint demo

This is the prepared local walkthrough for the checkpoint. It uses live PubMed and Europe PMC records in the local database; the two disagreement decisions are deliberately labelled demo decisions, not clinical ground truth.

## Open the app

- UI: http://localhost:5173/
- API health/docs: http://127.0.0.1:8000/docs
- Select the review named `CHECKPOINT DEMO — Metformin: decisions survive a changed search`.

## Five-minute run

1. **Protocol** — show the PICO question: adults with type 1 diabetes; metformin versus placebo; HbA1c and carotid intima-media thickness. Point out that the criteria are versioned and exclusions require a reason.
2. **Query evolution** — open the two PubMed versions. Version 1 is `metformin AND REMOVAL` for 2017 and imported 28 records. Version 2 expands the date range to 2016–2018 and adds 63 new records while retaining all 28 earlier records. Show the diff and the two preserved decisions.
3. **Screening** — search for PMID `28615149`. Open the REMOVAL randomized trial and show the solid Include decision by Manas Jain. Then search for PMID `29139080` and show the preserved Exclude decision for the secondary review, with its written reason.
4. **Deduplication** — open the duplicate queue. Use the exact PubMed/Europe PMC REMOVAL pair as the cross-source example. Confirming a pair hides the duplicate record while retaining provenance; leave at least one pair pending until this point.
5. **Conflict** — open the conflicts view. The record titled `What role for metformin in type 1 diabetes?` has an Include by Manas Jain and an Exclude by Member C. Explain that EvidenceFlow stops and asks for explicit consensus. Resolve it only if the judges ask; otherwise leave it open to show the safeguard.
6. **PICO** — open the REMOVAL trial. Show the highlighted machine spans, then correct the intervention span to `metformin 1000 mg twice daily`. Mention that the correction is recorded as a human overlay and the raw annotation remains auditable.
7. **Export/audit** — show the audit trail and CSV preview. Explain that open conflicts are quarantined from export until resolved; the primary included trial remains available.

## Numbers to say

- 93 stored records, 91 unique study groups.
- 28 records in v1; 63 new records in v2; 28 retained.
- One included primary trial and one preserved excluded secondary review.
- One intentionally open Include/Exclude conflict.
- Duplicate examples include exact PubMed/Europe PMC copies.

## Presenter guardrails

- Say “real abstracts with demo reviewer decisions,” not “expert-labelled clinical evidence.”
- Do not claim a hosted URL until deployment is complete; these links are local.
- Do not click exact revert during the first rehearsal. Restore is query-specific and can hide records from the active view; use it only for the final query-version explanation.
- If a page looks stale, use **Refresh** in the header. The green **Backend Live** badge confirms the UI is connected to FastAPI.

