import React, { useState, useEffect } from 'react';
import { Header } from './Header';
import { Sidebar, NavTab } from './Sidebar';
import { ReviewSetup } from '../features/reviews/ReviewSetup';
import { SearchBuilder } from '../features/search/SearchBuilder';
import { DuplicatesQueue } from '../features/duplicates/DuplicatesQueue';
import { ScreeningQueue } from '../features/screening/ScreeningQueue';
import { PicoWorkspace } from '../features/pico/PicoWorkspace';
import { HistoryDiffView } from '../features/history/HistoryDiffView';
import { ConflictsWorkspace } from '../features/conflicts/ConflictsWorkspace';
import { AuditTrail } from '../features/audit/AuditTrail';
import { ExportView } from '../features/export/ExportView';
import { api } from '../lib/api';
import { Review } from '../types/api';

export function App() {
  const [activeTab, setActiveTab] = useState<NavTab>('setup');
  const [review, setReview] = useState<Review | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const loadStats = async () => {
    try {
      const rev = await api.getReview(1);
      setReview(rev);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadStats();
  }, [refreshKey, activeTab]);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-brand-500 selection:text-white">
      {/* Top Header */}
      <Header onRefresh={handleRefresh} />

      {/* Main Container: Sidebar + Content */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          stats={review?.stats}
        />

        {/* Viewport Content */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-gradient-to-b from-slate-950 via-slate-900/40 to-slate-950">
          {activeTab === 'setup' && <ReviewSetup />}
          {activeTab === 'search' && <SearchBuilder />}
          {activeTab === 'duplicates' && <DuplicatesQueue />}
          {activeTab === 'screening' && <ScreeningQueue />}
          {activeTab === 'pico' && <PicoWorkspace />}
          {activeTab === 'history' && <HistoryDiffView onNavigateToConflicts={() => setActiveTab('conflicts')} />}
          {activeTab === 'conflicts' && <ConflictsWorkspace />}
          {activeTab === 'audit' && <AuditTrail />}
          {activeTab === 'export' && <ExportView />}
        </main>
      </div>
    </div>
  );
}

export default App;
