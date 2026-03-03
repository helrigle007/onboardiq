import { useState, useRef, useEffect } from 'react';
import type { Citation } from '../types';

interface CitationTooltipProps {
  citation: Citation;
  index: number;
}

export function CitationTooltip({ citation, index }: CitationTooltipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (tooltipRef.current && !tooltipRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  return (
    <span className="relative inline-block" ref={tooltipRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center justify-center w-4 h-4 text-[10px] font-medium text-blue-600 bg-blue-100 rounded-full hover:bg-blue-200 transition-colors cursor-pointer align-super leading-none"
      >
        {index + 1}
      </button>
      {isOpen && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 z-50">
          <div className="bg-white rounded-lg shadow-lg border border-slate-200 p-3">
            <p className="text-sm font-medium text-slate-900 mb-1">{citation.source_title}</p>
            <p className="text-xs text-slate-500 mb-2 truncate">{citation.source_url}</p>
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">
                Relevance: {Math.round(citation.relevance_score * 100)}%
              </span>
              <a
                href={citation.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                View source →
              </a>
            </div>
          </div>
        </div>
      )}
    </span>
  );
}
