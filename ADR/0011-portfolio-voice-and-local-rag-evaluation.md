# ADR 0011: Portfolio voice and local RAG evaluation (implementation pending)

- **Status:** Accepted
- **Date:** 2026-10-26
- **Implementation status:** Pending

## Context

The recruiter-facing assistant should feel more familiar and recognize that it
lives in Adrián's portfolio, while continuing to describe Adrián's career and
work accurately. Recruiters may also ask about portfolio and architecture
details in project documentation beyond the CV and generated project brief. It
is not yet established that these details exceed the prompt budget or that
retrieval improves the answers.

The current runtime grounds responses in `cv.md` and generated
`docs/PROJECT.md`. `cv.md` is local and excluded from Git. The project has no
vector store or embedding model today. ADR 0002 deferred repository RAG due to
its added dependencies, infrastructure, and latency.

## Decision

### Portfolio voice

- The assistant speaks as the voice of Adrián's portfolio. A fox is a visual
  mascot only; it has no name and is not a speaking character.
- Mirror the visitor's language. In Spanish, use tuteo with a conversational,
  warm and professional tone and subtle humor.
- Introduce the portfolio voice and explain that Adrián created the chatbot in
  the initial greeting; do not repeat this in every answer.
- Use first person to guide visitors through the portfolio, but refer to
  Adrián in third person when describing his career, projects, and authorship.
  For example: “Adrián creó este chatbot”, not “yo creé este chatbot”.

### Public CV and retrieval corpus

- Evolve the local `cv.md` into the public, approved CV used by the chatbot;
  keep it out of Git. Remove contact details and confidential client details.
  Retain employers, roles, dates, and achievements that Adrián approves for
  public answers.
- Index the public CV, generated `docs/PROJECT.md`, current factual sections of
  the README, and selected excerpts from ADRs 0001–0005 and 0007–0009.
- Exclude source code, secrets, operational configuration, local-development
  details, and observability data. Use only high-level, approved content from
  ADR 0009.
- Preserve source type, date, decision status, and supersession metadata. ADRs
  explain decisions in their historical context; do not present superseded
  decisions as current implementation. If sources disagree about a fact,
  explain the discrepancy and its sources rather than blending the claims.
- Attribute sources naturally when useful (for example, “En el CV…” or “En el
  proyecto…”). If retrieval finds no adequate evidence, say so and offer only
  related facts that are documented.

### Bounded local RAG evaluation

- Compare the existing no-RAG assistant with a local RAG candidate using the
  same chat model and a fixed set of Spanish and English questions covering CV
  facts, portfolio projects, architecture, historical decisions, missing
  evidence, and privacy.
- First candidate: Qdrant local mode with FastEmbed and a multilingual embedding
  model. `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` is the
  initial model candidate, subject to package and retrieval validation; no
  vector-store or model choice is final until the comparison passes.
- Adopt RAG only if it meaningfully improves technical and project answers,
  does not regress basic CV answers, and produces no unsupported claims or
  private-data leaks. Record cold-start and query latency. If it does not pass,
  retain the simpler no-RAG path.
- Calculate embeddings locally. Download the model on first use and persist its
  cache and the vector index outside the disposable container filesystem.
- At startup, detect changed sources and update only affected chunks. Use stable
  source/chunk identifiers and remove chunks for deleted or renamed sources.
- Give the generator and output guardrail the same retrieved passages and
  source metadata so the guardrail can verify the evidence used to answer.
- If RAG or its local model is unavailable, log the failure and continue using
  the existing CV and `docs/PROJECT.md` grounding path.

This ADR authorizes a bounded RAG evaluation and defines the portfolio voice; it
does not claim that a vector database, embedding model, or RAG retrieval is
implemented. It supersedes ADR 0002's RAG deferral only for this evaluation; a
production RAG implementation remains conditional on passing the criteria
above.

## Consequences

- The portfolio can speak with a recognizable, friendly voice without
  impersonating Adrián or claiming his experiences as its own.
- The chatbot's CV source becomes public-answer-safe while remaining local and
  uncommitted.
- Selected project and architecture documents become searchable without
  indexing the whole repository or treating historical decisions as current
  facts.
- Startup, disk usage, and query latency increase if RAG passes evaluation and
  is implemented; the comparison will determine whether the added complexity
  is worthwhile.
- The generator, prompt, guardrail, ingestion, persistence, and evaluation
  paths will need coordinated changes during implementation. Regenerate
  `docs/PROJECT.md` after adding this ADR and again for any later architecture
  changes.

## Alternatives considered

- **Keep the current neutral assistant voice:** rejected because the portfolio
  should feel more personal while preserving clear attribution to Adrián.
- **Have the fox speak as a separate named character:** rejected; the fox is
  only a visual mascot and the assistant represents the portfolio.
- **Index the complete repository:** rejected because it includes code,
  operational details, historical decisions, and private material that are not
  suitable recruiter-facing sources.
- **Adopt a vector store without comparing it to the current prompt-based
  approach:** rejected because the corpus is small and retrieval must justify
  its additional dependencies, startup time, and latency.
