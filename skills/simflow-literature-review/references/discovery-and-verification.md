# Discovery And Verification

## Corpus First

1. Inventory user-provided PDF, BibTeX, DOI, Zotero, or other local corpus
   material before external search.
2. Apply the same inclusion criteria to local and external candidates.
3. Report local entries that could not be screened; do not silently drop them.
4. Search external indexes only for unresolved identity, topic, date, method,
   contradiction, or coverage gaps.

## Multi-Source Use

- Treat Crossref as strong DOI registration metadata, not full-text evidence.
- Use OpenAlex and Semantic Scholar for discovery, identifiers, citation graph,
  and complementary metadata.
- Use arXiv for preprint identity, version history, and lawful open full text.
- Preserve provider-specific observations and conflicts. Do not overwrite a
  disagreement into a falsely certain citation.

## Identity And Deduplication

Merge automatically only when one of these holds:

- exact normalized DOI;
- exact normalized arXiv identifier, ignoring version for work identity;
- exact provider identifier from the same provider;
- near-exact normalized title plus compatible first author and publication
  year.

Title similarity alone is a candidate match, not a merge decision. Validate a
DOI against returned title, first author, and year before relying on it.

## Snowballing

Use backward references and forward cited-by search from relevant seed papers.
Keep the seed, direction, provider, depth, and parent paper traceable. Default
to depth one and bounded results; expand further only when the first pass
reveals a material evidence gap.
