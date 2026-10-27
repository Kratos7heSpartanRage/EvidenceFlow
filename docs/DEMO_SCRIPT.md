# EvidenceFlow: Official 5-Minute Hackathon Demo Script
**Team:** EvidenceFlow Team (Member D: Frontend & Demo Presenter)  
**Hackathon Target:** Mini-Rayyan (72 Hours)  
**Key Pitch:** *?Change your search as often as you like. EvidenceFlow shows exactly what changed and never loses a decision you made.?*

---

## Pre-Demo Checklist (At T-10 Minutes)
- [ ] Dev server running (`npm run dev` at `http://localhost:5173`)
- [ ] Reset Demo button clicked to restore pristine baseline state
- [ ] Reviewer set to `Member D (Lead)` in the top navigation bar
- [ ] Browser window sized to 1080p (1920x1080) at 100% zoom
- [ ] Backup screen recording ready in background in case of connectivity issues

---

## Timeline & Scene-by-Scene Talk Track

### 0:00 ? 0:30 | The Systematic Review Bottleneck (Problem Hook)
* **Screen:** EvidenceFlow Dashboard (`Step 0: Protocol & Criteria`)
* **Speaker Talk Track:**
  > *"Every year, systematic review teams spend months manually screening tens of thousands of biomedical abstracts across PubMed and Europe PMC. But literature search is an iterative loop: you tweak a keyword, expand a date range, or add a comparator. Traditionally, the moment you touch your search query, your screening workspace resets ? and weeks of reviewer decisions are destroyed.*
  > *This is EvidenceFlow. We built an auditable systematic review workspace that treats query evolution as a first-class loop. Change your query anytime: EvidenceFlow shows you exactly what changed and mathematically guarantees that not a single human decision is ever lost."*

---

### 0:30 ? 1:15 | Step 0 & Live Query Execution (Steps 0, 1, 2)
* **Actions:**
  1. Show **Step 0 Protocol Card**: Point out the structured PICO question: *"In adults with type 2 diabetes, does metformin, compared with placebo, lower HbA1c?"*
  2. Highlight the **Inclusion & Exclusion Criteria table**: Notice that every single criterion has a mandatory one-line rationale (e.g. Non-Human studies, Non-English literature, In Silico models).
  3. Click **Step 1-2: Search & Fetch** in the sidebar.
  4. Point out the Boolean search expression: `("type 2 diabetes" OR "type II diabetes") AND metformin AND placebo`.
  5. Point out the prominent **NCBI Disclaimer Notice**: Official compliance with NLM EFetch terms, copyright notices, and rate-limiting.
  6. Click **Preview Hits & Sample Abstracts**: Show that 1,842 estimated hits are found, and the top 10 sample abstracts load instantly.
  7. Click **Approve & Import (Run Pipeline)**.
* **Speaker Talk Track:**
  > *"We begin in Step 0 with an immutable review protocol. Notice our criteria: every single exclusion has a documented rationale and a detection engine.*
  > *Now in Steps 1 and 2, we query Europe PMC and PubMed APIs directly from within the workspace. Notice our official NCBI compliance disclaimer. We preview the hit counts ? 1,842 hits ? and upon researcher approval, we launch an auditable 7-step pipeline."*

---

### 1:15 ? 2:00 | Transparent Pipeline & Deduplication Queue (Step 4)
* **Actions:**
  1. Open the **Pipeline Run Drawer**: Show the 7 discrete steps executing: `fetch` ? `store` ? `dedup` ? `reconcile` ? `screen` ? `pico` ? `diff`.
  2. Click **Step 4: Deduplication** in the sidebar.
  3. Show the side-by-side comparison of **Pair #1** (Record #101 BMJ Europe PMC record vs Record #102 BMJ PubMed record):
     - Point out **Auto-Duplicate (100%)** badge.
     - Green matched fields: `doi_norm`, `pmid`, `title_norm`, `year`, `first_author`.
  4. Show **Pair #2** (Kahn et al. 2017 Journal Article vs 2016 Meeting Abstract):
     - Point out the **Uncertain Pair (88%)** badge and the **Conference vs. Journal Guard Warning**: *"Separate reports of the same study are not duplicates."*
  5. Click **Confirm Duplicate** on Pair #1. Point out: Record #102 is hidden, NEVER deleted, preserving provenance.
* **Speaker Talk Track:**
  > *"The slide-out run log ticks through our 7 transparent pipeline steps. Step 4 deduplicates both within and across databases. Look at Pair #1: the exact same trial indexed in PubMed and Europe PMC. It matches on DOI and PMID, scored 100%, and when we confirm it, the duplicate is hidden ? never deleted.*
  > *Now notice Pair #2: our conference guard detects that one is a meeting abstract and one is a journal article. EvidenceFlow halts and asks the human reviewer to decide."*

---

### 2:00 ? 2:45 | Screening Queue, Hotkeys & PICO Highlights (Steps 5 & 6)
* **Actions:**
  1. Click **Step 5: Screening Queue** in the sidebar.
  2. Point out visual badge distinction:
     - **Outline Badges** = Machine Suggestions with hover tooltip showing rule hits and metadata evidence.
     - **Solid Badges** = Human Decisions with reviewer name, timestamp, and origin.
  3. Select **Record #105** (Sprague-Dawley Rat study):
     - Press keyboard hotkey **E** (or click Exclude).
     - Show the **Exclusion Reason Required Modal**: Demonstrate that the Confirm button is disabled until a criterion or reason is provided.
     - Select **Non-Human Studies** and submit.
  4. Select **Record #109** (Adolescent study): Press hotkey **M** (Maybe).
  5. Click **Step 6: PICO Extraction** in the sidebar:
     - Show Record #101: Highlighted spans in 4 tailored colors: Population (Indigo), Intervention (Cyan), Comparator (Amber), Outcome (Emerald).
     - Point out: Missing comparator alerts the reviewer with *"Comparator Unknown / Not Detected"*.
     - Click an existing span and demonstrate instant correction.
* **Speaker Talk Track:**
  > *"In Step 5, machine suggestions and human decisions are visually distinct. Suggestions use outlined badges with transparent evidence tooltips. Human decisions are solid badges.*
  > *Let's test our hard constraint: we press 'E' to exclude this rat study. The modal pops up: exclusion is physically blocked without an explicit reason. We select 'Non-Human' and confirm.*
  > *In Step 6, included abstracts are parsed into Population, Intervention, Comparator, and Outcome spans with highlighted character offsets. Our custom comparator rule flags when a study lacks an explicit comparator, preventing false claims."*

---

### 2:45 ? 4:00 | The Centerpiece: Query Evolution & Decision Preservation (Level 2 Loop)
* **Actions:**
  1. Click **Level 2: Query Evolution & Diff** in the sidebar.
  2. Showcase the **Query Evolution & Decision Preservation Dashboard**:
     - **Records Added:** `+45`
     - **Already Present:** `500`
     - **Decisions Preserved:** `498` *(100% reviewer time saved!)*
     - **Inherited Decisions:** `+42` *(automatically inherited by duplicates)*
     - **Groups Merged:** `2`
     - **Open Conflicts:** `1`
  3. Click **Resolve ?** on the Open Conflicts card to navigate to **Conflicts Workspace**:
     - Show the conflict: Record #110 was Included by Member A in v1, but Record #111 was Excluded by Member C in v2. Deduplication merged them.
     - Emphasize: **Conflicts are never resolved silently.**
     - Click **Unify Group Decision** ? select **Include All** with note: *"Reconciled as early T2D population"* ? click **Apply Resolution**.
  4. Return to **Query Evolution & Diff** screen.
  5. Click **Exact Revert to v1**:
     - Show the confirmation dialog: *"Restores exact group snapshot and active record set of v1 with ZERO external API calls."*
     - Confirm revert: Point out instantaneous restoration and audit notification.
* **Speaker Talk Track:**
  > *"Now for the hackathon centerpiece: the Level 2 Loop. We broadened our search in Version 2. Look at this screen: built completely on persisted database state.*
  > *EvidenceFlow computed the exact diff: 45 new records added, 500 already present, 498 reviewer decisions preserved without re-screening, and 42 decisions inherited.*
  > *Notice this red alert: 1 Open Conflict. When our query expanded, two records previously judged differently by Member A and Member C merged into one group. Rather than silently overwriting or picking a winner, EvidenceFlow flagged an open conflict and blocked export until human resolution.*
  > *And if the lead investigator wants to revert to Version 1? We click 'Exact Revert'. It restores the exact v1 record set and group snapshot instantly, with zero API refetching."*

---

### 4:00 ? 4:35 | Audit Trail & Standard CSV Export (Audit & Step 7)
* **Actions:**
  1. Click **Audit Trail** in the sidebar:
     - Show the append-only ledger: `confirm_duplicate_pair`, `screening_decision`, `resolve_conflict`, `exact_revert`.
     - Click an event to expand the side-by-side **State Before vs. State After** JSON diff.
  2. Click **Step 7: Review & CSV Export**:
     - Show the synthesis preview table containing included representative studies and extracted PICO tags.
     - Click **Download CSV Export**: The `.csv` file downloads immediately to the presenter's computer.
* **Speaker Talk Track:**
  > *"Every single mutation is recorded in our append-only audit trail with exact before-and-after JSON snapshots. Nothing is ever lost or hidden from auditors.*
  > *Finally, Step 7 exports our synthesized review into standard CSV format with verified representative records, reviewer notes, and structured PICO annotations ready for statistical meta-analysis."*

---

### 4:35 ? 5:00 | Architecture Summary & Conclusion
* **Actions:**
  - Bring up the Architecture overview slide or summary.
* **Speaker Talk Track:**
  > *"To summarize our architectural principles:
  > 1. Pure Engines: deduplication, screening, and PICO are pure, testable mathematical functions with zero database coupling.
  > 2. Immutability: queries and protocol criteria are versioned and immutable; records are never deleted.
  > 3. Decision Preservation: decisions belong to the entity group, guaranteeing seamless repeatability across the query loop.
  > Thank you! We are excited to take your questions."*

---

## Judge Q&A Cheat Sheet
1. **Q: What happens if an excluded record reappears under a newly broadened query?**  
   *A: Provenance uniqueness is `(review_id, source, source_record_id)`. The existing record is recognized, its exclusion status is preserved, and the diff view highlights it under 'already present, previously Excluded'.*
2. **Q: How do you guarantee exact reproducibility on revert?**  
   *A: Each pipeline run persists a snapshot of `(run_id, record_id, group_key, is_representative)`. Reverting simply activates that stored snapshot; no network calls or re-grouping are executed.*
3. **Q: Why are machine suggestions separate from human decisions?**  
   *A: Human decisions live in append-only tables (`screening_decision`, `pair_decision`), whereas machine suggestions live in `screening_suggestion`. Machine algorithms can re-run without ever corrupting human work.*
