import { useState, useCallback } from 'react';
import type { GuideRequest, GuideResponse, GuideSection, SectionEvaluation, SSEEvent } from '../types';
import { generateGuide } from '../api/client';
import { useSSE } from './useSSE';

export interface AgentStatus {
  name: string;
  status: 'pending' | 'running' | 'complete';
  duration_ms?: number;
}

export interface GenerationState {
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
              a.name === event.agent ? { ...a, status: 'running' as const } : a
            ),
          };
        case 'agent_complete':
          return {
            ...prev,
            agents: prev.agents.map((a) =>
              a.name === event.agent
                ? { ...a, status: 'complete' as const, duration_ms: event.duration_ms }
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
            agents: prev.agents.map((a) =>
              ['content_curator', 'guide_generator', 'quality_evaluator'].includes(a.name)
                ? { ...a, status: 'pending' as const }
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
