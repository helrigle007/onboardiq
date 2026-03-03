# Phase 2 — Terminal 4: Frontend Integration

## Overview
Wire the React frontend to the real FastAPI backend. Replace mock data with live API calls and real SSE streaming. Polish the evaluation UI with real scores.

## Pre-flight
```bash
cd ~/onboardiq
git checkout main && git pull
git checkout -b feat/frontend-integration
```

## Task 1: Remove Mock Data, Wire Real API

### Update `frontend/src/App.tsx`
- Remove mock data imports
- Remove setTimeout-based fake pipeline
- Use `useGuideGeneration` hook connected to real `/api/guides/generate` + SSE

### Update `frontend/src/hooks/useGuideGeneration.ts`
- The hook should already be wired to `generateGuide()` and `useSSE()` from Phase 1
- Verify it handles all real SSE event types correctly
- Add error recovery: if SSE disconnects, poll `GET /api/guides/{id}` as fallback
- Add a `retryConnection` function for SSE reconnection

### Update `frontend/src/components/ProductSelector.tsx`
- Fetch products from `GET /api/products/` instead of hardcoding
- Show real doc_count and chunk_count from the API
- Handle loading and error states

## Task 2: Real SSE Streaming in GenerationView

### Update `frontend/src/components/GenerationView.tsx`

The component should now handle real events:

1. **agent_start** → Update pipeline stepper (set agent to "running" with pulse animation)
2. **agent_complete** → Update stepper (set to "complete" with checkmark, show duration)
3. **section_generated** → Append section card to streaming list below the stepper
   - Section fades in with slide-up animation
   - Show section title + summary immediately
   - "View details" expands to full content
4. **section_evaluated** → Add quality badge to the corresponding section card
   - Badge slides in from right
   - Color: green (≥0.8), yellow (≥0.7), red (<0.7)
5. **regeneration_triggered** → Show yellow banner with "Regenerating sections [X, Y]..."
   - Reset affected agent steps to "pending"
   - Pulse the re-generating section cards
6. **guide_complete** → Transition to GuideViewer
   - Brief success animation (checkmark + "Guide Complete!")
   - Auto-navigate after 1.5s, or click "View Guide"
7. **error** → Show error card
   - If recoverable: show "Retry" button
   - If not: show error message and "Start Over" button

Add timing display:
- Running clock showing elapsed time since generation started
- After complete: show total generation time prominently

## Task 3: Enhanced GuideViewer with Real Data

### Update `frontend/src/components/GuideViewer.tsx`

Ensure all data-dependent features work with real API responses:

1. **Section navigation** — populate from `guide.sections`
2. **Markdown rendering** — verify `react-markdown` handles all generated content (headers, code blocks, lists, links, tables)
3. **Code blocks** — syntax highlighting must work for Python, JavaScript, Ruby, curl
4. **Citations** — wire `CitationTooltip` to real citation data
5. **Warnings** — render in yellow callout boxes with ⚠️ icon
6. **Key takeaways** — render in blue-tinted box

### Update `frontend/src/components/EvalRadarChart.tsx`
- Accept real evaluation data from `guide.evaluation.section_evaluations`
- Support switching between per-section view and overall average view
- Add "Overall" tab that averages across all sections
- Add section tabs (Section 1, Section 2, ...) that show individual radar charts

### New: `frontend/src/components/MetadataPanel.tsx`
Extract the generation metadata display into its own component:

```tsx
interface Props {
  metadata: GenerationMetadata;
}
```

Display:
- Model name (with version)
- Total tokens used (formatted with commas)
- Total cost (formatted as $X.XX)
- Generation time (formatted as Xs or X.Xmin)
- Retrieval latency (formatted as Xms)
- Chunks: "X retrieved → Y after reranking"
- Regeneration count ("0 regenerations" or "2 regenerations")
- LangSmith trace link (if available, clickable external link)

Style as a compact card with icon labels (lucide icons: Cpu, DollarSign, Clock, Database, RefreshCw, ExternalLink).

## Task 4: Guide History Page

### New: `frontend/src/components/GuideHistory.tsx`

Add a simple history view accessible from the header:

- Fetch from `GET /api/guides/`
- Display as a table/list with columns: Title, Role, Product, Score, Date, Actions
- Score shows quality badge
- Click a row → navigate to GuideViewer for that guide
- "New Guide" button → back to ProductSelector

Add a simple tab/nav system to App.tsx:
- "New Guide" tab (default)
- "History" tab

## Task 5: Loading & Error States

Create polished loading and error UI across all components:

### New: `frontend/src/components/LoadingSpinner.tsx`
Simple branded spinner for API loading states.

### New: `frontend/src/components/ErrorCard.tsx`
```tsx
interface Props {
  title: string;
  message: string;
  onRetry?: () => void;
  onBack?: () => void;
}
```
Card with error icon, message, and action buttons.

### Apply throughout:
- ProductSelector: loading skeleton while fetching products
- GenerationView: error state if pipeline fails
- GuideViewer: loading skeleton while fetching guide
- GuideHistory: empty state if no guides yet

## Task 6: Polish & Animations

Add subtle animations that make the app feel alive:

1. **Page transitions** — fade in/out when switching between pages (150ms)
2. **Section stream-in** — sections in GenerationView slide up and fade in staggered (each 100ms after previous)
3. **Quality badge appear** — badges scale in from 0 (spring animation via CSS)
4. **Radar chart** — animated drawing on mount (recharts supports `isAnimationActive`)
5. **Pipeline stepper** — running state has subtle pulse glow
6. **Success state** — brief confetti or checkmark animation on guide_complete

Use CSS transitions/animations (no additional library needed). Keep animations subtle and professional — not playful.

## Completion Criteria
- [ ] Full flow works with real backend: select product → configure role → generate → view guide
- [ ] SSE streaming shows real-time pipeline progress
- [ ] All 7 SSE event types handled correctly
- [ ] Evaluation radar chart displays real 5-dimension scores
- [ ] Guide sections render with proper markdown, code highlighting, citations
- [ ] Guide history page works
- [ ] Loading and error states throughout
- [ ] Animations are subtle and professional
- [ ] No console errors
- [ ] Responsive at 1280px+ and 1024px

## Final Steps
```bash
git add -A
git commit -m "feat: frontend integration with real API and SSE streaming

- Real API calls replacing mock data
- Live SSE streaming with all event types
- Evaluation radar chart with per-section switching
- Generation metadata panel
- Guide history page
- Loading skeletons and error states
- Subtle animations (page transitions, stream-in, badge appear)
- Markdown rendering with syntax highlighting"
```
