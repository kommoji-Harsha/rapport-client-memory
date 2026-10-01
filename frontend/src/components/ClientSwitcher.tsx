import React from 'react';
import { Client } from '../types/api';
import { Upload, UserCheck } from 'lucide-react';

interface ClientSwitcherProps {
  clients: Client[];
  activeClient: Client | null;
  onSelectClient: (client: Client) => void;
  onOpenImport: () => void;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

const AVATAR_COLORS = [
  'bg-blue-600',
  'bg-emerald-600',
  'bg-purple-600',
  'bg-amber-600',
  'bg-rose-600',
  'bg-indigo-600',
];

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % AVATAR_COLORS.length;
  return AVATAR_COLORS[index];
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export const ClientSwitcher: React.FC<ClientSwitcherProps> = ({
  clients,
  activeClient,
  onSelectClient,
  onOpenImport,
  isLoading,
  error,
  onRetry,
}) => {
  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800 shadow-sm animate-pulse space-y-3">
        <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-1/3"></div>
        <div className="h-12 bg-slate-100 dark:bg-slate-800/60 rounded-lg"></div>
        <div className="h-12 bg-slate-100 dark:bg-slate-800/60 rounded-lg"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 rounded-xl p-4 text-sm text-red-700 dark:text-red-300 space-y-2">
        <p className="font-semibold">Failed to load clients</p>
        <p className="text-xs">{error}</p>
        <button
          onClick={onRetry}
          className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-medium transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold tracking-wider text-slate-500 dark:text-slate-400 uppercase">
          Client Workspace
        </h2>
        {activeClient && (
          <button
            onClick={onOpenImport}
            className="inline-flex items-center space-x-1.5 text-xs font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 transition-colors"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Import History</span>
          </button>
        )}
      </div>

      {clients.length === 0 ? (
        <div className="text-center py-6 text-slate-500 dark:text-slate-400 text-sm">
          No clients found.
        </div>
      ) : (
        <div className="space-y-2">
          {clients.map((client) => {
            const isActive = activeClient?.id === client.id;
            const initials = getInitials(client.name);
            const avatarBg = getAvatarColor(client.name);

            return (
              <button
                key={client.id}
                onClick={() => onSelectClient(client)}
                className={`w-full text-left p-3 rounded-lg border transition-all duration-150 flex items-start space-x-3 ${
                  isActive
                    ? 'bg-slate-50 dark:bg-slate-800/80 border-brand-500 dark:border-brand-500 shadow-sm'
                    : 'border-slate-200/80 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50/50 dark:hover:bg-slate-800/40'
                }`}
              >
                <div
                  className={`w-9 h-9 rounded-lg ${avatarBg} text-white font-semibold text-xs flex items-center justify-center shrink-0 shadow-sm`}
                >
                  {initials}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm text-slate-900 dark:text-slate-100 truncate">
                      {client.name}
                    </span>
                    {isActive && (
                      <UserCheck className="w-4 h-4 text-brand-600 dark:text-brand-400 shrink-0" />
                    )}
                  </div>

                  <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                    {client.contact_name ? `${client.contact_name} • ` : ''}
                    {client.industry || 'Consulting'}
                  </p>

                  <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-1 italic mt-1 bg-slate-100/60 dark:bg-slate-800/60 px-1.5 py-0.5 rounded">
                    {client.primary_quirk || 'Standard preferences'}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
