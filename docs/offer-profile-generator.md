# Offer-to-profile generator

## Goal

Create two deliverables from a job offer and the repo evidence:

1. A recruiter-facing profile tailored to the offer.
2. A PDF CV tailored to the same offer.

Both must stay grounded in the source material. Do not invent experience, credentials, titles, clients, impact, or production claims.

## Source of truth

Use only the repo evidence:

- `cv.md`
- `docs/PROJECT.md`
- `web/` portfolio content
- any project/profile notes already in the repo

If a detail is missing, say so plainly. Do not fill the gap with assumptions.

## Inputs

- job offer text or URL
- candidate CV
- project notes / portfolio context
- optional prior conversation memory

## Instructions

### 1) Language

Match the offer language.

- Spanish offer -> Spanish outputs
- English offer -> English outputs
- Keep the copy natural for the target market

### 2) Output types

Generate two separate outputs:

- `Profile adapted to the offer`, presented through the personalized portfolio route when available
- `PDF CV adapted to the offer`

The profile is recruiter-facing and value-oriented. The CV is application-ready and presentation-ready. A standalone `profile.md` is not required unless explicitly requested; do not create one by default.

### 3) JSON generation contract

When writing the profile JSON, keep the fields aligned to the actual role story:

- `welcome`: app intro only; 1 sentence, no greeting, and no overlap with `positioning`.
- `positioning`: introduce Adrián and the portfolio; lead with documented professional experience, not a project pitch.
- `questions`: exactly 3 recruiter-facing prompts in the target language.
- `requirements`: map cleanly to the offer; include required/preferred priority and keep `offer_quote` grounded in the job text.
- `evidence`: cite only repo-backed proof; do not invent employers, titles, clients, metrics, or deployment details.
- Keep `company_name` and `target_role` aligned with the profile slug and job language.

### 4) Profiling rule

The profile should answer:

- Why is this candidate relevant to this role?
- What evidence supports that fit?
- What can this candidate contribute?

Lead with documented professional experience. Use the portfolio or personal projects as supporting evidence, not as the main proof of employment.

### 5) Keep it brief and direct

Prefer short, clear sections and confident language.

- 1-2 short paragraphs for positioning
- 3 bullets for strengths
- 3 bullets for relevant experience
- 3 bullets for key skills
- short CTA with the tailored portfolio link

Do not write long generic intros or long project essays.

### 6) Evidence-first rules

- Reframe existing evidence; do not invent it.
- Distinguish professional work from personal portfolio work.
- If a fact is not documented, do not imply it.
- Do not invent company names, sectors, customers, deployment details, or impact metrics.
- Do not claim a role match or hiring decision without evidence.
- Do not over-weight a personal project just because the terminology matches the role.

### 7) Portfolio links

When the output mentions the portfolio or project context, include the relevant link.

Priority order:

1. Personalized offer profile route, if available
2. General portfolio URL
3. GitHub profile URL

Examples:

- `https://webcv-agent.vercel.app/p/conversational-crm-agentic-runtime`
- `https://webcv-agent.vercel.app/`
- `https://github.com/aaamaroq`

### 8) PDF requirement

The final CV must be a PDF for real application use.

- clean one-page or two-page layout
- concise and professional
- role-specific emphasis
- submission-ready

The PDF can be produced from HTML intermediate content, but the final artifact must be PDF.

## CV template and file naming

- Start from the reusable, tracked template at `templates/cv-template.html`. Preserve its typography, muted green accent, highlighted summary, visible portfolio invitation, and single-column reading order.
- Keep the order: summary, a contextual portfolio CTA directly below the summary, professional experience, clearly labelled personal project(s), core skills, and education.
- Keep the portfolio link in the CTA, not only in the contact links. Use the personalized offer route when available. The project date/title belongs on its own line; put its description on the following line.
- Fill the template placeholders from documented sources only. Duplicate or remove role, skill-group, project, and education entries as needed; do not leave placeholders in the deliverable. Keep professional experience distinct from personal projects.
- Name offer-specific artifacts with the profile slug under `artifacts/<profile-slug>/`: `<profile-slug>-cv.html` and `<profile-slug>-cv.pdf`. For example, `artifacts/industrial-genai-engineer/industrial-genai-engineer-cv.html` and `artifacts/industrial-genai-engineer/industrial-genai-engineer-cv.pdf`.
- Do not save a generic template or source-of-truth content under `artifacts/`; that directory is git-ignored. Keep reusable templates under `templates/`.
- Prefer a readable one-page CV when the evidence fits. Use two pages rather than making type too small or dropping important professional evidence.

### HTML-to-PDF workflow

Use WeasyPrint to render the tailored HTML. It preserves the template's CSS more faithfully than LibreOffice's HTML import/export. Keep WeasyPrint as a local document-generation tool; do not add it to the application's runtime dependencies just for CV output.

```bash
.venv/bin/weasyprint artifacts/<profile-slug>/<profile-slug>-cv.html artifacts/<profile-slug>/<profile-slug>-cv.pdf
```

Before delivery:

- Open the PDF and inspect its visual layout; confirm the single-column flow, section hierarchy, colors, visible CTA, and line breaks.
- Check the page count and paper size with `pdfinfo` and confirm text is extractable with `pdftotext`.
- Confirm the PDF and HTML filenames contain the profile slug, the HTML has no unresolved placeholders, and no standalone `profile.md` was created unless requested.

## Output contract

### Profile

```md
# [Role-targeted title]

## Positioning
[1-2 short paragraphs positioning the candidate for this role]

## Why this fits the role
- [evidence-based strength 1]
- [evidence-based strength 2]
- [evidence-based strength 3]

## Relevant experience
- [relevant role / project / capability]
- [relevant role / project / capability]
- [relevant role / project / capability]

## Key skills
- [skill 1]
- [skill 2]
- [skill 3]

## Portfolio / GitHub
- Portfolio: https://webcv-agent.vercel.app/
- GitHub: https://github.com/aaamaroq
```

### CV PDF

```md
# [Candidate Name]

## Summary
[brief role-specific summary]

## Experience
- [job 1]
- [job 2]

## Projects
- [personal project clearly labelled as such]

## Skills
- [core skills]
- [related stack]

## Portfolio / GitHub
- Portfolio: https://webcv-agent.vercel.app/
- GitHub: https://github.com/aaamaroq
```

## Safe framing

- "Worked with distributed backend systems and data-processing pipelines in professional roles."
- "Applied LLM concepts in a personal project and in backend/data engineering work."
- "This profile is tailored to the opportunity and grounded in the available evidence."

## Disallowed framing

- inventing years, titles, clients, or deployment details
- treating portfolio work as paid professional experience
- claiming production impact without evidence
- leading with a project instead of the documented professional background
- writing generic company-description language with no value proposition

## Final check

Before returning the result, verify:

- it is tailored to the offer
- it is brief and recruiter-friendly
- it clearly separates professional work from personal projects
- the portfolio link is included where relevant
- the CV has a contextual portfolio invitation immediately after its summary, not just an isolated URL
- the CV uses the reusable single-column template and the final PDF was rendered with WeasyPrint and visually inspected
- it does not invent evidence
- it is truthful, specific, and useful

If any answer is no, revise before finalizing.
