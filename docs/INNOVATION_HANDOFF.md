# Review intelligence: final-submission handoff

The workspace now has a **Review Intelligence** tab with two read-only views. Both work on the selected review's stored, live-source records. They do not create or overwrite human decisions.

## Old exclusions to reconsider

Create a new criteria version after screening papers with an exclusion linked to a criterion. The view compares the two latest criteria versions. When an exclusion criterion's description broadens, it flags earlier exclusions linked to that criterion if newly added words appear in the title or abstract. It displays the old reason, new criterion, reviewer and a source-text excerpt. Removing a criterion flags all active exclusions linked to it.

Demo: exclude a real adolescent paper under an `Adults only` criterion, then make the next version `Adults and adolescents`. The paper appears as a candidate to revisit. It remains excluded until a reviewer changes the decision in Screening.

This is a transparent lexical candidate finder, **not a trained semantic embedding model**. It can miss synonyms, paraphrases, and decisions without a linked criterion. Do not claim measured recall or automated eligibility decisions.

## Study families

The same tab lists duplicate records from the existing deduplication groups. It separately lists possible publications from the same registered trial when distinct deduplication groups share an `NCT` registration ID in the title or abstract. A shared registration is a candidate relationship, not proof that two articles report the same analysis or should be counted once. Unrelated papers have no edge.

The checkpoint review currently contains two cross-source duplicate groups. It has no detected NCT-linked separate-report family in its imported abstracts. New live searches can produce these dynamically.

These views provide a useful first release, but a learned criterion classifier, semantic embeddings, family-level graph layout, and expert-labelled precision/recall remain future work.

## Deployment

The backend process serving the local app was restarted with the existing root database. Refresh the browser to load the new tab. None of this work has been committed or deployed to Render. The prepared Render files are in the repository root; deployment requires a Git commit, which the user has explicitly deferred.
