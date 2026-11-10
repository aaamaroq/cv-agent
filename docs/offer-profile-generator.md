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
### 2.1) Company-oriented personal positioning

The generated profile and summary must be written as a professional value proposition, not as a generic company description. The text should feel personal and relevant:

- introduce the candidate in terms of who they are and what relevant experience they bring
- explain clearly what they can contribute to this company or role
- connect evidence to the target opportunity without inventing experience
- lead with documented professional backend, data, or distributed-systems experience and then connect it to AI/LLM readiness
- answer the direct HR question: why is this candidate prepared for this role?
- end with a direct and explicit invitation for the recruiter to click the tailored portfolio link or recruiter profile for more context
- present the portfolio invitation as the natural next step, not a generic afterthought

A strong pattern is:

- "I bring experience in backend/data engineering and distributed systems, and I can apply that to ..."
- "I can contribute to ... by combining production-oriented engineering with AI/LLM implementation"
- "This profile was prepared specifically for this opportunity, and I invite you to review the tailored portfolio here: ..."

This should be framed as a recruiter-facing value proposition for the specific offer, not as a neutral summary of the project alone. The recruiter should feel encouraged to click the portfolio link to continue the conversation. MCP, LangGraph, or a standalone personal-project lead should be secondary supporting evidence, not the opening story.

### 2.2) Recruiter-fit questions, not generic background questions

The profile must be optimized to answer hiring questions directly, especially:

- Why is Adrián prepared for this role?
- How does his documented experience map to this offer?
- What can he contribute to this business or team?
- What evidence supports his fit?

The generated question set should not be generic introspection such as “what technologies does he use?” or “what projects has he done?” unless the question is explicitly framed in the context of this offer and the value he can bring. In other words, the profile should be ready to answer HR and recruiter questions about fit, relevance, and contribution.
### 3) Final CV artifact must be a PDF

The final CV is not just a markdown text draft. The output must be a PDF generated for application use.

Requirements:

- final file type: PDF
- clean one-page or two-page professional layout depending on the role
- concise, recruiter-friendly structure
- job-specific emphasis in summary, experience, skills, and projects
- portable and submission-ready

The agent may generate the PDF from an HTML or markdown intermediate representation, but the final output presented to the user must be the PDF artifact.

### 4) Prefer an offer-specific portfolio link

The personalized profile is created in the same generation flow as the offer-tailored output. The agent should therefore produce the recruiter-oriented profile and immediately recommend the corresponding portfolio route for that profile.

In this project, personalized recruiter profiles are exposed at routes such as:

- `https://webcv-agent.vercel.app/p/acme`
- `https://webcv-agent.vercel.app/p/conversational-crm-agentic-runtime`

The agent should recommend the most relevant profile route for the offer, not just the generic portfolio root. If the profile is being generated for the first time and no route exists yet, the system should still point to the personalized profile URL that is generated as part of the same prompt or workflow. The fallback only applies when no tailored profile has been created at all: `https://webcv-agent.vercel.app/`.

### 5) Keep experience evidence-based

- Reframe existing evidence rather than inventing it.
- Do not add years, job titles, technologies, or projects that are not supported by the known sources.
- Distinguish clearly between professional experience and personal portfolio work.
- Calibrate prominence to the breadth and depth of documented evidence. Do not make a project dominate positioning solely because its terminology matches the offer; balance it with broader experience and other relevant projects. Do not imply sustained specialization or production delivery unless the sources establish it.
- If the personal portfolio project is relevant, mention it as supporting evidence, not as the primary proof of professional experience.
- Do not imply manufacturing, chemicals, industrial deployment, or customer production usage unless the sources explicitly say so.
- Do not invent a company name, sector, customer, or domain-specific integration that is not in the evidence.

### 5.1) Critical anti-patterns to avoid

The agent must explicitly avoid the errors seen in earlier drafts:

- neutral project summary that feels disconnected from the company or role
- generic company description with no value proposition for the candidate
- over-weighting a portfolio project above the documented professional background
- presenting portfolio work as if it were paid industry deployment
- leading with MCP, LangGraph, or the personal project when professional backend/data experience is more relevant
- omitting the tailored portfolio link or burying it in a footer
- giving a profile that reads like a project write-up instead of an applicant pitch

### 6) Commercially useful but honest

The text should highlight the strongest alignment with the role without implying direct equivalence where the evidence is weaker.

Good pattern:
- emphasize relevant experience and skills
- connect them to the role requirements
- keep the tone confident and tailored
- show what value the candidate can bring to the company
- invite the recruiter to review the tailored portfolio profile

Bad pattern:
- making unsupported claims
- mixing portfolio work into professional experience as if it were a paid role
- pretending to have a skill or project that is missing from the evidence
- writing only a neutral project summary with no contribution to the company
- failing to mention the relevant personalized portfolio route

### 7) Final self-check before delivering output

Before finalizing the profile or CV, validate all of the following:

- Does the opening clearly say who the candidate is and what value they bring for this company or role?
- Does the text sound like a value proposition, not a generic project description?
- Is the tailored offer-specific portfolio link included near the top or in the final CTA?
- Is the invitation to click the link framed as a direct call to continue exploring the candidate’s relevant work?
- Are the professional and personal project experiences clearly separated?
- Is the portfolio project treated as supporting evidence, not the only proof of fit?
- Has the candidate avoided inventing production deployment, industrial settings, customer impact or company-specific claims not supported by the sources?
- Does the text actively invite the recruiter to review the relevant portfolio, rather than ending without context?

If any answer is "no", revise before returning the result.

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

When the generated output mentions the portfolio, personal project, or repository, the assistant must include the most relevant portfolio URL and the public GitHub profile URL as a normal reference, not as an afterthought.

Priority order:

1. Personalized offer profile URL generated in the same prompt/workflow, for example `https://webcv-agent.vercel.app/p/conversational-crm-agentic-runtime`
2. General portfolio URL: `https://webcv-agent.vercel.app/`
3. GitHub profile: `https://github.com/aaamaroq`

The personalized profile and its portfolio link belong to the same offer-specific generation flow. This is a separate feature from the CV itself: the portfolio links help the recruiter reach the tailored project context, while the CV remains a truthful application document.

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
