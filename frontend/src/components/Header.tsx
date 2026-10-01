import React, { useEffect, useState } from 'react';
import { Activity, Moon, Sun, ShieldCheck } from 'lucide-react';
import { api } from '../api/client';
import { HealthResponse } from '../types/api';

interface HeaderProps {
  darkMode: boolean;
  onToggleDarkMode: () => void;
  showDiagnostics: boolean;
  onToggleDiagnostics: () => void;
  currentModel?: string;
  activeTab: 'workbench' | 'learning_curve';
  onSelectTab: (tab: 'workbench' | 'learning_curve') => void;
}

export const Header: React.FC<HeaderProps> = ({
  darkMode,
  onToggleDarkMode,
  showDiagnostics,
  onToggleDiagnostics,
  currentModel,
  activeTab,
  onSelectTab,
}) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      try {
        const res = await api.getHealth();
        if (isMounted) {
          setHealth(res);
          setHealthError(false);
        }
      } catch {
        if (isMounted) {
          setHealthError(true);
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="sticky top-0 z-30 bg-white/90 dark:bg-slate-900/90 backdrop-blur border-b border-slate-200 dark:border-slate-800 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
              R
            </div>
            <span className="font-semibold text-lg tracking-tight text-slate-900 dark:text-slate-100">
              Rapport
            </span>
          </div>

          <nav className="flex space-x-1">
            <button
              onClick={() => onSelectTab('workbench')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'workbench'
                  ? 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              Reply Workbench
            </button>
            <button
              onClick={() => onSelectTab('learning_curve')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'learning_curve'
                  ? 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              Learning Curve Evaluation
            </button>
          </nav>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
            <Activity
              className={`w-3.5 h-3.5 ${
                healthError
                  ? 'text-red-500 animate-pulse'
                  : health?.memory_backend === 'HindsightMemory'
                  ? 'text-emerald-500'
                  : 'text-amber-500'
              }`}
            />
            <span>
              {healthError
                ? 'Backend Offline'
                : health?.memory_backend === 'HindsightMemory'
                ? 'Hindsight Connected'
                : 'Offline Fake Memory'}
            </span>
          </div>

          {currentModel && (
            <span className="hidden sm:inline-block text-xs font-mono px-2.5 py-1 rounded-full bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 border border-brand-200/50 dark:border-brand-800/50">
              {currentModel}
            </span>
          )}

          <button
            onClick={onToggleDiagnostics}
            title="Toggle dev diagnostics"
            className={`p-1.5 rounded-lg border transition-colors ${
              showDiagnostics
                ? 'bg-indigo-50 border-indigo-300 text-indigo-700 dark:bg-indigo-950/50 dark:border-indigo-800 dark:text-indigo-300'
                : 'border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
          </button>

          <button
            onClick={onToggleDarkMode}
            title="Toggle theme"
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 transition-colors"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </header>
  );
};
