---
name: simflow-literature-review
description: Guide reliable literature discovery, screening, source verification, and evidence-bounded synthesis for computational simulation research.
---

# Literature Review

## Purpose

Help the agent establish a reliable scientific background without inventing
sources, overstating abstracts, or confusing secondary summaries with primary
evidence.

## Use when

- The user asks to find, screen, compare, or synthesize scientific literature.
- A research decision depends on published methods, parameters, benchmarks, or
  competing interpretations.
- Existing citations or factual claims need source verification.

## Do not use when

- The user only asks to format already verified citations.
- The task is primarily calculation setup, output analysis, or manuscript
  drafting and no new literature judgment is needed.

## Task principles

- Prefer primary sources for methods, parameters, and scientific claims.
- Trace important claims back to the original paper rather than a citing paper.
- Separate what a source reports from the agent's inference.
- Treat title and abstract screening as provisional until the relevant full text
  is checked.
- Preserve disagreement, uncertainty, and scope limits instead of forcing a
  single narrative.
- Never fabricate a citation, DOI, quotation, author list, or access result.

## Minimum checks

- Confirm bibliographic identity for every source used in a key conclusion.
- Record the search scope, inclusion logic, and obvious evidence gaps.
- Verify that quoted or paraphrased claims match the cited source.
- Distinguish peer-reviewed articles, preprints, reviews, documentation, and
  informal sources.
- State when full text was unavailable or only partial evidence was inspected.

## Common failure modes

- Expanding an abstract claim beyond the paper's actual evidence.
- Citing a review when an original parameter or result is available.
- Treating citation count or recency as a quality guarantee.
- Hiding contradictory papers or negative results.
- Producing a polished bibliography with unverified metadata.

## Escalate uncertainty when

- A key source is inaccessible, ambiguous, retracted, or internally inconsistent.
- Sources disagree in a way that changes the proposed scientific path.
- The requested evidence threshold or date range materially changes the answer.

## Completion criteria

- The review answers the user's question with traceable sources.
- Selection limits and unresolved evidence gaps are explicit.
- Factual claims, interpretations, and recommendations are clearly separated.

## Optional references

Use host search tools, local PDFs, Zotero, scholarly indexes, or user-provided
collections as appropriate. No particular provider is required.
