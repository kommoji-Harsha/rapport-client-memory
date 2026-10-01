import React, { useEffect, useState } from 'react';
import { api } from './api/client';
import { Client, AgentResponse, RecalledMemory } from './types/api';
import { Header } from './components/Header';
import { ClientSwitcher } from './components/ClientSwitcher';
import { ReplyWorkbench } from './components/ReplyWorkbench';
import { MemoryPanel } from './components/MemoryPanel';
import { FeedbackPanel } from './components/FeedbackPanel';
import { SourceDrawer } from './components/SourceDrawer';
import { ImportDialog } from './components/ImportDialog';
import { CrossClientSanityBadge } from './components/CrossClientSanityBadge';
import { LearningCurvePage } from './components/LearningCurvePage';

export const App: React.FC = () => {
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    return localStorage.getItem('rapport_theme') === 'dark';
  });
  const [showDiagnostics, setShowDiagnostics] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'workbench' | 'learning_curve'>('workbench');

  const [clients, setClients] = useState<Client[]>([]);
  const [activeClient, setActiveClient] = useState<Client | null>(null);
  const [loadingClients, setLoadingClients] = useState<boolean>(true);
  const [clientsError, setClientsError] = useState<string | null>(null);

  const [currentResponse, setCurrentResponse] = useState<AgentResponse | null>(null);
  const [inspectedMemory, setInspectedMemory] = useState<RecalledMemory | null>(null);
  const [isSourceDrawerOpen, setIsSourceDrawerOpen] = useState<boolean>(false);
  const [isImportOpen, setIsImportOpen] = useState<boolean>(false);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('rapport_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('rapport_theme', 'light');
    }
  }, [darkMode]);

  const fetchClients = async () => {
    setLoadingClients(true);
    setClientsError(null);
    try {
      const data = await api.getClients();
      setClients(data);
      if (data.length > 0 && !activeClient) {
        setActiveClient(data[0]);
      }
    } catch (err) {
      setClientsError(err instanceof Error ? err.message : 'Failed to connect to backend API');
    } finally {
      setLoadingClients(false);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  const handleOpenSourceMemory = (mem: RecalledMemory) => {
    setInspectedMemory(mem);
    setIsSourceDrawerOpen(true);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors">
      <Header
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode(!darkMode)}
        showDiagnostics={showDiagnostics}
        onToggleDiagnostics={() => setShowDiagnostics(!showDiagnostics)}
        currentModel={currentResponse?.model_used}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {activeTab === 'learning_curve' ? (
          <LearningCurvePage />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            <div className="lg:col-span-4 space-y-6">
              <ClientSwitcher
                clients={clients}
                activeClient={activeClient}
                onSelectClient={(c) => {
                  setActiveClient(c);
                  setCurrentResponse(null);
                }}
                onOpenImport={() => setIsImportOpen(true)}
                isLoading={loadingClients}
                error={clientsError}
                onRetry={fetchClients}
              />

              {showDiagnostics && (
                <CrossClientSanityBadge
                  activeClient={activeClient}
                  recalledMemories={currentResponse?.memory_used || []}
                />
              )}
            </div>

            <div className="lg:col-span-8 space-y-8">
              <ReplyWorkbench
                activeClient={activeClient}
                onOpenSourceMemory={handleOpenSourceMemory}
                onResponseGenerated={(resp) => setCurrentResponse(resp)}
              />

              {currentResponse && (
                <>
                  <FeedbackPanel responseId={currentResponse.response_id || 'unknown'} />

                  <MemoryPanel
                    activeClient={activeClient}
                    recalledMemories={currentResponse.memory_used}
                    onOpenMemory={handleOpenSourceMemory}
                  />
                </>
              )}
            </div>
          </div>
        )}
      </main>

      <SourceDrawer
        memory={inspectedMemory}
        isOpen={isSourceDrawerOpen}
        onClose={() => setIsSourceDrawerOpen(false)}
      />

      <ImportDialog
        activeClient={activeClient}
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
      />

      <footer className="border-t border-slate-200 dark:border-slate-800 py-6 text-center text-xs text-slate-500 dark:text-slate-400">
        Rapport Client-Memory Agent • Powered by Hindsight Cloud & Groq LLM
      </footer>
    </div>
  );
};

export default App;
