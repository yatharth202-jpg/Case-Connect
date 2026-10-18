import React, { useState, useEffect } from 'react';
import { casesApi, reportsApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCaseFlow } from '../context/CaseFlowContext';
import { 
  FolderOpen, Plus, Search, ChevronRight, Download, 
  FileText, ExternalLink, Shield, Clock, AlertCircle, 
  CheckCircle2, Copy, Check, Trash2, X 
} from 'lucide-react';

export default function Cases() {
  const { isViewer } = useAuth();
  const { loadCaseById, activeCaseId } = useCaseFlow();
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

  // Report download states
  const [exportingId, setExportingId] = useState(null);
  const [exportSuccess, setExportSuccess] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const data = await casesApi.list(search, priorityFilter);
      const list = data.cases || data || [];
      setCases(Array.isArray(list) ? list : []);
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
      setModalError('Case docket title is required.');
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
      await fetchCases();
      if (created?.id) {
        loadCaseById(created.id);
        window.history.pushState(null, '', '/');
      }
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to create case docket');
    } finally {
      setCreating(false);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setNewTitle('');
    setNewDesc('');
    setNewPriority('medium');
    setModalError('');
  };

  const handleOpenDossier = (caseId) => {
    loadCaseById(caseId);
    window.history.pushState(null, '', '/');
  };

  const handleExportPdf = async (caseId, caseTitle) => {
    setExportingId(caseId);
    setExportSuccess(null);
    try {
      const cleanTitle = (caseTitle || 'Case_Dossier').replace(/[^a-zA-Z0-9_-]/g, '_');
      const filename = `${cleanTitle}_Sec63_BSA.pdf`;

      const reportRes = await reportsApi.create(caseId, {
        report_title: `Investigation Court Dossier: ${caseTitle || caseId}`,
        format: 'pdf',
        sections: {
          overview: true,
          entities: true,
          cdr: true,
          financial: true,
          documents: true,
          audit: true
        },
        officer_remarks: 'Section 63 Bharatiya Sakshya Adhiniyam (BSA) 2023 certified court submission.'
      });

      if (reportRes?.id) {
        await reportsApi.download(reportRes.id, filename);
        setExportSuccess(`Dossier PDF downloaded with SHA-256 seal.`);
        setTimeout(() => setExportSuccess(null), 4000);
      }
    } catch (err) {
      console.error('[EXPORT PDF ERROR]', err);
      alert(err.response?.data?.detail || 'Failed to generate court PDF dossier.');
    } finally {
      setExportingId(null);
    }
  };

  const handleExportJson = async (caseId, caseTitle) => {
    try {
      const cleanTitle = (caseTitle || 'Case_Export').replace(/[^a-zA-Z0-9_-]/g, '_');
      await reportsApi.exportJson(caseId, `${cleanTitle}_Forensic.json`);
      setExportSuccess('Full machine-readable forensic JSON exported.');
      setTimeout(() => setExportSuccess(null), 4000);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to export forensic JSON.');
    }
  };

  const handleDeleteCase = async (caseId) => {
    if (!window.confirm('Are you sure you want to delete this case docket and all associated forensic indices? This action is recorded in the immutable audit log.')) {
      return;
    }
    try {
      await casesApi.delete(caseId);
      await fetchCases();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete case.');
    }
  };

  const handleCopyId = (id) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isModalOpen) {
        handleCloseModal();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isModalOpen]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 relative z-10 space-y-6">
      {/* Top Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-white/[0.08]">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-serif text-2xl sm:text-3xl font-semibold text-text tracking-tight">
              Investigation Case Repository
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-accent/10 border border-accent/30 text-accent font-mono">
              {cases.length} Dockets
            </span>
          </div>
          <p className="text-xs text-muted font-mono mt-1">
            Active multi-evidence investigations under statutory review (Section 63 BSA 2023).
          </p>
        </div>

        {!isViewer && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent/90 text-ink font-mono text-xs font-semibold rounded-lg transition-all shadow-md self-start md:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Open New Case Docket</span>
          </button>
        )}
      </div>

      {/* Global Alert Notification Banner */}
      {exportSuccess && (
        <div className="p-3 bg-data/10 border border-data/20 rounded-xl text-data text-xs font-mono flex items-center gap-2 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4" />
          <span>{exportSuccess}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Search */}
        <div className="w-full sm:w-80 relative">
          <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title or docket ID..."
            className="w-full pl-9 pr-3.5 py-2 glass-sm border border-white/10 rounded-lg text-xs font-mono text-text placeholder-muted focus:outline-none focus:border-accent"
          />
        </div>

        {/* Priority Filter */}
        <div className="flex items-center gap-1.5 self-start sm:self-auto">
          {['all', 'high', 'medium', 'low'].map((p) => (
            <button
              key={p}
              onClick={() => setPriorityFilter(p)}
              className={`px-3 py-1.5 text-xs font-mono uppercase tracking-wider rounded-lg transition-colors ${
                priorityFilter === p
                  ? 'bg-accent/15 text-accent border border-accent/40 font-semibold'
                  : 'glass-sm text-muted border border-white/10 hover:text-text'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-alert/10 border border-alert/30 text-alert font-mono text-xs">
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="py-24 text-center space-y-3">
          <div className="w-6 h-6 border-2 border-white/20 border-t-accent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-mono text-muted">Retrieving cases repository...</p>
        </div>
      ) : cases.length === 0 ? (
        /* Empty state */
        <div className="py-20 text-center border border-dashed border-white/10 rounded-2xl p-8 glass">
          <FolderOpen className="w-12 h-12 text-muted mx-auto mb-3 opacity-60" />
          <h3 className="font-serif text-lg font-medium text-text">No investigation cases found</h3>
          <p className="text-xs font-mono text-muted mt-1 max-w-sm mx-auto">
            {search || priorityFilter !== 'all'
              ? 'No cases match your active search or priority filter criteria.'
              : 'Get started by creating your first case to ingest evidence files and uncover hidden networks.'}
          </p>
          {!isViewer && (
            <div className="mt-5">
              <button
                onClick={() => setIsModalOpen(true)}
                className="px-4 py-2 bg-accent hover:bg-accent/90 text-ink font-mono text-xs font-semibold rounded-lg transition-all inline-flex items-center gap-1.5 shadow-md"
              >
                <Plus className="w-4 h-4" />
                <span>Open Your First Docket</span>
              </button>
            </div>
          )}
        </div>
      ) : (
        /* Cases Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cases.map((c) => {
            const isCurrent = activeCaseId === c.id;
            const priorityColor = 
              c.priority === 'high' ? 'text-alert border-alert/40 bg-alert/10' :
              c.priority === 'medium' ? 'text-accent border-accent/40 bg-accent/10' :
              'text-data border-data/40 bg-data/10';

            return (
              <div
                key={c.id}
                className={`glass p-5 rounded-2xl border transition-all duration-200 flex flex-col justify-between hover:border-white/20 ${
                  isCurrent ? 'border-accent/40 bg-accent/[0.02]' : 'border-white/[0.08]'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <button
                      onClick={() => handleCopyId(c.id)}
                      className="inline-flex items-center gap-1 text-[10px] font-mono text-muted bg-white/[0.04] px-2 py-0.5 rounded border border-white/10 hover:text-text transition-colors"
                      title="Copy full Case ID"
                    >
                      <span>ID: {c.id.substring(0, 8)}</span>
                      {copiedId === c.id ? <Check className="w-3 h-3 text-data" /> : <Copy className="w-3 h-3 opacity-60" />}
                    </button>
                    <span className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded-full border ${priorityColor}`}>
                      {c.priority} priority
                    </span>
                  </div>

                  <div>
                    <h2 className="font-serif text-lg font-medium text-text line-clamp-1 mb-1">
                      {c.title}
                    </h2>
                    <p className="text-xs font-mono text-muted line-clamp-2 min-h-[32px]">
                      {c.description || 'Statutory investigation docket under active review.'}
                    </p>
                  </div>
                </div>

                <div className="pt-4 mt-4 border-t border-white/[0.06] flex items-center justify-between gap-2">
                  <div className="text-[10px] font-mono text-muted flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>{new Date(c.created_at).toLocaleDateString()}</span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {/* Open Dossier */}
                    <button
                      onClick={() => handleOpenDossier(c.id)}
                      className="px-2.5 py-1 rounded-md bg-accent text-ink font-mono text-xs font-semibold hover:bg-accent/90 transition-all flex items-center gap-1"
                      title="Open Single-Scroll Dossier"
                    >
                      <span>Dossier</span>
                      <ChevronRight className="w-3 h-3" />
                    </button>

                    {/* Court PDF */}
                    <button
                      onClick={() => handleExportPdf(c.id, c.title)}
                      disabled={exportingId === c.id}
                      className="p-1 rounded-md glass-sm border border-white/10 text-muted hover:text-accent transition-all disabled:opacity-50"
                      title="Generate Court PDF (Section 63 BSA)"
                    >
                      {exportingId === c.id ? (
                        <div className="w-3.5 h-3.5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
                      ) : (
                        <Download className="w-3.5 h-3.5" />
                      )}
                    </button>

                    {/* JSON Export */}
                    <button
                      onClick={() => handleExportJson(c.id, c.title)}
                      className="p-1 rounded-md glass-sm border border-white/10 text-muted hover:text-text transition-all"
                      title="Export Forensic JSON"
                    >
                      <FileText className="w-3.5 h-3.5" />
                    </button>

                    {/* Deep Workbench */}
                    <a
                      href={`/cases/${c.id}`}
                      className="p-1 rounded-md glass-sm border border-white/10 text-muted hover:text-text transition-all"
                      title="Open Advanced Forensic Workbench"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>

                    {/* Delete Docket */}
                    <button
                      onClick={() => handleDeleteCase(c.id)}
                      className="p-1 rounded-md glass-sm border border-white/10 text-muted hover:text-alert transition-all"
                      title="Delete Docket"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* New Case Modal */}
      {isModalOpen && (
        <div
          onClick={() => setIsModalOpen(false)}
          className="fixed inset-0 bg-ink/80 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fadeIn"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg glass border border-white/15 rounded-2xl p-6 shadow-2xl space-y-4"
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-accent" />
                <h3 className="font-serif text-lg font-semibold text-text">Create Investigation Docket</h3>
              </div>
              <button
                type="button"
                onClick={handleCloseModal}
                className="w-7 h-7 rounded-full glass-sm border border-white/10 flex items-center justify-center text-muted hover:text-text transition-colors"
                title="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {modalError && (
              <div className="p-3 bg-alert/10 border border-alert/30 rounded-lg text-alert text-xs font-mono flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleCreateCase} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-muted mb-1 uppercase" htmlFor="case-title">
                  Docket Title / Reference *
                </label>
                <input
                  id="case-title"
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g., Hawala Money Routing Network (FIR #408)"
                  className="w-full px-3.5 py-2 glass-sm border border-white/10 rounded-lg text-xs font-mono text-text placeholder-muted focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-muted mb-1 uppercase" htmlFor="case-priority">
                  Investigation Priority
                </label>
                <select
                  id="case-priority"
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className="w-full px-3.5 py-2 glass-sm border border-white/10 rounded-lg text-xs font-mono text-text bg-ink focus:outline-none focus:border-accent"
                >
                  <option value="high">High Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="low">Low Priority</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-muted mb-1 uppercase" htmlFor="case-desc">
                  Case Summary / Description
                </label>
                <textarea
                  id="case-desc"
                  rows={3}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Brief summary of statutory allegations, jurisdiction units, and intelligence leads..."
                  className="w-full px-3.5 py-2 glass-sm border border-white/10 rounded-lg text-xs font-mono text-text placeholder-muted focus:outline-none focus:border-accent resize-none"
                />
              </div>

              <div className="pt-3 border-t border-white/[0.08] flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="px-3.5 py-2 rounded-lg text-xs font-mono text-muted hover:text-text transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 bg-accent hover:bg-accent/90 text-ink font-mono rounded-lg text-xs font-semibold transition-all disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Register Docket'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
