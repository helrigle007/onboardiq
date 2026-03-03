import { useEffect, useState, useCallback, useRef } from 'react';
import type { GuideSection, SectionEvaluation, GuideResponse, SSEEvent } from '../types';
import { mockSSESequence } from '../mocks/mockGuide';
import { QualityBadge } from './QualityBadge';
import { StreamingText } from './StreamingText';

interface AgentStatus {
  name: string;
  label: string;
  status: 'pending' | 'running' | 'complete';
  duration_ms?: number;
  message?: string;
}

interface GenerationViewProps {
  onComplete: (guide: GuideResponse) => void;
}

const AGENT_LABELS: Record<string, string> = {
  role_profiler: 'Role Profiler',
  content_curator: 'Content Curator',
  guide_generator: 'Guide Generator',
  quality_evaluator: 'Quality Evaluator',
};

export function GenerationView({ onComplete }: GenerationViewProps) {
  const [agents, setAgents] = useState<AgentStatus[]>(
    Object.entries(AGENT_LABELS).map(([name, label]) => ({
      name,
      label,
      status: 'pending',
    }))
  );
  const [sections, setSections] = useState<GuideSection[]>([]);
  const [evaluations, setEvaluations] = useState<SectionEvaluation[]>([]);
  const [regenerationBanner, setRegenerationBanner] = useState<string | null>(null);
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const handleEvent = useCallback(
    (event: SSEEvent) => {
      switch (event.type) {
        case 'agent_start':
          setAgents((prev) =>
            prev.map((a) =>
              a.name === event.agent ? { ...a, status: 'running', message: event.message } : a
            )
          );
          break;
        case 'agent_complete':
          setAgents((prev) =>
            prev.map((a) =>
              a.name === event.agent
                ? { ...a, status: 'complete', duration_ms: event.duration_ms }
                : a
            )
          );
          break;
        case 'section_generated':
          setSections((prev) => [...prev, event.section]);
          break;
        case 'section_evaluated':
          setEvaluations((prev) => [...prev, event.evaluation]);
          break;
        case 'regeneration_triggered':
          setRegenerationBanner(
            `Regenerating sections [${event.sections.join(', ')}] — attempt ${event.attempt} of 2`
          );
          break;
        case 'guide_complete':
          onComplete(event.guide);
          break;
      }
    },
    [onComplete]
  );

  // Run mock SSE sequence
  useEffect(() => {
    let cumulativeDelay = 0;
    const timeouts: ReturnType<typeof setTimeout>[] = [];

    for (const { event, delay } of mockSSESequence) {
      cumulativeDelay += delay;
      const t = setTimeout(() => handleEvent(event), cumulativeDelay);
      timeouts.push(t);
    }

    timeoutsRef.current = timeouts;
    return () => timeouts.forEach(clearTimeout);
  }, [handleEvent]);

  function getEvalForSection(sectionNumber: number): SectionEvaluation | undefined {
    return evaluations.find((e) => e.section_number === sectionNumber);
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-semibold text-slate-900 mb-2">Generating Your Guide</h2>
        <p className="text-slate-500">Our AI pipeline is building your personalized onboarding guide</p>
      </div>

      {/* Pipeline Progress */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 mb-6">
        <div className="flex items-center justify-between">
          {agents.map((agent, i) => (
            <div key={agent.name} className="flex items-center">
              <div className="flex flex-col items-center text-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all ${
                    agent.status === 'complete'
                      ? 'bg-green-100 border-green-500 text-green-600'
                      : agent.status === 'running'
                      ? 'bg-blue-100 border-blue-500 text-blue-600 animate-pulse'
                      : 'bg-slate-50 border-slate-200 text-slate-400'
                  }`}
                >
                  {agent.status === 'complete' ? (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : agent.status === 'running' ? (
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                  ) : (
                    <div className="w-3 h-3 rounded-full bg-slate-300" />
                  )}
                </div>
                <p className="text-xs font-medium text-slate-700 mt-2 max-w-[100px]">{agent.label}</p>
                {agent.status === 'complete' && agent.duration_ms && (
                  <p className="text-[10px] text-green-600 mt-0.5">
                    Done ({(agent.duration_ms / 1000).toFixed(1)}s)
                  </p>
                )}
                {agent.status === 'running' && agent.message && (
                  <p className="text-[10px] text-blue-500 mt-0.5 max-w-[120px] truncate">
                    {agent.message}
                  </p>
                )}
              </div>
              {i < agents.length - 1 && (
                <div
                  className={`w-12 lg:w-20 h-0.5 mx-2 ${
                    agents[i + 1].status !== 'pending' ? 'bg-green-400' : 'bg-slate-200'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Regeneration Banner */}
      {regenerationBanner && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 text-sm text-amber-700 text-center">
          {regenerationBanner}
        </div>
      )}

      {/* Streaming Sections */}
      <div className="space-y-3">
        {sections.map((section) => {
          const sectionEval = getEvalForSection(section.section_number);
          return (
            <div
              key={section.section_number}
              className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 animate-[fadeIn_0.3s_ease-in]"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-slate-100 text-slate-600 text-xs font-semibold">
                    {section.section_number}
                  </span>
                  <h3 className="text-sm font-semibold text-slate-900">{section.title}</h3>
                </div>
                {sectionEval && <QualityBadge score={sectionEval.overall_score} />}
              </div>
              <div className="mt-2 ml-10">
                <StreamingText
                  text={section.summary}
                  speed={30}
                  className="text-sm text-slate-500"
                />
              </div>
              <div className="mt-2 ml-10 flex items-center gap-3 text-xs text-slate-400">
                <span>{section.estimated_time_minutes} min</span>
                <span className="w-1 h-1 rounded-full bg-slate-300" />
                <span>{section.code_examples.length} code examples</span>
                <span className="w-1 h-1 rounded-full bg-slate-300" />
                <span>{section.citations.length} citations</span>
              </div>
            </div>
          );
        })}
      </div>

      {sections.length === 0 && (
        <div className="text-center py-12 text-slate-400 text-sm">
          Sections will appear here as they are generated...
        </div>
      )}
    </div>
  );
}
