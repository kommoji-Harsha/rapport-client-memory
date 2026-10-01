import React from 'react';
import { ShieldCheck, AlertTriangle } from 'lucide-react';
import { Client, RecalledMemory } from '../types/api';

interface CrossClientSanityBadgeProps {
  activeClient: Client | null;
  recalledMemories: RecalledMemory[];
}

export const CrossClientSanityBadge: React.FC<CrossClientSanityBadgeProps> = ({
  activeClient,
  recalledMemories,
}) => {
  if (!activeClient) return null;

  const activeTag = `client:${activeClient.id}`;
  let isIsolated = true;
  const tagBreakdown: { memId: string; tags: string[]; isMatch: boolean }[] = [];

  for (const mem of recalledMemories) {
    const hasActiveTag = mem.tags.includes(activeTag);
    const hasOtherClientTags = mem.tags.some(
      (t) => t.startsWith('client:') && t !== activeTag
    );

    if (!hasActiveTag || hasOtherClientTags) {
      isIsolated = false;
    }

    tagBreakdown.push({
      memId: mem.id,
      tags: mem.tags,
      isMatch: hasActiveTag && !hasOtherClientTags,
    });
  }

  return (
    <div className="bg-slate-900 text-slate-100 rounded-xl p-3 border border-slate-800 text-xs font-mono space-y-2 shadow-lg">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-1.5 font-semibold text-slate-200">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Client Isolation Diagnostic</span>
        </div>
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
            isIsolated ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-red-950 text-red-300 border border-red-800'
          }`}
        >
          {isIsolated ? 'STRICT ISOLATION VERIFIED' : 'LEAKAGE DETECTED'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
        <div>
          <span className="text-slate-500">Active Client ID:</span>{' '}
          <span className="text-amber-300 font-bold">{activeClient.id}</span>
        </div>
        <div>
          <span className="text-slate-500">Required Tag:</span>{' '}
          <span className="text-indigo-300 font-bold">{activeTag}</span>
        </div>
      </div>

      {recalledMemories.length > 0 && (
        <div className="space-y-1 pt-1 max-h-28 overflow-y-auto pr-1">
          {tagBreakdown.map((item) => (
            <div
              key={item.memId}
              className={`p-1.5 rounded flex items-center justify-between text-[10px] ${
                item.isMatch
                  ? 'bg-slate-800/80 text-slate-300'
                  : 'bg-red-900/50 text-red-200'
              }`}
            >
              <span>{item.memId}</span>
              <div className="flex items-center space-x-1">
                <span>tags: [{item.tags.join(', ')}]</span>
                {!item.isMatch && <AlertTriangle className="w-3 h-3 text-red-400" />}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
