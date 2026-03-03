# Phase 1 — Terminal 4: React Frontend

## Overview
You are building the complete React frontend for OnboardIQ using Vite, TypeScript, and Tailwind CSS. The frontend connects to the FastAPI backend via REST + SSE. Build ALL components with mock data first — real API integration happens in Phase 2.

## Pre-flight
```bash
cd ~/onboardiq
git checkout infra/scaffolding   # wait for T1 to finish
git checkout -b feat/frontend
```

## Task 1: Scaffold React App

```bash
cd ~/onboardiq/frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install recharts lucide-react react-markdown react-syntax-highlighter
npm install -D @types/react-syntax-highlighter
```

### Configure Tailwind (Vite plugin approach)

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

```css
/* src/index.css */
@import "tailwindcss";
```

## Task 2: TypeScript Types

### File: `frontend/src/types/index.ts`

Mirror the backend Pydantic schemas exactly:

```typescript
// Enums
export type SupportedProduct = 'stripe' | 'twilio' | 'sendgrid';
export type UserRole = 
  | 'frontend_developer'
  | 'backend_developer' 
  | 'security_engineer'
  | 'devops_engineer'
  | 'product_manager'
  | 'team_lead';
export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced';
export type GuideStatus = 'pending' | 'generating' | 'evaluating' | 'regenerating' | 'complete' | 'failed';

// Request
export interface GuideRequest {
  product: SupportedProduct;
  role: UserRole;
  experience_level: ExperienceLevel;
  focus_areas: string[];
  tech_stack: string[];
}

// Guide structures
export interface CodeExample {
  language: string;
  code: string;
  description: string;
}

export interface Citation {
  source_url: string;
  source_title: string;
  chunk_id: string;
  relevance_score: number;
}

export interface GuideSection {
  section_number: number;
  title: string;
  summary: string;
  content: string;
  key_takeaways: string[];
  code_examples: CodeExample[];
  warnings: string[];
  citations: Citation[];
  estimated_time_minutes: number;
  prerequisites: string[];
}

// Evaluation
export interface DimensionScore {
  dimension: string;
  score: number;
  reasoning: string;
  suggestions: string[];
}

export interface SectionEvaluation {
  section_number: number;
  overall_score: number;
  dimensions: DimensionScore[];
  pass_threshold: boolean;
  needs_regeneration: boolean;
}

export interface GenerationMetadata {
  model: string;
  total_tokens_used: number;
  total_cost_usd: number;
  generation_time_seconds: number;
  retrieval_latency_ms: number;
  chunks_retrieved: number;
  chunks_after_reranking: number;
  regeneration_count: number;
  langsmith_trace_url: string | null;
}

export interface GuideEvaluation {
  guide_id: string;
  overall_score: number;
  section_evaluations: SectionEvaluation[];
  generation_metadata: GenerationMetadata;
}

export interface GuideResponse {
  id: string;
  product: SupportedProduct;
  role: UserRole;
  title: string;
  description: string;
  sections: GuideSection[];
  evaluation: GuideEvaluation;
  metadata: GenerationMetadata;
  created_at: string;
}

// SSE Events
export type SSEEvent =
  | { type: 'agent_start'; agent: string; message: string }
  | { type: 'agent_complete'; agent: string; duration_ms: number }
  | { type: 'section_generated'; section: GuideSection; index: number }
  | { type: 'section_evaluated'; evaluation: SectionEvaluation; index: number }
  | { type: 'regeneration_triggered'; sections: number[]; attempt: number }
  | { type: 'guide_complete'; guide: GuideResponse }
  | { type: 'error'; message: string; recoverable: boolean }
  | { type: 'keepalive' };

// Product info
export interface ProductInfo {
  id: string;
  name: string;
  description: string;
  doc_count: number;
  chunk_count: number;
  available_roles: UserRole[];
}

// Role display info (for UI)
export interface RoleDisplayInfo {
  role: UserRole;
  label: string;
  icon: string;  // lucide icon name
  description: string;
}
```

## Task 3: API Client + SSE Hook

### File: `frontend/src/api/client.ts`

```typescript
const API_BASE = '/api';

export async function generateGuide(request: GuideRequest): Promise<{ guide_id: string }> {
  const res = await fetch(`${API_BASE}/guides/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error(`Failed to generate: ${res.statusText}`);
  return res.json();
}

export async function getGuide(guideId: string): Promise<GuideResponse> {
  const res = await fetch(`${API_BASE}/guides/${guideId}`);
  if (!res.ok) throw new Error(`Failed to fetch guide: ${res.statusText}`);
  return res.json();
}

export async function listProducts(): Promise<{ products: ProductInfo[] }> {
  const res = await fetch(`${API_BASE}/products/`);
  if (!res.ok) throw new Error(`Failed to fetch products: ${res.statusText}`);
  return res.json();
}
```

### File: `frontend/src/hooks/useSSE.ts`

```typescript
import { useState, useEffect, useCallback, useRef } from 'react';
import { SSEEvent } from '../types';

interface UseSSEOptions {
  guideId: string | null;
  onEvent?: (event: SSEEvent) => void;
}

interface UseSSEReturn {
  isConnected: boolean;
  events: SSEEvent[];
  error: string | null;
}

export function useSSE({ guideId, onEvent }: UseSSEOptions): UseSSEReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!guideId) return;

    const es = new EventSource(`/api/guides/${guideId}/stream`);
    eventSourceRef.current = es;

    es.onopen = () => setIsConnected(true);

    es.onmessage = (event) => {
      try {
        const parsed: SSEEvent = JSON.parse(event.data);
        if (parsed.type === 'keepalive') return;

        setEvents((prev) => [...prev, parsed]);
        onEvent?.(parsed);

        if (parsed.type === 'guide_complete' || parsed.type === 'error') {
          es.close();
          setIsConnected(false);
        }
      } catch (e) {
        console.error('SSE parse error:', e);
      }
    };

    es.onerror = () => {
      setError('Connection lost');
      setIsConnected(false);
      es.close();
    };

    return () => {
      es.close();
      setIsConnected(false);
    };
  }, [guideId]);

  return { isConnected, events, error };
}
```

### File: `frontend/src/hooks/useGuideGeneration.ts`

```typescript
import { useState, useCallback } from 'react';
import { GuideRequest, GuideResponse, GuideSection, SectionEvaluation, SSEEvent } from '../types';
import { generateGuide } from '../api/client';
import { useSSE } from './useSSE';

interface AgentStatus {
  name: string;
  status: 'pending' | 'running' | 'complete';
  duration_ms?: number;
}

interface GenerationState {
  guideId: string | null;
  status: 'idle' | 'generating' | 'complete' | 'error';
  agents: AgentStatus[];
  sections: GuideSection[];
  evaluations: SectionEvaluation[];
  regenerationAttempt: number;
  completedGuide: GuideResponse | null;
  error: string | null;
}

const AGENT_NAMES = ['role_profiler', 'content_curator', 'guide_generator', 'quality_evaluator'];

export function useGuideGeneration() {
  const [state, setState] = useState<GenerationState>({
    guideId: null,
    status: 'idle',
    agents: AGENT_NAMES.map((name) => ({ name, status: 'pending' })),
    sections: [],
    evaluations: [],
    regenerationAttempt: 0,
    completedGuide: null,
    error: null,
  });

  const handleSSEEvent = useCallback((event: SSEEvent) => {
    setState((prev) => {
      switch (event.type) {
        case 'agent_start':
          return {
            ...prev,
            agents: prev.agents.map((a) =>
              a.name === event.agent ? { ...a, status: 'running' } : a
            ),
          };
        case 'agent_complete':
          return {
            ...prev,
            agents: prev.agents.map((a) =>
              a.name === event.agent
                ? { ...a, status: 'complete', duration_ms: event.duration_ms }
                : a
            ),
          };
        case 'section_generated':
          return {
            ...prev,
            sections: [...prev.sections, event.section],
          };
        case 'section_evaluated':
          return {
            ...prev,
            evaluations: [...prev.evaluations, event.evaluation],
          };
        case 'regeneration_triggered':
          return {
            ...prev,
            regenerationAttempt: event.attempt,
            // Reset affected agents back to pending
            agents: prev.agents.map((a) =>
              ['content_curator', 'guide_generator', 'quality_evaluator'].includes(a.name)
                ? { ...a, status: 'pending' }
                : a
            ),
          };
        case 'guide_complete':
          return {
            ...prev,
            status: 'complete',
            completedGuide: event.guide,
          };
        case 'error':
          return {
            ...prev,
            status: 'error',
            error: event.message,
          };
        default:
          return prev;
      }
    });
  }, []);

  const { isConnected } = useSSE({
    guideId: state.guideId,
    onEvent: handleSSEEvent,
  });

  const startGeneration = useCallback(async (request: GuideRequest) => {
    setState({
      guideId: null,
      status: 'generating',
      agents: AGENT_NAMES.map((name) => ({ name, status: 'pending' })),
      sections: [],
      evaluations: [],
      regenerationAttempt: 0,
      completedGuide: null,
      error: null,
    });

    try {
      const { guide_id } = await generateGuide(request);
      setState((prev) => ({ ...prev, guideId: guide_id }));
    } catch (e) {
      setState((prev) => ({
        ...prev,
        status: 'error',
        error: e instanceof Error ? e.message : 'Failed to start generation',
      }));
    }
  }, []);

  const reset = useCallback(() => {
    setState({
      guideId: null,
      status: 'idle',
      agents: AGENT_NAMES.map((name) => ({ name, status: 'pending' })),
      sections: [],
      evaluations: [],
      regenerationAttempt: 0,
      completedGuide: null,
      error: null,
    });
  }, []);

  return {
    ...state,
    isConnected,
    startGeneration,
    reset,
  };
}
```

## Task 4: Mock Data

### File: `frontend/src/mocks/mockGuide.ts`

Create a realistic mock `GuideResponse` for Stripe + Security Engineer with 6 sections. Each section should have realistic content (a few paragraphs of markdown), 2-3 code examples, 1-2 warnings, citations, and evaluation scores. This mock data drives the entire UI development before the backend pipeline is real.

Make it convincing — someone looking at the UI should think it's real output. Include:
- Section 1: "Platform Overview & Security Architecture" (score: 0.92)
- Section 2: "API Authentication & Key Management" (score: 0.88)
- Section 3: "Webhook Security & Signature Verification" (score: 0.95)
- Section 4: "PCI Compliance & Data Handling" (score: 0.78)
- Section 5: "Fraud Prevention & Risk Management" (score: 0.85)
- Section 6: "Monitoring, Logging & Incident Response" (score: 0.90)

Overall score: 0.88. Include realistic GenerationMetadata (tokens, cost, latency).

## Task 5: Components

### App Layout & Routing

Use a simple state-based routing (no react-router needed for MVP):
- State: `'select'` → `'configure'` → `'generating'` → `'viewing'`

### File: `frontend/src/App.tsx`

Main app shell with state-driven page rendering. Clean layout with:
- Header bar with OnboardIQ logo text + tagline
- Main content area (switches between pages)
- Subtle footer with "Powered by Claude + LangChain"

### File: `frontend/src/components/ProductSelector.tsx`

Grid of product cards. For MVP, only Stripe is active; Twilio and SendGrid are shown as "Coming Soon" with reduced opacity. Each card shows:
- Product logo/icon (use lucide icons: CreditCard for Stripe, Phone for Twilio, Mail for SendGrid)
- Product name
- Brief description
- "Available" badge or "Coming Soon" badge

Clicking Stripe advances to the role configurator.

### File: `frontend/src/components/RoleConfigurator.tsx`

Two-column layout:

**Left column — Role Selection:**
Grid of 6 role cards (2x3). Each card:
- Icon (lucide: Code for Frontend Dev, Server for Backend Dev, Shield for Security Eng, Cloud for DevOps, BarChart3 for PM, Users for Team Lead)
- Role label (human-readable)
- 1-line description of what the guide focuses on for this role
- Selected state: blue border + checkmark

**Right column — Configuration:**
- Experience Level: 3-option segmented control (Beginner / Intermediate / Advanced)
- Focus Areas: Tag-style input where users can type and press Enter to add tags. Show 4-5 suggested tags based on selected role (e.g., for Security Engineer: "API security", "PCI compliance", "audit logging", "fraud prevention", "encryption")
- Tech Stack: Same tag input, suggested: "Python", "Node.js", "Go", "Ruby", "Java"
- "Generate Guide" button (prominent, full-width at bottom)

### File: `frontend/src/components/GenerationView.tsx`

Real-time pipeline progress. This is the "wow" screen. Layout:

**Top: Pipeline Progress**
Horizontal stepper showing the 4 agents:
```
[●] Role Profiler → [◐] Content Curator → [○] Guide Generator → [○] Quality Evaluator
    ✓ Done (1.2s)     Retrieving docs...
```

Each step shows:
- Filled circle (complete), half-filled (running), empty (pending)
- Agent name
- Status text or duration
- Subtle animation (pulse) when running

**Bottom: Streaming Sections**
As sections arrive via SSE, they appear in a stack below the progress bar. Each section card shows:
- Section number + title
- Summary text (fades in with animation)
- Quality badge (appears after evaluation): green ≥0.8, yellow ≥0.7, red <0.7
- "View full section →" link

If regeneration triggers, show a yellow banner: "Regenerating sections [3, 5] — attempt 2 of 2"

### File: `frontend/src/components/GuideViewer.tsx`

The main guide reading experience. Three-panel layout:

**Left sidebar (narrow, ~250px):**
- Guide title + role badge
- Section navigation list
- Each section shows: number, title, quality score badge, time estimate
- Clicking scrolls to / highlights that section
- Total time estimate at bottom

**Main content (wide):**
- Current section with full markdown content
- Render markdown with `react-markdown`
- Code blocks with syntax highlighting via `react-syntax-highlighter` (use oneDark theme)
- Warning callouts: yellow background with ⚠️ icon
- Key takeaways: bulleted list in a blue-tinted box
- Citations: small superscript numbers that show a tooltip on hover with source info

**Right panel (~300px):**
- Evaluation radar chart (EvalRadarChart component)
- Per-section score breakdown (expandable accordion)
- Generation metadata card:
  - Model used
  - Total tokens / cost
  - Generation time
  - Chunks retrieved → after reranking
  - Regeneration count
  - LangSmith trace link (if available)

### File: `frontend/src/components/EvalRadarChart.tsx`

Recharts RadarChart showing the 5 evaluation dimensions:
- Completeness, Role Relevance, Actionability, Clarity, Progressive Complexity
- Color-coded by overall score (green ≥0.8, yellow ≥0.7, red <0.7)
- Large score number overlay (e.g., "88%")
- Tooltip on hover showing exact scores
- Smooth animation on mount

### File: `frontend/src/components/QualityBadge.tsx`

Small pill/badge component:
- Score ≥ 0.8: Green background, "Excellent" or score %
- Score ≥ 0.7: Yellow background, "Good" or score %
- Score < 0.7: Red background, "Needs Work" or score %

### File: `frontend/src/components/CitationTooltip.tsx`

Hover/click tooltip for inline citations:
- Shows source title, URL, relevance score
- Small card that appears above the citation marker
- Click opens source URL in new tab

### File: `frontend/src/components/StreamingText.tsx`

Text that appears character-by-character (or word-by-word) for that streaming effect during generation. Used in the GenerationView for section summaries as they arrive.

## Task 6: Design System & Theming

Use a professional, clean aesthetic. NOT generic chatbot vibes. Think: Vercel dashboard meets Notion.

**Color palette:**
- Background: `#fafafa` (light) 
- Surface: `#ffffff` with subtle shadow
- Primary: `#2563eb` (blue-600)
- Success: `#16a34a` (green-600)
- Warning: `#d97706` (amber-600)
- Danger: `#dc2626` (red-600)
- Text primary: `#0f172a` (slate-900)
- Text secondary: `#64748b` (slate-500)
- Border: `#e2e8f0` (slate-200)

**Typography:**
- Font: system-ui / Inter (via Tailwind defaults)
- Headings: font-semibold
- Body: font-normal, text-sm/text-base

**Component patterns:**
- Cards: rounded-xl, bg-white, shadow-sm, border border-slate-200
- Buttons: rounded-lg, font-medium, transition-colors
- Badges: rounded-full, text-xs, font-medium, px-2.5 py-0.5
- Inputs: rounded-lg, border border-slate-300, focus:ring-2 focus:ring-blue-500

## Task 7: Wire Up Mock Data Flow

The full app should work end-to-end with mock data:
1. ProductSelector → click Stripe → RoleConfigurator
2. RoleConfigurator → select Security Engineer, set experience → click Generate
3. GenerationView → shows animated pipeline progress (fake 1s delays per agent)
4. After "completion" → auto-transition to GuideViewer with mock guide data
5. GuideViewer → navigate sections, see eval chart, explore citations

For the mock flow, use `setTimeout` to simulate the pipeline stages. When real SSE is connected in Phase 2, just swap out the mock for real events.

## Completion Criteria
- [ ] `npm run dev` starts on port 3000
- [ ] Full user flow works with mock data: select → configure → generate → view
- [ ] All components render correctly with realistic content
- [ ] Radar chart displays 5 dimensions with correct colors
- [ ] Code blocks have syntax highlighting
- [ ] SSE hook is implemented and ready for real events
- [ ] TypeScript types match backend Pydantic schemas exactly
- [ ] Responsive layout works at common breakpoints (1280px+, 1024px, 768px)
- [ ] No TypeScript errors (`npm run type-check` passes)
- [ ] UI looks polished and professional — not a tutorial project

## Final Steps
```bash
git add -A
git commit -m "feat: complete React frontend with all components and mock data flow

- Vite + React + TypeScript + Tailwind CSS setup
- Full type system mirroring backend schemas
- SSE hook and guide generation state management
- ProductSelector, RoleConfigurator, GenerationView, GuideViewer
- Evaluation radar chart (recharts)
- Code syntax highlighting, citation tooltips
- Mock data for end-to-end UI development
- Professional design system"
```
