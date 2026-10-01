import React, { useState } from 'react';
import { Copy, Check, AlertTriangle, Cpu, ShieldAlert, FileText, ExternalLink } from 'lucide-react';
import { AgentResponse, RecalledMemory } from '../types/api';

interface ResponseResultProps {
  response: AgentResponse;
  onOpenSourceMemory: (mem: RecalledMemory) => void;
  titleSuffix?: string;
}

export const ResponseResult: React.FC<ResponseResultProps> = ({
  response,
  onOpenSourceMemory,
  titleSuffix = '',
}) => {
  const [draftText, setDraftText] = useState<string>(response.draft_reply);
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(draftText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const findMemoryByCitation = (sourceId: string): RecalledMemory | undefined => {
    return response.memory_used.find(
      (m) => m.id === sourceId || m.source_interaction_id === sourceId || m.document_id === sourceId
    );
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-6">
      <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
            {response.memory_enabled ? 'Memory-Aware Reply' : 'Generic Draft (Memory OFF)'}
            {titleSuffix && <span className="text-slate-400 font-normal ml-1">({titleSuffix})</span>}
          </h3>
        </div>

        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
            <Cpu className="w-3 h-3 text-brand-500" />
            {response.model_used}
          </span>
        </div>
      </div>

      {response.warnings && response.warnings.length > 0 && (
        <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/60 text-xs text-amber-800 dark:text-amber-200 space-y-1">
          <div className="flex items-center space-x-1.5 font-semibold">
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
            <span>Notice / Memory Status</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-[11px] pl-1">
            {response.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Draft Reply
          </label>
          <button
            onClick={handleCopy}
            className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-medium rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>

        <textarea
          value={draftText}
          onChange={(e) => setDraftText(e.target.value)}
          rows={6}
          className="w-full p-3 text-sm rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors leading-relaxed"
        />
      </div>

      {response.client_brief && response.client_brief.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-brand-500" /> Client Brief & History Citations
          </h4>

          <ul className="space-y-2">
            {response.client_brief.map((item, idx) => (
              <li
                key={idx}
                className="p-2.5 rounded-lg bg-slate-50/70 dark:bg-slate-800/40 border border-slate-200/60 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-200 space-y-1.5"
              >
                <p className="leading-normal">{item.text}</p>

                <div className="flex flex-wrap items-center gap-1">
                  <span className="text-[10px] text-slate-400 font-medium">Sources:</span>
                  {[...item.source_interaction_ids, ...item.source_memory_ids].map((sourceId) => {
                    const matchedMem = findMemoryByCitation(sourceId);
                    return (
                      <button
                        key={sourceId}
                        onClick={() => matchedMem && onOpenSourceMemory(matchedMem)}
                        disabled={!matchedMem}
                        className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800 hover:bg-brand-100 dark:hover:bg-brand-900 transition-colors disabled:opacity-50"
                      >
                        <span>{sourceId}</span>
                        {matchedMem && <ExternalLink className="w-2.5 h-2.5" />}
                      </button>
                    );
                  })}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {response.risk_flags && response.risk_flags.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
          <h4 className="text-xs font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5" /> Risk Flags & Watchpoints
          </h4>

          <div className="grid gap-2 sm:grid-cols-1">
            {response.risk_flags.map((risk, idx) => {
              const isPayment = risk.type.toLowerCase().includes('payment') || risk.type.toLowerCase().includes('late');
              const cardBg = isPayment
                ? 'bg-amber-50/80 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/50'
                : 'bg-indigo-50/80 dark:bg-indigo-950/30 border-indigo-200 dark:border-indigo-900/50';

              const badgeColor = isPayment
                ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                : 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200';

              return (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border text-xs space-y-1.5 ${cardBg}`}
                >
                  <div className="flex items-center justify-between">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${badgeColor}`}>
                      {risk.type}
                    </span>
                  </div>

                  <p className="text-slate-800 dark:text-slate-200 leading-normal">
                    {risk.text}
                  </p>

                  {risk.sources && risk.sources.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1 pt-1">
                      <span className="text-[10px] text-slate-400">Sources:</span>
                      {risk.sources.map((srcId) => {
                        const matchedMem = findMemoryByCitation(srcId);
                        return (
                          <button
                            key={srcId}
                            onClick={() => matchedMem && onOpenSourceMemory(matchedMem)}
                            disabled={!matchedMem}
                            className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
                          >
                            <span>{srcId}</span>
                            {matchedMem && <ExternalLink className="w-2.5 h-2.5" />}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
