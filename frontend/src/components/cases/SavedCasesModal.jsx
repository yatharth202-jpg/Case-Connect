import React, { useState, useEffect } from 'react';
import { casesApi, reportsApi } from '../../api/client';
import { useCaseFlow } from '../../context/CaseFlowContext';
import { 
  FolderOpen, Search, Plus, X, Download, FileText, 
  ExternalLink, Trash2, CheckCircle2, AlertCircle, Clock, 
  Shield, Layers, ChevronRight, Copy, Check
} from 'lucide-react';

export const SavedCasesModal = ({ isOpen, onClose }) => {
  const { loadCaseById, activeCaseId } = useCaseFlow();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');

  // New Case Form state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newPriority, setNewPriority] = useState('medium');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  // Report export states
  const [exportingId, setExportingId] = useState(null);
  const [exportSuccess, setExportSuccess] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    if (isOpen) {
      fetchCases();
    }
  }, [isOpen, search, priorityFilter]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const res = await casesApi.list(search, priorityFilter);
      const list = res.cases || res || [];
      setCases(Array.isArray(list) ? list : []);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not retrieve stored investigation dockets.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCase = async (e) => {
    e.preventDefault();
    if (!newTitle.trim()) {
      setCreateError('Case docket title is required.');
      return;
    }

    setCreating(true);
    setCreateError('');
    try {
      const created = await casesApi.create({
        title: newTitle.trim(),
        description: newDesc.trim(),
        priority: newPriority,
      });
      setNewTitle('');
      setNewDesc('');
      setNewPriority('medium');
      setShowCreateForm(false);
      await fetchCases();
      // Automatically load into single-scroll dossier
      if (created?.id) {
        loadCaseById(created.id);
        onClose();
      }
    } catch (err) {
      setCreateError(err.response?.data?.detail || 'Failed to create case docket.');
    } finally {
      setCreating(false);
    }
  };

  const handleOpenDossier = (caseId) => {
    loadCaseById(caseId);
    onClose();
  };

  const handleExportPdf = async (caseId, caseTitle) => {
    setExportingId(caseId);
    setExportSuccess(null);
    try {
      const cleanTitle = (caseTitle || 'Case_Dossier').replace(/[^a-zA-Z0-9_-]/g, '_');
      const filename = `${cleanTitle}_Sec63_BSA.pdf`;

      // 1. Generate ReportLab PDF via backend
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

      // 2. Download the generated binary PDF
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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-ink/85 backdrop-blur-xl animate-fadeIn">
      {/* Main Glass Dialog */}
      <div 
        className="w-full max-w-5xl max-h-[90vh] glass border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Header */}
        <div className="p-5 sm:p-6 border-b border-white/[0.08] flex items-center justify-between gap-4 bg-white/[0.02]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl glass-sm border border-accent/20 flex items-center justify-center text-accent">
              <FolderOpen className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-serif text-xl sm:text-2xl text-text font-semibold">
                  Investigation Dossiers Ledger
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-accent/10 border border-accent/30 text-accent uppercase tracking-wider">
                  {cases.length} Dockets
                </span>
              </div>
              <p className="text-xs font-mono text-muted mt-0.5">
                Section 63 BSA 2023 compliant repository · Sovereign SQLite source of truth
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="glass-pill px-3.5 py-1.5 flex items-center gap-1.5 text-xs font-mono text-text hover:text-accent border-white/15 hover:border-accent/40 transition-all"
            >
              <Plus className="w-3.5 h-3.5 text-accent" />
              <span>{showCreateForm ? 'Cancel New Docket' : 'New Case Docket'}</span>
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full glass-sm border border-white/10 flex items-center justify-center text-muted hover:text-text hover:bg-white/[0.06] transition-colors"
              title="Close (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Global Alert Notification Banner */}
        {exportSuccess && (
          <div className="px-6 py-2.5 bg-data/10 border-b border-data/20 text-data text-xs font-mono flex items-center gap-2 animate-fadeIn">
            <CheckCircle2 className="w-4 h-4" />
            <span>{exportSuccess}</span>
          </div>
        )}

        {/* Sub-panel: Inline New Docket Creator */}
        {showCreateForm && (
          <div className="p-5 border-b border-white/[0.08] bg-white/[0.03] animate-fadeIn">
            <form onSubmit={handleCreateCase} className="space-y-4 max-w-3xl">
              <div className="flex items-center gap-2 text-xs font-mono text-accent">
                <Shield className="w-3.5 h-3.5" />
                <span>REGISTER NEW STATUTORY CASE DOCKET</span>
              </div>

              {createError && (
                <div className="p-3 rounded-lg bg-alert/10 border border-alert/30 text-alert text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{createError}</span>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2 space-y-1">
                  <label className="text-[11px] font-mono text-muted uppercase">Case Title / Reference *</label>
                  <input
                    type="text"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="e.g., Hawala Money Routing Network (FIR #408)"
                    className="w-full px-3.5 py-2 glass-sm border border-white/10 rounded-lg text-xs font-mono text-text placeholder-muted focus:outline-none focus:border-accent"
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-mono text-muted uppercase">Priority Status</label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value)}
                    className="w-full px-3.5 py-2 glass-sm border border-white/10 rounded-lg text-xs font-mono text-text bg-ink focus:outline-none focus:border-accent"
                  >
                    <option value="high">High Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="low">Low Priority</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-mono text-muted uppercase">Investigation Docket Description</label>
                <textarea
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  rows={2}
                  placeholder="Summary of statutory allegations, jurisdiction units, and initial intelligence leads..."
                  className="w-full px-3.5 py-2 glass-sm border border-white/10 rounded-lg text-xs font-mono text-text placeholder-muted focus:outline-none focus:border-accent resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-3 py-1.5 rounded-lg text-xs font-mono text-muted hover:text-text"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-1.5 rounded-lg bg-accent text-ink font-mono text-xs font-semibold hover:bg-accent/90 transition-all flex items-center gap-1.5 disabled:opacity-50"
                >
                  {creating ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-ink/40 border-t-ink rounded-full animate-spin" />
                      <span>Creating...</span>
                    </>
                  ) : (
                    <span>Register Case Docket</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Filter and Search Bar */}
        <div className="p-4 sm:px-6 border-b border-white/[0.06] flex flex-col sm:flex-row items-center justify-between gap-3 bg-white/[0.01]">
          {/* Search Bar */}
          <div className="w-full sm:w-80 relative">
            <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title or docket ID..."
              className="w-full pl-9 pr-3.5 py-1.5 glass-sm border border-white/10 rounded-lg text-xs font-mono text-text placeholder-muted focus:outline-none focus:border-accent"
            />
          </div>

          {/* Priority Filter Buttons */}
          <div className="flex items-center gap-1.5 w-full sm:w-auto">
            {['all', 'high', 'medium', 'low'].map((p) => (
              <button
                key={p}
                onClick={() => setPriorityFilter(p)}
                className={`text-[11px] font-mono uppercase tracking-wider px-3 py-1 rounded-full transition-all ${
                  priorityFilter === p
                    ? 'bg-accent/15 text-accent border border-accent/40 font-semibold'
                    : 'text-muted hover:text-text hover:bg-white/[0.04] border border-transparent'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Docket Cards Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-3 custom-scrollbar">
          {error && (
            <div className="p-3.5 rounded-xl bg-alert/10 border border-alert/30 text-alert text-xs font-mono flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div className="py-20 text-center space-y-3">
              <div className="w-6 h-6 border-2 border-white/20 border-t-accent rounded-full animate-spin mx-auto" />
              <p className="text-xs font-mono text-muted">Retrieving court investigation dockets...</p>
            </div>
          ) : cases.length === 0 ? (
            <div className="py-16 text-center border border-dashed border-white/10 rounded-xl p-8 glass-sm">
              <FolderOpen className="w-10 h-10 text-muted mx-auto mb-3 opacity-60" />
              <h3 className="font-serif text-lg text-text font-medium">No Investigation Dockets Found</h3>
              <p className="text-xs font-mono text-muted mt-1 max-w-md mx-auto">
                {search || priorityFilter !== 'all'
                  ? 'No stored cases match your active filter criteria. Try clearing search keywords.'
                  : 'No statutory cases have been opened yet. Ingest evidence files or create a new docket.'}
              </p>
              <div className="mt-4">
                <button
                  onClick={() => setShowCreateForm(true)}
                  className="px-4 py-2 rounded-lg bg-accent/20 border border-accent/40 text-accent font-mono text-xs hover:bg-accent/30 transition-all inline-flex items-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create First Docket</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {cases.map((c) => {
                const isCurrent = activeCaseId === c.id;
                const priorityColor = 
                  c.priority === 'high' ? 'text-alert border-alert/40 bg-alert/10' :
                  c.priority === 'medium' ? 'text-accent border-accent/40 bg-accent/10' :
                  'text-data border-data/40 bg-data/10';

                return (
                  <div
                    key={c.id}
                    className={`glass-sm p-4 sm:p-5 rounded-xl border transition-all duration-200 hover:border-white/20 ${
                      isCurrent 
                        ? 'border-accent/40 bg-accent/[0.03] shadow-lg shadow-accent/5' 
                        : 'border-white/[0.08]'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      {/* Left: Case Info */}
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <button
                            onClick={() => handleCopyId(c.id)}
                            className="inline-flex items-center gap-1 text-[10px] font-mono text-muted bg-white/[0.04] px-2 py-0.5 rounded border border-white/10 hover:text-text transition-colors"
                            title="Click to copy full Case UUID"
                          >
                            <span>ID: {c.id.substring(0, 8)}</span>
                            {copiedId === c.id ? <Check className="w-3 h-3 text-data" /> : <Copy className="w-3 h-3 opacity-60" />}
                          </button>

                          <span className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded-full border ${priorityColor}`}>
                            {c.priority || 'medium'} priority
                          </span>

                          <span className="text-[10px] font-mono text-muted uppercase">
                            Status: <strong className="text-text">{c.status || 'Active'}</strong>
                          </span>

                          {isCurrent && (
                            <span className="text-[9px] font-mono text-accent bg-accent/15 px-2 py-0.5 rounded-full border border-accent/30 animate-pulse">
                              Active in Dossier
                            </span>
                          )}
                        </div>

                        <h4 className="font-serif text-lg text-text font-medium truncate">
                          {c.title || 'Untitled Case Docket'}
                        </h4>

                        {c.description && (
                          <p className="text-xs text-muted line-clamp-1">
                            {c.description}
                          </p>
                        )}

                        <div className="flex items-center gap-4 text-[10px] font-mono text-muted pt-1">
                          <span className="inline-flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>{c.created_at ? new Date(c.created_at).toLocaleDateString() : 'Active'}</span>
                          </span>
                        </div>
                      </div>

                      {/* Right: Actions Strip */}
                      <div className="flex items-center gap-1.5 flex-wrap sm:flex-nowrap pt-2 sm:pt-0 border-t sm:border-t-0 border-white/[0.06]">
                        {/* Open Single Scroll Dossier */}
                        <button
                          onClick={() => handleOpenDossier(c.id)}
                          className="px-3 py-1.5 rounded-lg bg-accent text-ink font-mono text-xs font-semibold hover:bg-accent/90 transition-all flex items-center gap-1.5 shadow-sm"
                          title="Open Single-Scroll Forensic Dossier"
                        >
                          <span>Open Dossier</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>

                        {/* Section 63 BSA PDF Export */}
                        <button
                          onClick={() => handleExportPdf(c.id, c.title)}
                          disabled={exportingId === c.id}
                          className="px-2.5 py-1.5 rounded-lg glass-sm border border-white/10 text-text hover:text-accent hover:border-accent/30 font-mono text-xs transition-all flex items-center gap-1.5 disabled:opacity-50"
                          title="Generate Section 63 BSA Court Admissible PDF Dossier"
                        >
                          {exportingId === c.id ? (
                            <>
                              <div className="w-3.5 h-3.5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
                              <span className="hidden sm:inline">Generating...</span>
                            </>
                          ) : (
                            <>
                              <Download className="w-3.5 h-3.5 text-accent" />
                              <span className="hidden sm:inline">Court PDF</span>
                            </>
                          )}
                        </button>

                        {/* JSON Export */}
                        <button
                          onClick={() => handleExportJson(c.id, c.title)}
                          className="p-1.5 rounded-lg glass-sm border border-white/10 text-muted hover:text-text hover:border-white/20 transition-all"
                          title="Export Forensic JSON"
                        >
                          <FileText className="w-3.5 h-3.5" />
                        </button>

                        {/* Deep Workbench Link */}
                        <a
                          href={`/cases/${c.id}`}
                          className="p-1.5 rounded-lg glass-sm border border-white/10 text-muted hover:text-text hover:border-white/20 transition-all"
                          title="Open Deep Forensic Workbench"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>

                        {/* Delete Docket */}
                        <button
                          onClick={() => handleDeleteCase(c.id)}
                          className="p-1.5 rounded-lg glass-sm border border-white/10 text-muted hover:text-alert hover:border-alert/30 transition-all"
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
        </div>

        {/* Modal Bottom Status Bar */}
        <div className="p-3.5 sm:px-6 border-t border-white/[0.08] bg-white/[0.02] flex items-center justify-between text-[11px] font-mono text-muted">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-data animate-pulse" />
            <span>Sovereign Storage Active</span>
          </div>
          <span className="text-[10px]">ESC to close</span>
        </div>
      </div>
    </div>
  );
};

export default SavedCasesModal;
