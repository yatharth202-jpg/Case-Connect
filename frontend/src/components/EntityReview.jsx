import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { extractionApi, evidenceApi } from '../api/client';

const ENTITY_STYLES = {
  PERSON: { bg: 'bg-blue-950/70', border: 'border-blue-600', text: 'text-blue-300', badge: 'bg-blue-900 text-blue-200' },
  PHONE: { bg: 'bg-emerald-950/70', border: 'border-emerald-600', text: 'text-emerald-300', badge: 'bg-emerald-900 text-emerald-200' },
  BANK_ACCOUNT: { bg: 'bg-amber-950/70', border: 'border-amber-600', text: 'text-amber-300', badge: 'bg-amber-900 text-amber-200' },
  ACCOUNT_SUFFIX: { bg: 'bg-slate-900/70', border: 'border-slate-600', text: 'text-slate-300', badge: 'bg-slate-800 text-slate-300' },
  VEHICLE: { bg: 'bg-cyan-950/70', border: 'border-cyan-600', text: 'text-cyan-300', badge: 'bg-cyan-900 text-cyan-200' },
  AMOUNT: { bg: 'bg-indigo-950/70', border: 'border-indigo-600', text: 'text-indigo-300', badge: 'bg-indigo-900 text-indigo-200' },
  DATE: { bg: 'bg-purple-950/70', border: 'border-purple-600', text: 'text-purple-300', badge: 'bg-purple-900 text-purple-200' },
  EMAIL: { bg: 'bg-teal-950/70', border: 'border-teal-600', text: 'text-teal-300', badge: 'bg-teal-900 text-teal-200' },
  IP: { bg: 'bg-pink-950/70', border: 'border-pink-600', text: 'text-pink-300', badge: 'bg-pink-900 text-pink-200' },
  FIR: { bg: 'bg-rose-950/70', border: 'border-rose-600', text: 'text-rose-300', badge: 'bg-rose-900 text-rose-200' },
  POLICE_STATION: { bg: 'bg-orange-950/70', border: 'border-orange-600', text: 'text-orange-300', badge: 'bg-orange-900 text-orange-200' },
  RELATIONSHIP: { bg: 'bg-violet-950/70', border: 'border-violet-600', text: 'text-violet-300', badge: 'bg-violet-900 text-violet-200' },
  DEFAULT: { bg: 'bg-slate-900/70', border: 'border-slate-600', text: 'text-slate-300', badge: 'bg-slate-800 text-slate-300' },
};

export default function EntityReview({ caseId, isViewer }) {
  // Document selection
  const [docList, setDocList] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [docLoading, setDocLoading] = useState(false);
  const [docData, setDocData] = useState(null);
  const [currentPageIdx, setCurrentPageIdx] = useState(0);

  // Entities review state
  const [entities, setEntities] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'pending_review', 'approved', 'rejected'
  const [typeFilter, setTypeFilter] = useState('all');
  const [selectedEntityId, setSelectedEntityId] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Manual Add Modal
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [manualType, setManualType] = useState('PERSON');
  const [manualRaw, setManualRaw] = useState('');
  const [manualNorm, setManualNorm] = useState('');

  // 1. Fetch case evidence files and filter text documents (pdf, docx, txt)
  useEffect(() => {
    let mounted = true;
    const loadDocuments = async () => {
      try {
        const evList = await evidenceApi.list(caseId);
        const textDocs = evList.filter((f) => {
          const ext = f.original_name.split('.').pop().toLowerCase();
          return ['pdf', 'docx', 'txt', 'text'].includes(ext);
        });
        if (mounted) {
          setDocList(textDocs);
          if (textDocs.length > 0 && !selectedDocId) {
            setSelectedDocId(textDocs[0].id);
          }
        }
      } catch (err) {
        // Handle error
      }
    };
    loadDocuments();
    return () => {
      mounted = false;
    };
  }, [caseId]);

  // 2. Load selected document text and entities
  const loadDocumentText = useCallback(async (docId) => {
    if (!docId) return;
    setDocLoading(true);
    try {
      const res = await extractionApi.getText(docId);
      setDocData(res);
      setEntities(res.entities || []);
      setCurrentPageIdx(0);
      setSelectedEntityId(null);
    } catch (err) {
      setDocData(null);
      setEntities([]);
    } finally {
      setDocLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedDocId) {
      loadDocumentText(selectedDocId);
    }
  }, [selectedDocId, loadDocumentText]);

  // Run Extraction trigger
  const handleExtract = async () => {
    if (!selectedDocId) return;
    setActionLoading(true);
    try {
      await extractionApi.extract(selectedDocId);
      await loadDocumentText(selectedDocId);
    } catch (err) {
      alert(err.response?.data?.detail || 'Extraction failed');
    } finally {
      setActionLoading(false);
    }
  };

  // Approve / Reject Entity
  const handleDecision = async (extractedId, newStatus) => {
    setActionLoading(true);
    try {
      await extractionApi.update(extractedId, { status: newStatus });
      setEntities((prev) =>
        prev.map((e) => (e.id === extractedId ? { ...e, status: newStatus } : e))
      );
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update entity status');
    } finally {
      setActionLoading(false);
    }
  };

  // Bulk Approve
  const handleBulkApprove = async () => {
    setActionLoading(true);
    try {
      const res = await extractionApi.approveAll(caseId, 0.8);
      alert(`Bulk approved ${res.approved_count} entities with confidence ≥ 80%`);
      if (selectedDocId) {
        await loadDocumentText(selectedDocId);
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Bulk approval failed');
    } finally {
      setActionLoading(false);
    }
  };

  // Submit Manual Entity
  const handleManualAdd = async (e) => {
    e.preventDefault();
    if (!manualRaw.trim() || !manualNorm.trim()) return;

    setActionLoading(true);
    try {
      await extractionApi.createManual(caseId, {
        evidence_id: selectedDocId,
        entity_type: manualType,
        raw_value: manualRaw.trim(),
        normalized_value: manualNorm.trim(),
        page_or_paragraph: docData?.pages[currentPageIdx]?.page_or_paragraph || 'Page 1',
        confidence: 1.0,
      });
      setAddModalOpen(false);
      setManualRaw('');
      setManualNorm('');
      if (selectedDocId) {
        await loadDocumentText(selectedDocId);
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to add entity');
    } finally {
      setActionLoading(false);
    }
  };

  // Filter entities
  const filteredEntities = useMemo(() => {
    return entities.filter((e) => {
      const matchStatus =
        statusFilter === 'all' || e.status === statusFilter;
      const matchType =
        typeFilter === 'all' || e.entity_type === typeFilter;
      return matchStatus && matchType;
    });
  }, [entities, statusFilter, typeFilter]);

  // Current Page Data
  const currentPage = docData?.pages[currentPageIdx] || null;

  // Build Highlighted Page Text
  const renderedPageContent = useMemo(() => {
    if (!currentPage) return null;
    const pageText = currentPage.text;
    const pageOffset = currentPage.char_offset || 0;
    const pageEnd = pageOffset + pageText.length;

    // Filter entities located on this page
    const pageSpans = entities
      .filter((e) => e.char_span_start >= pageOffset && e.char_span_end <= pageEnd)
      .sort((a, b) => a.char_span_start - b.char_span_start);

    if (pageSpans.length === 0) {
      return <div className="whitespace-pre-wrap leading-relaxed">{pageText}</div>;
    }

    const elements = [];
    let lastIndex = 0;

    pageSpans.forEach((span, idx) => {
      const localStart = Math.max(0, span.char_span_start - pageOffset);
      const localEnd = Math.min(pageText.length, span.char_span_end - pageOffset);

      if (localStart > lastIndex) {
        elements.push(
          <span key={`text_${lastIndex}`}>
            {pageText.substring(lastIndex, localStart)}
          </span>
        );
      }

      const style = ENTITY_STYLES[span.entity_type] || ENTITY_STYLES.DEFAULT;
      const isSelected = selectedEntityId === span.id;

      elements.push(
        <mark
          key={`span_${span.id}_${idx}`}
          onClick={() => setSelectedEntityId(span.id)}
          className={`px-1 py-0.5 rounded cursor-pointer border transition-all ${style.bg} ${style.border} ${style.text} ${
            isSelected ? 'ring-2 ring-white font-bold' : 'hover:opacity-80'
          }`}
          title={`${span.entity_type} (${Math.round((span.confidence || 0) * 100)}%)`}
        >
          {pageText.substring(localStart, localEnd)}
        </mark>
      );

      lastIndex = Math.max(lastIndex, localEnd);
    });

    if (lastIndex < pageText.length) {
      elements.push(
        <span key={`tail_${lastIndex}`}>{pageText.substring(lastIndex)}</span>
      );
    }

    return <div className="whitespace-pre-wrap leading-relaxed">{elements}</div>;
  }, [currentPage, entities, selectedEntityId]);

  return (
    <div className="flex flex-col h-[750px] bg-[#0b1120] border border-[#1e293b] rounded-lg overflow-hidden">
      {/* 1. Header Toolbar */}
      <div className="bg-[#030712] border-b border-[#1e293b] p-3 flex flex-wrap items-center justify-between gap-3">
        {/* Document Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-400 font-mono">DOCUMENT:</label>
          <select
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
            className="bg-[#0b1120] border border-[#334155] focus:border-[#0284c7] px-3 py-1.5 rounded text-xs text-white max-w-xs focus:outline-none"
          >
            {docList.length === 0 && <option value="">No text/FIR documents in case</option>}
            {docList.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.original_name}
              </option>
            ))}
          </select>

          <button
            onClick={handleExtract}
            disabled={actionLoading || !selectedDocId}
            className="px-3 py-1.5 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded disabled:opacity-50 transition-colors"
          >
            {actionLoading ? 'Analyzing...' : 'Extract Entities'}
          </button>
        </div>

        {/* Global Review Actions */}
        {!isViewer && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAddModalOpen(true)}
              disabled={!selectedDocId}
              className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-white text-xs font-medium rounded border border-[#334155] disabled:opacity-50 transition-colors"
            >
              + Add Entity
            </button>
            <button
              onClick={handleBulkApprove}
              disabled={actionLoading || entities.length === 0}
              className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold rounded disabled:opacity-50 transition-colors"
            >
              Approve All (≥ 80%)
            </button>
          </div>
        )}
      </div>

      {/* Warning Notice (if Devanagari partially ignored) */}
      {docData?.warning && (
        <div className="bg-amber-950/40 border-b border-amber-900 px-4 py-1.5 text-xs text-amber-300 font-mono flex items-center justify-between">
          <span>⚠️ {docData.warning}</span>
          <span className="text-[10px] text-amber-400">Latin-script portions analyzed</span>
        </div>
      )}

      {/* 2. Split Workspace (Document Text vs Entity Queue) */}
      <div className="relative flex-1 flex overflow-hidden">
        {/* Left Pane: Interactive Document Reader */}
        <div className="flex-1 flex flex-col bg-[#070b14] border-r border-[#1e293b] overflow-hidden">
          {/* Page Bar */}
          <div className="bg-[#030712] border-b border-[#1e293b] px-4 py-2 flex items-center justify-between text-xs">
            <span className="font-mono text-slate-400">
              {currentPage ? currentPage.page_or_paragraph : 'No document selected'}
            </span>
            {docData?.pages && docData.pages.length > 1 && (
              <div className="flex items-center gap-2">
                <button
                  disabled={currentPageIdx === 0}
                  onClick={() => setCurrentPageIdx((p) => Math.max(0, p - 1))}
                  className="px-2 py-0.5 bg-[#1e293b] hover:bg-[#334155] text-white text-xs rounded disabled:opacity-40"
                >
                  Previous
                </button>
                <span className="text-slate-400 font-mono text-[11px]">
                  {currentPageIdx + 1} / {docData.pages.length}
                </span>
                <button
                  disabled={currentPageIdx >= docData.pages.length - 1}
                  onClick={() => setCurrentPageIdx((p) => Math.min(docData.pages.length - 1, p + 1))}
                  className="px-2 py-0.5 bg-[#1e293b] hover:bg-[#334155] text-white text-xs rounded disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            )}
          </div>

          {/* Document Content View */}
          <div className="flex-1 p-6 overflow-y-auto font-mono text-xs text-slate-300 leading-relaxed select-text">
            {docLoading ? (
              <div className="py-20 text-center text-slate-500 text-xs">
                <div className="inline-block animate-spin w-6 h-6 border-2 border-slate-600 border-t-[#38bdf8] rounded-full mb-2" />
                <p>Loading document text...</p>
              </div>
            ) : docData?.full_text ? (
              renderedPageContent
            ) : (
              <div className="py-20 text-center text-slate-500 text-xs">
                Select a text document and click 'Extract Entities' to begin review.
              </div>
            )}
          </div>
        </div>

        {/* Right Pane: Extracted Entities Queue */}
        <div className="w-[450px] bg-[#030712] flex flex-col justify-between overflow-hidden shadow-2xl">
          {/* Filter Bar */}
          <div className="p-3 border-b border-[#1e293b] flex items-center gap-2 flex-wrap text-xs bg-[#0b1120]">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-[#030712] border border-[#334155] px-2 py-1 rounded text-[11px] text-white"
            >
              <option value="all">All Status ({entities.length})</option>
              <option value="pending_review">Pending Review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>

            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-[#030712] border border-[#334155] px-2 py-1 rounded text-[11px] text-white"
            >
              <option value="all">All Entity Types</option>
              <option value="PERSON">PERSON</option>
              <option value="PHONE">PHONE</option>
              <option value="BANK_ACCOUNT">BANK_ACCOUNT</option>
              <option value="ACCOUNT_SUFFIX">ACCOUNT_SUFFIX</option>
              <option value="VEHICLE">VEHICLE</option>
              <option value="AMOUNT">AMOUNT</option>
              <option value="FIR">FIR</option>
              <option value="POLICE_STATION">POLICE_STATION</option>
              <option value="RELATIONSHIP">RELATIONSHIP</option>
            </select>
          </div>

          {/* Queue List */}
          <div className="flex-1 p-3 overflow-y-auto space-y-2.5">
            {filteredEntities.length === 0 ? (
              <div className="py-16 text-center text-xs text-slate-500">
                No extracted entities matching active filters.
              </div>
            ) : (
              filteredEntities.map((ent) => {
                const style = ENTITY_STYLES[ent.entity_type] || ENTITY_STYLES.DEFAULT;
                const isSelected = selectedEntityId === ent.id;

                return (
                  <div
                    key={ent.id}
                    onClick={() => setSelectedEntityId(ent.id)}
                    className={`p-3 bg-[#0b1120] border rounded text-xs transition-all ${
                      isSelected
                        ? 'border-[#0284c7] ring-1 ring-[#0284c7]'
                        : 'border-[#1e293b] hover:border-[#334155]'
                    }`}
                  >
                    {/* Header badge & confidence */}
                    <div className="flex items-center justify-between mb-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold ${style.badge}`}>
                        {ent.entity_type}
                      </span>
                      <div className="flex items-center gap-1.5 font-mono text-[10px]">
                        <span className="text-slate-400">
                          {Math.round((ent.confidence || 0) * 100)}% Conf
                        </span>
                        <span
                          className={`px-1 rounded uppercase ${
                            ent.status === 'approved'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                              : ent.status === 'rejected'
                              ? 'bg-rose-950 text-rose-400 border border-rose-800'
                              : 'bg-amber-950 text-amber-400 border border-amber-800'
                          }`}
                        >
                          {ent.status}
                        </span>
                      </div>
                    </div>

                    {/* Value */}
                    <div className="space-y-0.5">
                      <div className="font-semibold text-white break-words">
                        {ent.raw_value}
                      </div>
                      <div className="font-mono text-[11px] text-slate-400 break-words">
                        Norm: <code className="text-[#38bdf8]">{ent.normalized_value}</code>
                      </div>
                    </div>

                    {/* Source reference */}
                    <div className="mt-2 pt-2 border-t border-[#1e293b] flex items-center justify-between text-[10px] text-slate-500 font-mono">
                      <span>{ent.page_or_paragraph}</span>
                      <span>Method: {ent.method}</span>
                    </div>

                    {/* Action buttons */}
                    {!isViewer && (
                      <div className="mt-2.5 flex items-center gap-1.5 justify-end">
                        {ent.status !== 'approved' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDecision(ent.id, 'approved');
                            }}
                            className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-600 text-white text-[11px] font-semibold rounded transition-colors"
                          >
                            Approve
                          </button>
                        )}
                        {ent.status !== 'rejected' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDecision(ent.id, 'rejected');
                            }}
                            className="px-2.5 py-1 bg-rose-900/60 hover:bg-rose-800 text-rose-200 text-[11px] rounded border border-rose-800 transition-colors"
                          >
                            Reject
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Queue Footer */}
          <div className="p-3 bg-[#0b1120] border-t border-[#1e293b] text-[10px] text-slate-500 font-mono flex items-center justify-between">
            <span>Section 63 BSA 2023 Compliant Extraction</span>
            <span>{filteredEntities.length} entities displayed</span>
          </div>
        </div>
      </div>

      {/* 3. Manual Add Entity Modal */}
      {addModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] mb-4">
              <div>
                <h3 className="text-sm font-bold text-white">Add Entity Manually</h3>
                <p className="text-xs text-slate-400">Tag uncaptured entity from document narrative</p>
              </div>
              <button
                onClick={() => setAddModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs font-mono"
              >
                [X]
              </button>
            </div>

            <form onSubmit={handleManualAdd} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Entity Category
                </label>
                <select
                  value={manualType}
                  onChange={(e) => setManualType(e.target.value)}
                  className="w-full bg-[#030712] border border-[#334155] px-3 py-2 rounded text-xs text-white focus:outline-none"
                >
                  <option value="PERSON">PERSON (Subject / Person of Interest / Witness)</option>
                  <option value="PHONE">PHONE (Mobile / Contact)</option>
                  <option value="BANK_ACCOUNT">BANK_ACCOUNT (Account Number)</option>
                  <option value="VEHICLE">VEHICLE (Registration Number)</option>
                  <option value="FIR">FIR (Case / FIR Number)</option>
                  <option value="POLICE_STATION">POLICE_STATION (Station Name)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Raw Text in Document
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Shri Ramesh Kumar"
                  value={manualRaw}
                  onChange={(e) => {
                    setManualRaw(e.target.value);
                    if (!manualNorm) setManualNorm(e.target.value.toLowerCase().trim());
                  }}
                  className="w-full bg-[#030712] border border-[#334155] focus:border-[#0284c7] px-3 py-2 rounded text-xs text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Normalized Value
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. ramesh kumar"
                  value={manualNorm}
                  onChange={(e) => setManualNorm(e.target.value)}
                  className="w-full bg-[#030712] border border-[#334155] focus:border-[#0284c7] px-3 py-2 rounded text-xs text-white focus:outline-none font-mono"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-[#1e293b]">
                <button
                  type="button"
                  onClick={() => setAddModalOpen(false)}
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 text-xs rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-1.5 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded disabled:opacity-50"
                >
                  {actionLoading ? 'Saving...' : 'Add & Approve'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
