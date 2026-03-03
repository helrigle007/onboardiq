# ADR-004: Sequential Section Generation

## Status
Accepted

## Context
OnboardIQ generates 6-section onboarding guides covering a progression from introductory concepts through advanced patterns. Each section could theoretically be generated in parallel across multiple LLM calls for faster total latency — six parallel calls would reduce wall-clock time from roughly 20-30 seconds to 8-10 seconds.

However, the evaluation dimension "progressive_complexity" (see ADR-003) requires each section to build on previous ones. A "Getting Started" section must be simpler and more foundational than an "Advanced Patterns" section that follows it. If sections are generated in parallel, each one is written in isolation without knowledge of what the others cover. This leads to three specific problems:

1. **Duplicate content:** Without knowing what Section 2 covered, Section 3 may re-explain the same concepts, wasting the reader's time and inflating the guide length.
2. **Broken cross-references:** A section cannot reference "the API key you created in Section 2" if it does not know what Section 2 actually contains.
3. **Inconsistent complexity curve:** Parallel sections cannot coordinate their difficulty levels. Section 4 might accidentally be simpler than Section 2, violating the progressive complexity expectation.

## Decision
Generate guide sections sequentially, not in parallel. Each section's generation prompt receives the full text of all previously generated sections as context. This enables the LLM to:

- Build on concepts already introduced, rather than re-explaining them
- Reference specific examples, code snippets, or terminology from earlier sections
- Calibrate its complexity level relative to what came before
- Avoid repeating content that was already covered thoroughly

The sequential pipeline is implemented as a LangGraph state machine where each section generation is a node. The state carries an accumulating list of completed sections. The guide generator agent receives this list as part of its prompt context, with explicit instructions to build on prior content and increase complexity progressively.

SSE (Server-Sent Events) streaming is used to deliver each completed section to the frontend immediately upon generation. The frontend renders sections as they arrive, creating a progressive disclosure experience.

## Consequences

### Positive
- **Natural progressive complexity:** Section 3 knows exactly what Sections 1 and 2 covered. It can introduce more advanced concepts, use terminology that was defined earlier, and build on code examples that were already established. This produces a coherent learning arc rather than six disconnected essays.
- **Cross-references work naturally:** The generator can write "Building on the basic charge creation from Section 2, let's now handle disputes..." because it has the full text of Section 2 in its context window. This creates a cohesive guide that reads as a single authored document.
- **No duplicate content:** Each section's prompt explicitly instructs the LLM to skip topics already covered in previous sections. With the full prior text available, the model can reliably avoid repetition.
- **SSE streaming mitigates perceived latency:** Users see the first section appear within approximately 4 seconds of starting generation. Subsequent sections stream in every 3-5 seconds. The progressive reveal creates engagement and gives users content to read while later sections generate. The perceived experience is significantly faster than the total wall-clock time.

### Negative
- **Higher total latency:** Sequential generation takes approximately 20-30 seconds for a full 6-section guide (3-5 seconds per section). Parallel generation would reduce this to roughly 8-10 seconds. This is a 2-3x increase in total wall-clock time.
- **Cascading failure risk:** A failure in Section 3 blocks Sections 4, 5, and 6. If the LLM call for one section times out or returns an error, all subsequent sections are delayed. This is mitigated with per-section retry logic (up to 2 retries per section) and a circuit-breaker that returns a partial guide if a section fails after retries.
- **Growing context window:** By Section 6, the prompt includes the full text of Sections 1-5 plus the retrieval context and system instructions. This can push toward context window limits with verbose guides. This is managed by summarizing earlier sections if the total context exceeds 80% of the model's window.

### Mitigation
SSE streaming is the primary mitigation for the latency trade-off. The frontend emits `agent_start` and `section_generated` events through the pipeline, keeping users informed of progress. Each section appears in the UI as soon as it is generated, with a progress indicator showing which section is currently being written. Users can begin reading Section 1 while Section 2 generates, and by the time they finish reading the first few sections, the full guide is typically complete. The real-time progress feedback transforms a 25-second wait into an engaging, progressive experience.
