---
name: simflow-literature-review
description: Use when a user asks to collect, screen, or synthesize literature for a computational simulation question.
---

# SimFlow Literature Review

## Trigger conditions

- The user provides papers, PDFs, DOIs, citations, keywords, or a research question for literature review.
- The current research intent is to understand prior work, methods, datasets, open questions, or evidence quality.
- A later proposal, model, computation, analysis, or writing task needs source-backed context.

## Input conditions

- A research question, topic, uploaded paper set, citation list, or search intent.
- Optional user constraints such as time range, domain, language, venue, theory level, method family, or supplied PDFs.
- Existing `.simflow/` state may be used, but literature review can also be the entry stage.

## Output artifacts

- Search log or source log recording where each paper or source came from.
- Paper notes that separate direct source claims from agent interpretation.
- Review summary, gap list, citation map, or another user-requested literature deliverable.
- Access notes for sources without full text, inaccessible PDFs, or unverified metadata.

## Status write rules

- Resolve the user's current working directory as `project_root` before writing SimFlow state.
- Record literature artifacts with source, query, selection criteria, access status, and citation metadata when available.
- Link review summaries to their source notes or citation artifacts through lineage.

## Checkpoint rules

- Create a checkpoint when the literature review reaches a handoff boundary, such as search complete, screening complete, or synthesis complete.
- A checkpoint must identify unresolved access, metadata, citation, or interpretation risks.

## Prohibited actions

- Do not fabricate papers, citations, search results, quotes, data, or conclusions.
- Do not treat inaccessible full text as read.
- Do not require a specific literature database, PDF manager, parser, report filename, or citation format when the user has another reasonable path.

## Manual confirmation scenarios

- Search scope, screening criteria, or inclusion thresholds are ambiguous.
- Key papers are inaccessible, contradictory, or missing metadata.
- The user asks for claims that require stronger evidence than the available sources support.
