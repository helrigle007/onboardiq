# ADR-003: Five-Dimension Quality Evaluation Rubric

## Status
Accepted

## Context
OnboardIQ generates onboarding guides that must meet a quality bar before being shown to users. A single overall "quality score" is too coarse — a score of 0.65 does not tell you whether the guide is incomplete, off-topic for the reader's role, or simply poorly organized. Without granular feedback, the only remediation strategy is "regenerate everything and hope it improves."

The evaluation system needs to answer the three questions that different stakeholders care about:

1. **"Did it cover everything?"** — The content team needs assurance that essential topics are not missing from the guide. A Stripe Payments onboarding guide that omits error handling is incomplete regardless of how well-written the rest is.
2. **"Is it for me?"** — The end user needs a guide tailored to their role. A backend engineer integrating Stripe should not receive a guide written for a product manager evaluating Stripe. Role relevance determines whether the guide feels personalized or generic.
3. **"Can I act on it?"** — The end user needs to be able to take concrete steps after reading. A guide full of conceptual overviews without code examples or step-by-step instructions fails to onboard — it merely informs.

Additionally, because OnboardIQ's guides are generated sequentially across multiple sections (see ADR-004), the evaluation must assess whether the guide builds knowledge progressively rather than jumping between difficulty levels randomly.

## Decision
Five evaluation dimensions, each scored on a continuous 0.0-1.0 scale by an LLM-as-judge:

1. **Completeness (0.0-1.0)** — Does the section cover all essential concepts for the topic? Evaluated against expected coverage based on the retrieved source chunks. A score of 1.0 means every key concept from the source material is addressed; 0.0 means the section is effectively empty.

2. **Role Relevance (0.0-1.0)** — Is the content tailored to the reader's specific role and experience level? A 1.0 means the examples, terminology, and depth are perfectly calibrated for the target persona; 0.0 means the content is written for a completely different audience.

3. **Actionability (0.0-1.0)** — Can the reader take concrete action after reading? Evaluated by the presence of code examples, configuration snippets, step-by-step instructions, and explicit "do this" guidance. A 1.0 means the reader can immediately implement; 0.0 means the content is entirely abstract.

4. **Clarity (0.0-1.0)** — Is the section well-organized with logical flow, clear explanations, and appropriate use of headers, lists, and formatting? A 1.0 means the content is immediately comprehensible; 0.0 means it is disorganized or incoherent.

5. **Progressive Complexity (0.0-1.0)** — Does the section build from basics to advanced topics at an appropriate rate? Evaluated in the context of the full guide — early sections should be simpler, later sections should tackle edge cases and advanced patterns. A 1.0 means the complexity curve is smooth and intentional; 0.0 means topics are ordered randomly.

**Quality threshold:** 0.7 overall weighted score (equal weights across all five dimensions). Sections scoring below 0.7 trigger targeted regeneration. Maximum 2 regeneration attempts per section before accepting the best-scoring result.

**Targeted regeneration logic:** The specific dimensions that scored low determine the regeneration strategy. Low completeness triggers re-retrieval with expanded queries. Low role relevance triggers prompt adjustment with stronger role-conditioning. Low actionability triggers explicit instructions to include code examples. Low clarity triggers structural reorganization. Low progressive complexity triggers reordering or scope adjustment.

## Consequences

### Positive
- **Granular, actionable feedback:** Each dimension maps to a specific remediation action. Unlike a single score, a dimension breakdown of {completeness: 0.9, role_relevance: 0.4, actionability: 0.8, clarity: 0.85, progressive_complexity: 0.75} immediately tells you the problem is role targeting, not content quality. The regeneration system can adjust the prompt specifically for role conditioning rather than regenerating blindly.
- **Alignment with real user needs:** The five dimensions were selected based on research into what makes technical documentation effective. Completeness, actionability, and clarity are consistently the top three factors in user satisfaction surveys for developer documentation.
- **Portfolio demonstration value:** The evaluation pipeline is the centerpiece of the portfolio project. Five scored dimensions with visual breakdowns (radar charts via Recharts) demonstrate a sophisticated understanding of LLM output quality assessment, a concern that is top-of-mind for anyone building production AI systems.
- **Structured rubric reduces variance:** Each dimension includes a detailed rubric with score anchors (what does 0.3 look like vs. 0.7 vs. 0.9) and concrete examples. This structured approach reduces the inherent variance of LLM-as-judge evaluation from roughly 15% to approximately 5% between runs.

### Negative
- **Evaluation cost:** Five LLM judge calls per section evaluation costs approximately $0.01 per section. For a 6-section guide, that is $0.06 per evaluation pass. With up to 2 regeneration attempts per section, worst-case evaluation cost is approximately $0.18 per guide. This is non-trivial but acceptable for a quality-focused product.
- **LLM-as-judge inherent limitations:** Despite the structured rubric, LLM judges exhibit approximately 5% score variance between identical runs. This is mitigated but not eliminated by the rubric. For borderline scores near the 0.7 threshold, this variance can cause inconsistent pass/fail decisions.
- **Threshold selection is empirical:** The 0.7 threshold was chosen based on manual review of generated guides. Below 0.6, quality issues are obvious to any reader. Above 0.8, improvements are marginal. The 0.7 threshold catches meaningful issues without triggering excessive regeneration, but it may need tuning as the prompt engineering matures.

### Why Max 2 Regenerations
Diminishing returns set in sharply after 2 regeneration attempts. If a section consistently scores below 0.7 after two regenerations, the root cause is almost always systemic — poor retrieval results, an inadequately defined role profile, or a topic that the source documentation simply does not cover well. A third regeneration attempt with the same inputs is unlikely to produce a meaningfully different result. Accepting the best-scoring attempt and surfacing the low-scoring dimensions to the user is more honest than hiding behind infinite retry loops.
