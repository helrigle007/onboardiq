import { useState } from 'react';
import Markdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  Clock,
  AlertTriangle,
  Lightbulb,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  ArrowLeft,
} from 'lucide-react';
import type { GuideResponse, GuideSection, DimensionScore } from '../types';
import { EvalRadarChart } from './EvalRadarChart';
import { QualityBadge } from './QualityBadge';
import { CitationTooltip } from './CitationTooltip';

interface GuideViewerProps {
  guide: GuideResponse;
  onBack: () => void;
}

const ROLE_LABELS: Record<string, string> = {
  frontend_developer: 'Frontend Developer',
  backend_developer: 'Backend Developer',
  security_engineer: 'Security Engineer',
  devops_engineer: 'DevOps Engineer',
  product_manager: 'Product Manager',
  team_lead: 'Team Lead',
};

const DIMENSION_LABELS: Record<string, string> = {
  completeness: 'Completeness',
  role_relevance: 'Role Relevance',
  actionability: 'Actionability',
  clarity: 'Clarity',
  progressive_complexity: 'Progressive Complexity',
};

function SectionContent({ section }: { section: GuideSection }) {
  return (
    <div>
      {/* Markdown Content */}
      <div className="prose prose-slate prose-sm max-w-none">
        <Markdown
          components={{
            code({ className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '');
              const codeString = String(children).replace(/\n$/, '');
              if (match) {
                return (
                  <SyntaxHighlighter
                    style={oneDark}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{ borderRadius: '0.75rem', fontSize: '0.8rem' }}
                  >
                    {codeString}
                  </SyntaxHighlighter>
                );
              }
              return (
                <code className="bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded text-xs" {...props}>
                  {children}
                </code>
              );
            },
          }}
        >
          {section.content}
        </Markdown>
      </div>

      {/* Code Examples */}
      {section.code_examples.length > 0 && (
        <div className="mt-6 space-y-4">
          {section.code_examples.map((example, i) => (
            <div key={i} className="rounded-xl overflow-hidden border border-slate-200">
              <div className="bg-slate-800 px-4 py-2 flex items-center justify-between">
                <span className="text-xs text-slate-400 font-mono">{example.language}</span>
              </div>
              <SyntaxHighlighter
                style={oneDark}
                language={example.language === 'bash' ? 'bash' : example.language}
                customStyle={{ margin: 0, borderRadius: 0, fontSize: '0.8rem' }}
              >
                {example.code}
              </SyntaxHighlighter>
              <div className="bg-slate-50 px-4 py-2 border-t border-slate-200">
                <p className="text-xs text-slate-500">{example.description}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Warnings */}
      {section.warnings.length > 0 && (
        <div className="mt-6 space-y-2">
          {section.warnings.map((warning, i) => (
            <div
              key={i}
              className="flex gap-3 rounded-lg bg-amber-50 border border-amber-200 p-3"
            >
              <AlertTriangle size={16} className="text-amber-600 mt-0.5 shrink-0" />
              <p className="text-sm text-amber-800">{warning}</p>
            </div>
          ))}
        </div>
      )}

      {/* Key Takeaways */}
      {section.key_takeaways.length > 0 && (
        <div className="mt-6 rounded-lg bg-blue-50 border border-blue-200 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb size={14} className="text-blue-600" />
            <h4 className="text-sm font-medium text-blue-900">Key Takeaways</h4>
          </div>
          <ul className="space-y-1.5">
            {section.key_takeaways.map((takeaway, i) => (
              <li key={i} className="text-sm text-blue-800 flex gap-2">
                <span className="text-blue-400 mt-0.5">•</span>
                {takeaway}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Citations */}
      {section.citations.length > 0 && (
        <div className="mt-6 flex items-center gap-2">
          <span className="text-xs text-slate-400">Sources:</span>
          {section.citations.map((citation, i) => (
            <CitationTooltip key={i} citation={citation} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

function EvalAccordion({ dimensions, sectionNumber }: { dimensions: DimensionScore[]; sectionNumber: number }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 text-sm hover:bg-slate-50 transition-colors cursor-pointer"
      >
        <span className="font-medium text-slate-700">Section {sectionNumber} Scores</span>
        {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>
      {isOpen && (
        <div className="border-t border-slate-200 p-3 space-y-2">
          {dimensions.map((dim) => (
            <div key={dim.dimension} className="flex items-center justify-between">
              <span className="text-xs text-slate-600">
                {DIMENSION_LABELS[dim.dimension] ?? dim.dimension}
              </span>
              <div className="flex items-center gap-2">
                <div className="w-20 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      dim.score >= 0.8 ? 'bg-green-500' : dim.score >= 0.7 ? 'bg-amber-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${dim.score * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-slate-500 w-8 text-right">
                  {Math.round(dim.score * 100)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function GuideViewer({ guide, onBack }: GuideViewerProps) {
  const [activeSection, setActiveSection] = useState(0);

  const currentSection = guide.sections[activeSection];
  const totalTime = guide.sections.reduce((sum, s) => sum + s.estimated_time_minutes, 0);

  // Aggregate dimensions across all sections for the radar chart
  const aggregatedDimensions: DimensionScore[] = (() => {
    const dimMap = new Map<string, { total: number; count: number; reasoning: string; suggestions: string[] }>();
    for (const sectionEval of guide.evaluation.section_evaluations) {
      for (const dim of sectionEval.dimensions) {
        const existing = dimMap.get(dim.dimension);
        if (existing) {
          existing.total += dim.score;
          existing.count += 1;
        } else {
          dimMap.set(dim.dimension, {
            total: dim.score,
            count: 1,
            reasoning: dim.reasoning,
            suggestions: dim.suggestions,
          });
        }
      }
    }
    return Array.from(dimMap.entries()).map(([dimension, data]) => ({
      dimension,
      score: data.total / data.count,
      reasoning: data.reasoning,
      suggestions: data.suggestions,
    }));
  })();

  const { metadata } = guide;

  return (
    <div className="flex h-[calc(100vh-120px)] overflow-hidden">
      {/* Left sidebar — Section nav */}
      <div className="w-64 shrink-0 border-r border-slate-200 bg-white overflow-y-auto">
        <div className="p-4 border-b border-slate-200">
          <button
            onClick={onBack}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 mb-3 cursor-pointer"
          >
            <ArrowLeft size={12} />
            New Guide
          </button>
          <h2 className="text-sm font-semibold text-slate-900 leading-tight">{guide.title}</h2>
          <span className="inline-block mt-1.5 rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-xs font-medium">
            {ROLE_LABELS[guide.role] ?? guide.role}
          </span>
        </div>

        <nav className="p-2">
          {guide.sections.map((section, i) => {
            const sectionEval = guide.evaluation.section_evaluations.find(
              (e) => e.section_number === section.section_number
            );
            return (
              <button
                key={section.section_number}
                onClick={() => setActiveSection(i)}
                className={`w-full text-left rounded-lg p-2.5 mb-1 transition-colors cursor-pointer ${
                  activeSection === i
                    ? 'bg-blue-50 border border-blue-200'
                    : 'hover:bg-slate-50 border border-transparent'
                }`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-xs font-semibold text-slate-400 mt-0.5">
                    {section.section_number}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-800 leading-tight truncate">
                      {section.title}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      {sectionEval && <QualityBadge score={sectionEval.overall_score} />}
                      <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                        <Clock size={10} />
                        {section.estimated_time_minutes}m
                      </span>
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-200">
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <Clock size={12} />
            <span>Total: ~{totalTime} minutes</span>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto p-8">
          <div className="flex items-center gap-3 mb-1">
            <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-100 text-blue-700 text-sm font-bold">
              {currentSection.section_number}
            </span>
            <h1 className="text-xl font-semibold text-slate-900">{currentSection.title}</h1>
          </div>
          <p className="text-sm text-slate-500 mb-6 ml-11">{currentSection.summary}</p>

          {currentSection.prerequisites.length > 0 && (
            <div className="mb-6 ml-11 flex items-center gap-2 text-xs text-slate-400">
              <span>Prerequisites:</span>
              {currentSection.prerequisites.map((p, i) => (
                <span key={i} className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-500">
                  {p}
                </span>
              ))}
            </div>
          )}

          <div className="ml-11">
            <SectionContent section={currentSection} />
          </div>

          {/* Section navigation */}
          <div className="flex items-center justify-between mt-10 ml-11 pt-6 border-t border-slate-200">
            <button
              onClick={() => setActiveSection((prev) => Math.max(0, prev - 1))}
              disabled={activeSection === 0}
              className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
                activeSection === 0
                  ? 'text-slate-300 cursor-not-allowed'
                  : 'text-slate-600 hover:bg-slate-100 cursor-pointer'
              }`}
            >
              ← Previous
            </button>
            <span className="text-xs text-slate-400">
              {activeSection + 1} of {guide.sections.length}
            </span>
            <button
              onClick={() => setActiveSection((prev) => Math.min(guide.sections.length - 1, prev + 1))}
              disabled={activeSection === guide.sections.length - 1}
              className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
                activeSection === guide.sections.length - 1
                  ? 'text-slate-300 cursor-not-allowed'
                  : 'text-blue-600 hover:bg-blue-50 cursor-pointer'
              }`}
            >
              Next →
            </button>
          </div>
        </div>
      </div>

      {/* Right panel — Evaluation */}
      <div className="w-80 shrink-0 border-l border-slate-200 bg-white overflow-y-auto">
        <div className="p-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Quality Evaluation</h3>

          {/* Radar chart */}
          <div className="bg-slate-50 rounded-xl p-2 mb-4">
            <EvalRadarChart
              dimensions={aggregatedDimensions}
              overallScore={guide.evaluation.overall_score}
            />
          </div>

          {/* Per-section accordion */}
          <div className="space-y-2 mb-6">
            {guide.evaluation.section_evaluations.map((sectionEval) => (
              <EvalAccordion
                key={sectionEval.section_number}
                dimensions={sectionEval.dimensions}
                sectionNumber={sectionEval.section_number}
              />
            ))}
          </div>

          {/* Generation Metadata */}
          <div className="border-t border-slate-200 pt-4">
            <h3 className="text-sm font-semibold text-slate-900 mb-3">Generation Details</h3>
            <dl className="space-y-2">
              <div className="flex justify-between">
                <dt className="text-xs text-slate-500">Model</dt>
                <dd className="text-xs font-mono text-slate-700">{metadata.model}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-xs text-slate-500">Total Tokens</dt>
                <dd className="text-xs font-mono text-slate-700">
                  {metadata.total_tokens_used.toLocaleString()}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-xs text-slate-500">Cost</dt>
                <dd className="text-xs font-mono text-slate-700">
                  ${metadata.total_cost_usd.toFixed(4)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-xs text-slate-500">Generation Time</dt>
                <dd className="text-xs font-mono text-slate-700">
                  {metadata.generation_time_seconds.toFixed(1)}s
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-xs text-slate-500">Retrieval Latency</dt>
                <dd className="text-xs font-mono text-slate-700">{metadata.retrieval_latency_ms}ms</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-xs text-slate-500">Chunks</dt>
                <dd className="text-xs font-mono text-slate-700">
                  {metadata.chunks_retrieved} → {metadata.chunks_after_reranking}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-xs text-slate-500">Regenerations</dt>
                <dd className="text-xs font-mono text-slate-700">{metadata.regeneration_count}</dd>
              </div>
              {metadata.langsmith_trace_url && (
                <div className="pt-2">
                  <a
                    href={metadata.langsmith_trace_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
                  >
                    <ExternalLink size={11} />
                    View LangSmith Trace
                  </a>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
