import React, { useState } from 'react';
import {
  FileSpreadsheet,
  Download,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Filter,
  Loader2,
  Calendar,
  Layers,
} from 'lucide-react';
import { exportApi } from '../api/client';

export default function ExportPanel({ caseId, caseNumber }) {
  const [selectedTables, setSelectedTables] = useState([
    'raw_rows',
    'call_records',
    'transactions',
    'ip_events',
    'rejected_rows',
    'entities',
    'top_leads',
    'graph_nodes',
    'graph_edges',
  ]);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [useBackground, setUseBackground] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(null);
  const [exportError, setExportError] = useState(null);

  const availableTables = [
    { id: 'raw_rows', label: 'Lossless Raw Rows', desc: 'Pre-validation cell text & unmapped attributes' },
    { id: 'call_records', label: 'Call Records (CDR)', desc: 'Caller, receiver, cell tower, IMEI, durations' },
    { id: 'transactions', label: 'Transactions', desc: 'Financial records with integer paise & INR string' },
    { id: 'ip_events', label: 'IP Events', desc: 'IP access logs & protocol session records' },
    { id: 'rejected_rows', label: 'Rejected Rows', desc: 'Malformed or invalid records with failure reasons' },
    { id: 'entities', label: 'Entities', desc: 'Resolved phone, account, person, and device nodes' },
    { id: 'top_leads', label: 'Top-5 Leads', desc: 'Prioritised investigative leads with score breakdown' },
    { id: 'graph_nodes', label: 'Graph Nodes', desc: 'Topological node projection with properties' },
    { id: 'graph_edges', label: 'Graph Edges', desc: 'Forensic relationship links with weights & totals' },
  ];

  const handleToggleTable = (id) => {
    setSelectedTables((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedTables.length === availableTables.length) {
      setSelectedTables([]);
    } else {
      setSelectedTables(availableTables.map((t) => t.id));
    }
  };

  const handleTriggerExport = async () => {
    if (selectedTables.length === 0) {
      setExportError('Please select at least one table to include in the export.');
      return;
    }

    setIsExporting(true);
    setExportError(null);
    setExportSuccess(null);

    try {
      const response = await exportApi.downloadExcel(caseId, {
        tables: selectedTables,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        background: useBackground,
      });

      if (useBackground && response.data && response.data.job_id) {
        setExportSuccess({
          message: 'Background export job dispatched successfully.',
          jobId: response.data.job_id,
          downloadUrl: response.data.download_url,
        });
      } else {
        // Blob download
        const blob = new Blob([response.data], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const filename = `case_${caseNumber || caseId.slice(0, 8)}_forensic_dossier.xlsx`;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);

        const sha256 = response.headers?.['x-case-integrity-sha256'] || 'Generated';
        setExportSuccess({
          message: 'Forensic Excel dossier downloaded successfully.',
          sha256,
          filename,
        });
      }
    } catch (err) {
      const errMsg =
        err.response?.data?.detail || err.message || 'Excel export request failed.';
      setExportError(errMsg);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400">
            <FileSpreadsheet className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold tracking-wide text-white flex items-center gap-2">
              Forensic Excel Export Dossier
              <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono">
                Section 63 BSA 2023
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Multi-sheet streaming export (.xlsx) preserving all lossless raw data, staged records, entities, and graph projections.
            </p>
          </div>
        </div>

        <button
          onClick={handleTriggerExport}
          disabled={isExporting || selectedTables.length === 0}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-md transition shadow-sm"
        >
          {isExporting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating Dossier...
            </>
          ) : (
            <>
              <Download className="w-4 h-4" />
              Export to Excel (.xlsx)
            </>
          )}
        </button>
      </div>

      {/* Compliance Notice */}
      <div className="flex items-start gap-3 p-3.5 bg-slate-950/70 border border-slate-800 rounded-md text-xs text-slate-300">
        <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-medium text-slate-200">
            Cryptographic Chain of Custody & Formula Injection Safety
          </p>
          <p className="text-slate-400 leading-relaxed">
            All text tokens starting with <code className="text-amber-400 font-mono">=</code>,{' '}
            <code className="text-amber-400 font-mono">+</code>,{' '}
            <code className="text-amber-400 font-mono">-</code>, or{' '}
            <code className="text-amber-400 font-mono">@</code> are sanitized with a single-quote prefix to prevent DDE code execution. Financial amounts are recorded strictly as 64-bit integer paise alongside formatted INR strings (zero floating-point numbers).
          </p>
        </div>
      </div>

      {/* Filter and Table Selection */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Table selection */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-slate-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-slate-400" />
              Select Sheets to Include ({selectedTables.length} / {availableTables.length})
            </label>
            <button
              onClick={handleSelectAll}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-medium underline-offset-2 hover:underline"
            >
              {selectedTables.length === availableTables.length ? 'Deselect All' : 'Select All'}
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {availableTables.map((t) => {
              const checked = selectedTables.includes(t.id);
              return (
                <div
                  key={t.id}
                  onClick={() => handleToggleTable(t.id)}
                  className={`cursor-pointer p-3 rounded-md border text-left transition flex items-start gap-3 ${
                    checked
                      ? 'bg-slate-800/80 border-emerald-500/40 text-white'
                      : 'bg-slate-950/50 border-slate-800/70 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {}}
                    className="mt-0.5 rounded border-slate-700 bg-slate-900 text-emerald-600 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                  />
                  <div>
                    <p className="text-xs font-semibold text-slate-200">{t.label}</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">{t.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Date & Job Options */}
        <div className="space-y-4 bg-slate-950/40 p-4 rounded-md border border-slate-800">
          <h3 className="text-sm font-medium text-slate-200 flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            Filters & Processing Scope
          </h3>

          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                From Date (ISO / YYYY-MM-DD)
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                To Date (ISO / YYYY-MM-DD)
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="pt-2 border-t border-slate-800">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={useBackground}
                  onChange={(e) => setUseBackground(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-900 text-emerald-600 focus:ring-0"
                />
                Run as Background Job (for &gt; 50,000 rows)
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Success Banner */}
      {exportSuccess && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-md flex items-start gap-3 text-emerald-300 text-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold">{exportSuccess.message}</p>
            {exportSuccess.filename && (
              <p className="text-emerald-400/80 font-mono">File: {exportSuccess.filename}</p>
            )}
            {exportSuccess.sha256 && (
              <p className="text-emerald-400/80 font-mono break-all">
                SHA-256: {exportSuccess.sha256}
              </p>
            )}
            {exportSuccess.downloadUrl && (
              <a
                href={exportSuccess.downloadUrl}
                className="inline-block mt-1 text-emerald-400 underline font-medium"
              >
                Download Completed Background File
              </a>
            )}
          </div>
        </div>
      )}

      {/* Error Banner */}
      {exportError && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-md flex items-start gap-3 text-red-300 text-xs">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <p>{exportError}</p>
        </div>
      )}
    </div>
  );
}
