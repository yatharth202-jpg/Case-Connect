import React, { useState, useEffect } from 'react';
import { casesApi } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Cases() {
  const { isViewer } = useAuth();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newPriority, setNewPriority] = useState('medium');
  const [creating, setCreating] = useState(false);
  const [modalError, setModalError] = useState('');

  const fetchCases = async () => {
    setLoading(true);
    try {
      const data = await casesApi.list(search, priorityFilter);
      setCases(data);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to retrieve cases repository');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [search, priorityFilter]);

  const handleCreateCase = async (e) => {
    e.preventDefault();
    if (!newTitle.trim()) {
      setModalError('Case title is required.');
      return;
    }

    setCreating(true);
    setModalError('');
    try {
      const created = await casesApi.create({
        title: newTitle.trim(),
        description: newDesc.trim(),
        priority: newPriority,
      });
      setIsModalOpen(false);
      setNewTitle('');
      setNewDesc('');
      setNewPriority('medium');
      fetchCases();
      window.location.href = `/cases/${created.id}`;
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to create case');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Top Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#1e293b]">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white tracking-tight">Investigation Case Repository</h1>
            <span className="text-xs px-2 py-0.5 bg-[#0b1120] border border-[#334155] rounded text-[#38bdf8] font-mono">
              {cases.length} Total
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Active crime network investigations under statutory review (Section 63 BSA 2023).
          </p>
        </div>

        {!isViewer && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded-md transition-colors shadow-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Open New Case</span>
          </button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 my-6">
        {/* Search */}
        <div className="w-full sm:w-72 relative">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title or description..."
            className="w-full pl-9 pr-3 py-2 bg-[#0b1120] border border-[#1e293b] rounded-md text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#38bdf8]"
          />
          <svg className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        {/* Priority Filter */}
        <div className="flex items-center gap-1.5 self-start sm:self-auto">
          {['all', 'high', 'medium', 'low'].map((p) => (
            <button
              key={p}
              onClick={() => setPriorityFilter(p)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md uppercase tracking-wider transition-colors ${
                priorityFilter === p
                  ? 'bg-[#1e293b] text-[#38bdf8] border border-[#38bdf8]/40'
                  : 'bg-[#0b1120] text-slate-400 border border-[#1e293b] hover:text-slate-200'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-rose-950/60 border border-rose-800 rounded-md text-rose-200 text-xs mb-6">
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="py-20 text-center">
          <div className="inline-block animate-spin w-6 h-6 border-2 border-slate-600 border-t-[#38bdf8] rounded-full mb-2"></div>
          <p className="text-xs text-slate-400">Loading cases repository...</p>
        </div>
      ) : cases.length === 0 ? (
        /* Empty state */
        <div className="py-20 text-center border border-dashed border-[#1e293b] rounded-lg bg-[#0b1120]/50">
          <svg className="w-10 h-10 text-slate-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <h3 className="text-sm font-semibold text-white">No investigation cases found</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            {search || priorityFilter !== 'all'
              ? 'No cases match your active search or priority filter criteria.'
              : 'Get started by creating your first case to ingest evidence files and uncover hidden networks.'}
          </p>
          {!isViewer && (
            <div className="mt-5">
              <button
                onClick={() => setIsModalOpen(true)}
                className="px-4 py-2 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded-md transition-colors inline-flex items-center gap-1.5 shadow-sm"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>Open Your First Case</span>
              </button>
            </div>
          )}
        </div>
      ) : (
        /* Cases Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cases.map((c) => (
            <a
              key={c.id}
              href={`/cases/${c.id}`}
              className="group block p-5 bg-[#0b1120] border border-[#1e293b] hover:border-[#38bdf8]/50 rounded-lg transition-all shadow-sm hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-2 mb-3">
                <span className="text-[11px] font-mono text-[#38bdf8] bg-[#030712] px-2 py-0.5 rounded border border-[#1e293b]">
                  ID: {c.id.substring(0, 8)}
                </span>
                <span
                  className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border font-semibold ${
                    c.priority === 'high'
                      ? 'bg-rose-950/60 text-rose-300 border-rose-800'
                      : c.priority === 'medium'
                      ? 'bg-amber-950/60 text-amber-300 border-amber-800'
                      : 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                  }`}
                >
                  {c.priority}
                </span>
              </div>

              <h2 className="text-sm font-bold text-white group-hover:text-[#38bdf8] transition-colors line-clamp-1 mb-1.5">
                {c.title}
              </h2>

              <p className="text-xs text-slate-400 line-clamp-2 min-h-[32px] mb-4">
                {c.description || 'No case description recorded.'}
              </p>

              <div className="pt-3 border-t border-[#1e293b] flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span>Files: {c.evidence_count}</span>
                <span>{new Date(c.created_at).toLocaleDateString()}</span>
              </div>
            </a>
          ))}
        </div>
      )}

      {/* New Case Modal */}
      {isModalOpen && (
        <div
          onClick={() => setIsModalOpen(false)}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50 cursor-pointer"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-[#0b1120] border border-[#1e293b] rounded-lg p-6 shadow-2xl cursor-default"
          >
            <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] mb-4">
              <h3 className="text-sm font-bold text-white">Create New Investigation Case</h3>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white text-sm px-2 py-1 rounded hover:bg-[#1e293b] transition-colors"
                title="Close"
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div className="p-2.5 bg-rose-950/60 border border-rose-800 rounded text-rose-200 text-xs mb-4">
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreateCase} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1" htmlFor="case-title">
                  Case Title *
                </label>
                <input
                  id="case-title"
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Operation Golden Layer - NCR Financial Fraud"
                  className="w-full px-3 py-2 bg-[#030712] border border-[#334155] rounded text-white text-xs placeholder-slate-600 focus:outline-none focus:border-[#38bdf8]"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1" htmlFor="case-priority">
                  Investigation Priority
                </label>
                <select
                  id="case-priority"
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className="w-full px-3 py-2 bg-[#030712] border border-[#334155] rounded text-white text-xs focus:outline-none focus:border-[#38bdf8]"
                >
                  <option value="high">High Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="low">Low Priority</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1" htmlFor="case-desc">
                  Case Summary / Description
                </label>
                <textarea
                  id="case-desc"
                  rows={3}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Brief summary of reported complaints, jurisdiction details, or target intelligence..."
                  className="w-full px-3 py-2 bg-[#030712] border border-[#334155] rounded text-white text-xs placeholder-slate-600 focus:outline-none focus:border-[#38bdf8]"
                />
              </div>

              <div className="pt-3 border-t border-[#1e293b] flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-2 bg-[#030712] hover:bg-[#1e293b] text-slate-300 rounded text-xs transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 bg-[#0284c7] hover:bg-[#0369a1] text-white rounded text-xs font-semibold transition-colors disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Initialize Case'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
