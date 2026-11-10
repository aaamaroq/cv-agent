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

- `Profile adapted to the offer`
- `PDF CV adapted to the offer`

The profile is recruiter-facing and value-oriented. The CV is application-ready and presentation-ready.

### 3) Profiling rule

The profile should answer:

- Why is this candidate relevant to this role?
- What evidence supports that fit?
- What can this candidate contribute?

Lead with documented professional experience. Use the portfolio or personal projects as supporting evidence, not as the main proof of employment.

### 4) Keep it brief and direct

Prefer short, clear sections and confident language.

- 1-2 short paragraphs for positioning
- 3 bullets for strengths
- 3 bullets for relevant experience
- 3 bullets for key skills
- short CTA with the tailored portfolio link

Do not write long generic intros or long project essays.

### 5) Evidence-first rules

- Reframe existing evidence; do not invent it.
- Distinguish professional work from personal portfolio work.
- If a fact is not documented, do not imply it.
- Do not invent company names, sectors, customers, deployment details, or impact metrics.
- Do not claim a role match or hiring decision without evidence.
- Do not over-weight a personal project just because the terminology matches the role.

### 6) Portfolio links

When the output mentions the portfolio or project context, include the relevant link.

Priority order:

1. Personalized offer profile route, if available
2. General portfolio URL
3. GitHub profile URL

Examples:

- `https://webcv-agent.vercel.app/p/conversational-crm-agentic-runtime`
- `https://webcv-agent.vercel.app/`
- `https://github.com/aaamaroq`

### 7) PDF requirement

The final CV must be a PDF for real application use.

- clean one-page or two-page layout
- concise and professional
- role-specific emphasis
- submission-ready

The PDF can be produced from HTML/Markdown intermediate content, but the final artifact must be PDF.

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
- it does not invent evidence
- it is truthful, specific, and useful

If any answer is no, revise before finalizing.
