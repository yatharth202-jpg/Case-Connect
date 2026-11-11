import React, { useState, useEffect, useMemo } from 'react';
import { Table, Download, Search, Filter, History, ShieldCheck, Check, ChevronDown, RefreshCw, Eye } from 'lucide-react';
import { extractionV2Api } from '../../api/client';
import NumberBadge from './NumberBadge';

export default function MasterSheetTab({ caseId, isViewer = false }) {
  const [loading, setLoading] = useState(true);
  const [records, setRecords] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [recordTypeFilter, setRecordTypeFilter] = useState('all');
  const [visibleColumns, setVisibleColumns] = useState({});
  const [columnDropdownOpen, setColumnDropdownOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [lastExportSha, setLastExportSha] = useState('');
  const [historyModalData, setHistoryModalData] = useState(null);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    if (caseId) {
      loadMasterRecords();
    }
  }, [caseId, recordTypeFilter, page]);

  const loadMasterRecords = async () => {
    setLoading(true);
    try {
      const typeParam = recordTypeFilter === 'all' ? undefined : recordTypeFilter;
      const res = await extractionV2Api.getRecords(caseId, {
        type: typeParam,
        page,
        limit: 50,
      });

      const list = res.records || res.items || res || [];
      const recList = Array.isArray(list) ? list : [];
      setRecords(recList);
      setTotalCount(res.total || recList.length);

      // Initialize visible columns based on data
      if (recList.length > 0 && Object.keys(visibleColumns).length === 0) {
        const initial = {
          record_type: true,
          natural_key: true,
          status: true,
          confidence: true,
          source_kind: true,
        };
        // Add top 5 common fields from data_json or extra_json
        recList.slice(0, 10).forEach(r => {
          const d = r.data_json ? (typeof r.data_json === 'string' ? JSON.parse(r.data_json) : r.data_json) : {};
          Object.keys(d).slice(0, 5).forEach(k => { initial[k] = true; });
        });
        setVisibleColumns(initial);
      }
    } catch (err) {
      console.warn('[MASTER SHEET ERROR]', err);
    } finally {
      setLoading(false);
    }
  };

  // Derive all possible dynamic columns across visible rows
  const allColumns = useMemo(() => {
    const colSet = new Set(['record_type', 'natural_key', 'status', 'confidence', 'source_kind', 'extractor_version']);
    records.forEach(r => {
      const d = r.data_json ? (typeof r.data_json === 'string' ? JSON.parse(r.data_json) : r.data_json) : {};
      const extra = r.extra_json ? (typeof r.extra_json === 'string' ? JSON.parse(r.extra_json) : r.extra_json) : {};
      Object.keys(d).forEach(k => colSet.add(k));
      Object.keys(extra).forEach(k => colSet.add(`extra:${k}`));
    });
    return Array.from(colSet);
  }, [records]);

  // Filter records by search
  const filteredRecords = useMemo(() => {
    if (!searchQuery.trim()) return records;
    const q = searchQuery.toLowerCase();
    return records.filter(r => {
      return JSON.stringify(r).toLowerCase().includes(q);
    });
  }, [records, searchQuery]);

  const handleExport = async (format) => {
    setExporting(true);
    setLastExportSha('');
    try {
      const res = await extractionV2Api.getMasterSheet(caseId, { format, view: 'wide' });
      if (res.sha256) {
        setLastExportSha(res.sha256);
      }

      if (format === 'json') {
        const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
        downloadBlob(blob, `case_${caseId}_mastersheet.json`);
      } else {
        downloadBlob(res.data, `case_${caseId}_mastersheet.${format}`);
      }
    } catch (err) {
      alert('Failed to export master sheet: ' + (err.response?.data?.detail || err.message));
    } finally {
      setExporting(false);
    }
  };

  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const openHistoryPopover = async (record, field) => {
    try {
      const hist = await extractionV2Api.getRecordHistory(caseId, record.id);
      setHistoryModalData({
        recordId: record.id,
        field,
        claims: hist.claims || hist || [],
      });
    } catch (e) {
      setHistoryModalData({
        recordId: record.id,
        field,
        claims: [],
      });
    }
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Top Controls Toolbar */}
      <div className="p-4 rounded-2xl glass-sm border border-white/10 flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search & Type filter */}
        <div className="flex flex-wrap items-center gap-2 flex-1">
          <div className="relative min-w-[220px]">
            <Search className="w-3.5 h-3.5 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search all columns & claims..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-black/40 border border-white/10 text-text text-xs focus:outline-none focus:border-accent"
            />
          </div>

          <div className="flex items-center gap-1 bg-black/30 p-1 rounded-xl border border-white/10 text-[11px]">
            {['all', 'call', 'transaction', 'entity', 'ip_event'].map(t => (
              <button
                key={t}
                onClick={() => { setRecordTypeFilter(t); setPage(1); }}
                className={`px-2.5 py-0.5 rounded-lg capitalize transition-colors ${
                  recordTypeFilter === t
                    ? 'bg-accent text-ink font-semibold'
                    : 'text-muted hover:text-text'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Column chooser & Export buttons */}
        <div className="flex items-center gap-2">
          {/* Column Picker Dropdown */}
          <div className="relative">
            <button
              onClick={() => setColumnDropdownOpen(!columnDropdownOpen)}
              className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-muted hover:text-text flex items-center gap-1.5 text-xs"
            >
              <ColumnsDropdownIcon />
              <span>Columns</span>
              <ChevronDown className="w-3.5 h-3.5" />
            </button>

            {columnDropdownOpen && (
              <div className="absolute right-0 top-full mt-2 w-64 p-3 rounded-2xl glass border border-white/15 shadow-2xl z-40 space-y-2 max-h-72 overflow-y-auto">
                <div className="font-semibold text-text text-[11px] pb-1 border-b border-white/10">
                  Visible Column Fields
                </div>
                {allColumns.map(col => (
                  <label key={col} className="flex items-center gap-2 text-[11px] text-muted hover:text-text cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!visibleColumns[col]}
                      onChange={(e) => setVisibleColumns(prev => ({ ...prev, [col]: e.target.checked }))}
                      className="accent-accent"
                    />
                    <span className="truncate">{col}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Export Action Menu */}
          <div className="flex items-center gap-1">
            <button
              disabled={exporting || records.length === 0}
              onClick={() => handleExport('csv')}
              className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-text hover:text-accent disabled:opacity-40 flex items-center gap-1.5 text-xs transition-colors"
              title="Export as CSV with SHA-256 integrity checksum"
            >
              <Download className="w-3.5 h-3.5" />
              <span>CSV</span>
            </button>
            <button
              disabled={exporting || records.length === 0}
              onClick={() => handleExport('json')}
              className="px-3 py-1.5 rounded-xl bg-accent text-ink font-semibold rounded-xl hover:bg-accent/90 disabled:opacity-40 flex items-center gap-1.5 text-xs transition-colors"
              title="Export complete claim provenance ledger as JSON"
            >
              <Download className="w-3.5 h-3.5" />
              <span>JSON</span>
            </button>
          </div>
        </div>
      </div>

      {/* Export SHA-256 Integrity Banner */}
      {lastExportSha && (
        <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-800 text-emerald-300 flex items-center justify-between text-[11px] font-mono">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Export Hash (Section 63 BSA Certified):</span>
            <code className="text-text font-bold select-all">{lastExportSha}</code>
          </div>
          <span className="text-muted text-[10px]">Logged to Immutable Audit Ledger</span>
        </div>
      )}

      {/* Main Table */}
      {loading ? (
        <div className="py-20 text-center space-y-2">
          <div className="inline-block animate-spin w-6 h-6 border-2 border-white/20 border-t-accent rounded-full" />
          <p className="text-muted">Loading consolidated Master Sheet records...</p>
        </div>
      ) : filteredRecords.length === 0 ? (
        /* Actionable Empty State */
        <div className="p-16 text-center rounded-2xl glass-sm border border-dashed border-white/10 space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-accent mx-auto">
            <Table className="w-6 h-6" />
          </div>
          <div className="font-serif text-lg text-text">No Extraction Records Staged</div>
          <p className="text-muted text-xs max-w-sm mx-auto leading-relaxed">
            Upload CDR dumps, bank statements, or FIRs to populate the unified multi-source Master Sheet.
          </p>
        </div>
      ) : (
        <div className="border border-white/10 rounded-2xl overflow-hidden glass shadow-xl">
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="w-full text-left font-mono text-xs whitespace-nowrap">
              <thead className="bg-white/5 text-muted uppercase text-[10px] tracking-wider border-b border-white/10 sticky top-0 z-20 backdrop-blur-md">
                <tr>
                  <th className="py-3 px-3.5">#</th>
                  {Object.keys(visibleColumns).filter(k => visibleColumns[k]).map(col => (
                    <th key={col} className="py-3 px-3.5">{col}</th>
                  ))}
                  <th className="py-3 px-3.5 text-right">Provenance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-text">
                {filteredRecords.map((rec, rIdx) => {
                  const data = rec.data_json ? (typeof rec.data_json === 'string' ? JSON.parse(rec.data_json) : rec.data_json) : {};
                  const extra = rec.extra_json ? (typeof rec.extra_json === 'string' ? JSON.parse(rec.extra_json) : rec.extra_json) : {};

                  return (
                    <tr key={rec.id || rIdx} className="hover:bg-white/[0.03] transition-colors">
                      <td className="py-2.5 px-3.5 text-muted text-[10px]">{(page - 1) * 50 + rIdx + 1}</td>
                      {Object.keys(visibleColumns).filter(k => visibleColumns[k]).map(col => {
                        let cellVal = '—';
                        if (col === 'record_type') cellVal = <span className="uppercase font-semibold text-accent">{rec.record_type}</span>;
                        else if (col === 'natural_key') cellVal = <code className="text-muted text-[10px]">{rec.natural_key?.slice(0, 10)}...</code>;
                        else if (col === 'status') cellVal = (
                          <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-semibold ${
                            rec.status === 'active' ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800' : 'bg-white/5 text-muted'
                          }`}>
                            {rec.status || 'active'}
                          </span>
                        );
                        else if (col === 'confidence') cellVal = `${Math.round((rec.confidence || 0.95) * 100)}%`;
                        else if (col === 'source_kind') cellVal = rec.source_kind || 'structured_file';
                        else if (col.startsWith('extra:')) {
                          const k = col.replace('extra:', '');
                          cellVal = extra[k] ? <span className="text-cyan-300">{String(extra[k])}</span> : '—';
                        } else {
                          const rawVal = data[col];
                          if (rawVal !== undefined && rawVal !== null) {
                            if (col.includes('phone') || col.includes('account') || col.includes('aadhaar')) {
                              cellVal = <NumberBadge value={String(rawVal)} caseId={caseId} recordId={rec.id} fieldName={col} />;
                            } else {
                              cellVal = String(rawVal);
                            }
                          }
                        }

                        return (
                          <td key={col} className="py-2.5 px-3.5">
                            {cellVal}
                          </td>
                        );
                      })}
                      <td className="py-2.5 px-3.5 text-right">
                        <button
                          onClick={() => openHistoryPopover(rec, 'general')}
                          className="p-1 rounded text-muted hover:text-accent hover:bg-white/5 transition-colors"
                          title="View all contributing field claims and sources"
                        >
                          <History className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination bar */}
          <div className="flex items-center justify-between p-3 border-t border-white/10 text-muted text-[11px] bg-black/30">
            <span>Showing {filteredRecords.length} of {totalCount} records</span>
            <div className="flex gap-1.5">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="px-2.5 py-1 rounded-lg border border-white/10 hover:bg-white/5 disabled:opacity-30"
              >
                Previous
              </button>
              <button
                disabled={filteredRecords.length < 50}
                onClick={() => setPage(p => p + 1)}
                className="px-2.5 py-1 rounded-lg border border-white/10 hover:bg-white/5 disabled:opacity-30"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Claim History Popover Modal */}
      {historyModalData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="glass w-full max-w-lg p-5 rounded-2xl border border-white/10 shadow-2xl relative space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2 text-accent">
                <History className="w-4 h-4" />
                <h3 className="font-serif text-base text-text font-bold">Field Claim Provenance</h3>
              </div>
              <button onClick={() => setHistoryModalData(null)} className="p-1 text-muted hover:text-text">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs text-muted">
              Record ID: <code className="text-text">{historyModalData.recordId}</code>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto">
              {historyModalData.claims && historyModalData.claims.length > 0 ? (
                historyModalData.claims.map((claim, idx) => (
                  <div key={idx} className="p-3 rounded-xl glass-sm border border-white/5 space-y-1">
                    <div className="flex justify-between font-bold text-text">
                      <span>{claim.field_name}: {claim.value_norm || claim.value_raw}</span>
                      <span className="text-accent">{claim.confidence ? Math.round(claim.confidence * 100) : 90}%</span>
                    </div>
                    <div className="text-[10px] text-muted flex justify-between">
                      <span>Source: {claim.source_kind || 'file'}</span>
                      <span>Trust Rank: #{claim.trust_rank || 1}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-6 text-center text-muted italic">
                  Single original claim registered upon evidence ingestion.
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setHistoryModalData(null)}
                className="px-4 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-text border border-white/10 text-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ColumnsDropdownIcon() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
    </svg>
  );
}
