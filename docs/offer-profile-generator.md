# Offer-to-profile generator

## Objective

Given a job offer, generate two tailored outputs while staying grounded in the source material of the portfolio and CV:

1. A recruiter-facing profile adapted to the offer.
2. A PDF CV adapted to the same offer and ready to be submitted in a real application process.

The output should be useful for actual job applications, but it must never invent experience, credentials, or capabilities that are not supported by the known sources.

## Source of truth

Use the repository evidence as the canonical base:

- `cv.md`
- `docs/PROJECT.md`
- the public portfolio content in `web/`
- relevant project notes or profile notes already present in the repo

## Inputs

The agent receives:

- a job offer in plain text or a URL to the offer
- the candidate CV
- the project notes or portfolio context
- optional conversation memory from a prior interaction

## Required behavior

### 1) Respect the language of the offer

- If the offer is in Spanish, the generated profile and CV should be in Spanish.
- If the offer is in English, the generated profile and CV should be in English.
- Keep wording natural for the target market and role.

### 2) Generate two outputs, not one

Produce two separate deliverables:

- `Profile adapted to the offer` (recruiter-facing summary / positioning document)
- `PDF CV adapted to the offer` (final application document)

The profile should read like a positioning document for a recruiter or hiring manager. The CV should be a more complete, role-aligned version of the candidate's background, rendered as a polished PDF intended for real applications.

### 3) Final CV artifact must be a PDF

The final CV is not just a markdown text draft. The output must be a PDF generated for application use.

Requirements:

- final file type: PDF
- clean one-page or two-page professional layout depending on the role
- concise, recruiter-friendly structure
- job-specific emphasis in summary, experience, skills, and projects
- portable and submission-ready

The agent may generate the PDF from an HTML or markdown intermediate representation, but the final output presented to the user must be the PDF artifact.

### 3) Keep experience evidence-based

- Reframe existing evidence rather than inventing it.
- Do not add years, job titles, technologies, or projects that are not supported by the known sources.
- Distinguish clearly between professional experience and personal portfolio work.

### 4) Commercially useful but honest

The text should highlight the strongest alignment with the role without implying direct equivalence where the evidence is weaker.

Good pattern:
- emphasize relevant experience and skills
- connect them to the role requirements
- keep the tone confident and tailored

Bad pattern:
- making unsupported claims
- mixing portfolio work into professional experience as if it were a paid role
- pretending to have a skill or project that is missing from the evidence

## Output contract

### Profile document structure

```md
# [Role-Targeted Profile Title]

## Positioning
[1–2 paragraphs positioning the candidate for the role]

## Why this fits the role
- [strength 1]
- [strength 2]
- [strength 3]

## Relevant experience
- [relevant role / project / capability]
- [relevant role / project / capability]

## Key skills
- [skill 1]
- [skill 2]
- [skill 3]

## Portfolio and GitHub
If the portfolio or personal project is mentioned, include:
- Portfolio: https://webcv-agent.vercel.app/
- GitHub: https://github.com/aaamaroq
```

### CV document structure for PDF output

The final application PDF should follow a clean professional layout. The content should still be grounded in the candidate sources, but the final artifact should be presentation-ready.

```md
# [Candidate Name]

## Summary
[tailored summary for the offer]

## Experience
- [job 1 with role-specific emphasis]
- [job 2 with role-specific emphasis]

## Projects
- [portfolio or personal project, clearly labelled]

## Skills
- [core skills]
- [related stack]

## Education
- [academic background]

## Portfolio / GitHub
- Portfolio: https://webcv-agent.vercel.app/
- GitHub: https://github.com/aaamaroq
```

This content is then exported to a PDF for final submission.

## Portfolio and GitHub rule

When the generated output mentions the portfolio, personal project, or repository, the assistant must include the portfolio URL and the public GitHub profile URL as a normal reference, not as an afterthought.

Required references:

- Portfolio: https://webcv-agent.vercel.app/
- GitHub: https://github.com/aaamaroq

### Repetition rule

If the portfolio has already been mentioned once in the same conversation, the agent does not need to repeat the links in every subsequent message unless the user asks explicitly for them again.

This is a separate feature from the CV itself: the portfolio links are helpful context for the assistant and the recruiter-facing output, not evidence that belongs to a paid role.

## Examples of safe framing

- "Built a portfolio chatbot grounded in source documents and reviewed by guardrails."
- "Worked with distributed backend services and data processing in professional settings."
- "Applied AI/LLM concepts in a personal project and in backend/data engineering work."

## Examples of disallowed framing

- "Led a team of AI engineers at X company" when the evidence does not support it.
- "Built production AI products used by customers" without concrete documentation.
- "Merged personal portfolio work and professional experience as if they were the same category."

## Final instruction

The agent should optimize for relevance, clarity, and evidence-based positioning. It must adapt to the target offer, preserve truthfulness, produce a recruiter-facing profile, and generate a final PDF CV that is ready to apply for the role. It should include the portfolio links whenever portfolio/project references appear.
