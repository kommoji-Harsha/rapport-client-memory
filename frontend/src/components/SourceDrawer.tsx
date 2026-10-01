import React from 'react';
import { X, Calendar, FileText, Tag, Award } from 'lucide-react';
import { RecalledMemory } from '../types/api';

interface SourceDrawerProps {
  memory: RecalledMemory | null;
  isOpen: boolean;
  onClose: () => void;
}

export const SourceDrawer: React.FC<SourceDrawerProps> = ({
  memory,
  isOpen,
  onClose,
}) => {
  if (!isOpen || !memory) return null;

  const scoreList = [
    { label: 'Final Score', value: memory.scores?.final },
    { label: 'Reranker', value: memory.scores?.reranker },
    { label: 'Semantic', value: memory.scores?.semantic },
    { label: 'Keyword', value: memory.scores?.keyword },
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-xs flex justify-end transition-opacity">
      <div className="w-full max-w-md bg-white dark:bg-slate-900 h-full shadow-2xl border-l border-slate-200 dark:border-slate-800 flex flex-col transform transition-transform duration-200 ease-out">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-950">
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-brand-100 text-brand-700 dark:bg-brand-950 dark:text-brand-300 uppercase">
              {memory.type}
            </span>
            <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
              {memory.id}
            </span>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Recalled Text
            </h3>
            <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-slate-700/80 text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-sans whitespace-pre-wrap">
              {memory.text}
            </div>
          </div>

          {memory.context && (
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5" /> Context
              </span>
              <p className="text-xs text-slate-600 dark:text-slate-300 bg-slate-100/70 dark:bg-slate-800/40 p-2.5 rounded border border-slate-200/60 dark:border-slate-700/50">
                {memory.context}
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 space-y-1">
              <span className="text-slate-500 dark:text-slate-400 font-medium flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" /> Date / Occurred
              </span>
              <p className="font-mono text-slate-800 dark:text-slate-200">
                {memory.occurred_start || memory.mentioned_at || 'Unknown'}
              </p>
            </div>

            <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 space-y-1">
              <span className="text-slate-500 dark:text-slate-400 font-medium flex items-center gap-1">
                <Tag className="w-3.5 h-3.5" /> Document ID
              </span>
              <p className="font-mono text-slate-800 dark:text-slate-200 truncate">
                {memory.document_id || 'N/A'}
              </p>
            </div>
          </div>

          {memory.tags && memory.tags.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Tags
              </span>
              <div className="flex flex-wrap gap-1.5">
                {memory.tags.map((tag, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 rounded text-xs font-mono bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Award className="w-3.5 h-3.5 text-amber-500" /> Hindsight Recall Scores
            </span>

            <div className="grid grid-cols-2 gap-2">
              {scoreList.map((sc) => (
                <div
                  key={sc.label}
                  className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 flex items-center justify-between"
                >
                  <span className="text-xs text-slate-500 dark:text-slate-400">{sc.label}:</span>
                  <span className="font-mono text-xs font-semibold text-slate-900 dark:text-slate-100">
                    {sc.value !== null && sc.value !== undefined ? sc.value.toFixed(3) : '—'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
