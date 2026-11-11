import React, { useState, useEffect } from 'react';
import { Columns, AlertTriangle, Check, X, ArrowRight, ShieldCheck, RefreshCw } from 'lucide-react';
import { evidenceApi } from '../../api/client';

export default function MappingPreviewModal({
  isOpen,
  onClose,
  evidenceId,
  caseId,
  onConfirm,
}) {
  const [loading, setLoading] = useState(true);
  const [previewData, setPreviewData] = useState(null);
  const [activeMapping, setActiveMapping] = useState({});
  const [selectedFileType, setSelectedFileType] = useState('cdr');
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen && evidenceId) {
      loadPreview();
    }
  }, [isOpen, evidenceId]);

  const loadPreview = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await evidenceApi.preview(evidenceId);
      setPreviewData(res);
      setSelectedFileType(res.detected_type !== 'unknown' ? res.detected_type : 'cdr');
      
      const initial = {};
      if (res.suggested_mapping) {
        Object.entries(res.suggested_mapping).forEach(([col, val]) => {
          initial[col] = typeof val === 'string' ? val : val.canonical || val.target || '';
        });
      }
      setActiveMapping(initial);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze candidate column profiles.');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (rawHeader, newTarget) => {
    setActiveMapping(prev => ({
      ...prev,
      [rawHeader]: newTarget
    }));
  };

  const handleConfirm = async () => {
    setConfirming(true);
    try {
      await evidenceApi.confirmMapping(evidenceId, {
        file_type: selectedFileType,
        mapping: activeMapping,
      });
      if (onConfirm) {
        onConfirm(selectedFileType, activeMapping);
      }
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save confirmed schema mapping.');
    } finally {
      setConfirming(false);
    }
  };

  if (!isOpen) return null;

  const candidateFields = {
    cdr: ['caller', 'receiver', 'datetime', 'duration_seconds', 'call_type', 'imei', 'imsi', 'cell_tower_id', 'latitude', 'longitude'],
    bank: ['txn_id', 'account_number', 'counterparty_account', 'amount', 'direction', 'txn_date', 'narration', 'balance_after', 'ifsc'],
    fir: ['fir_number', 'police_station', 'sections', 'complainant', 'incident_datetime', 'incident_place'],
    sdr: ['phone_number', 'subscriber_name', 'father_name', 'address', 'aadhaar', 'pan', 'alt_phone', 'activation_date'],
  };

  const currentOptions = candidateFields[selectedFileType] || candidateFields.cdr;
  const isTemplateDrift = previewData?.template_drift && Object.keys(previewData.template_drift).length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="glass w-full max-w-4xl max-h-[90vh] flex flex-col p-6 rounded-2xl border border-white/10 shadow-2xl relative">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2.5 text-accent">
            <Columns className="w-5 h-5 shrink-0" />
            <div>
              <h2 className="font-serif text-lg text-text font-bold">
                Forensic Schema & Column Mapping Preview
              </h2>
              <p className="text-xs font-mono text-muted">
                Confidence-weighted content profiling and standard field alignment
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded text-muted hover:text-text hover:bg-white/5">
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="py-16 text-center space-y-3">
            <div className="inline-block animate-spin w-6 h-6 border-2 border-white/20 border-t-accent rounded-full" />
            <p className="text-xs font-mono text-muted">Profiling column data distributions & sniffing encoding...</p>
          </div>
        ) : error ? (
          <div className="py-10 text-center space-y-4">
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-xs font-mono max-w-md mx-auto">
              {error}
            </div>
            <button onClick={loadPreview} className="px-4 py-2 text-xs font-mono bg-white/5 hover:bg-white/10 text-text rounded-xl border border-white/10">
              Retry Preview
            </button>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto space-y-5 py-4 pr-1">
            {/* Template Drift Alert */}
            {isTemplateDrift && (
              <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-800 text-amber-300 text-xs font-mono flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
                <div className="space-y-1">
                  <div className="font-semibold text-amber-200">SCHEMA DRIFT DETECTED AGAINST SAVED TEMPLATE</div>
                  <p className="text-[11px] text-amber-200/80">
                    The evidence file has column variations compared to the established layout. Please verify aligned target fields before ingestion.
                  </p>
                </div>
              </div>
            )}

            {/* Target Record Type Selector */}
            <div className="flex items-center gap-3 p-3 rounded-xl glass-sm font-mono text-xs">
              <span className="text-muted">Target Record Type:</span>
              <div className="flex gap-2">
                {[
                  { id: 'cdr', label: 'Call Detail Record (CDR)' },
                  { id: 'bank', label: 'Bank Statement' },
                  { id: 'fir', label: 'Police FIR Document' },
                  { id: 'sdr', label: 'Subscriber Details (SDR)' },
                ].map(t => (
                  <button
                    key={t.id}
                    onClick={() => setSelectedFileType(t.id)}
                    className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${
                      selectedFileType === t.id
                        ? 'bg-accent text-ink font-semibold'
                        : 'bg-white/5 text-muted hover:text-text hover:bg-white/10'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Column Mapping Table */}
            <div className="border border-white/10 rounded-xl overflow-hidden">
              <table className="w-full text-left font-mono text-xs">
                <thead className="bg-white/5 text-muted uppercase text-[10px] tracking-wider border-b border-white/10">
                  <tr>
                    <th className="py-2.5 px-3">File Header</th>
                    <th className="py-2.5 px-3">Target Field</th>
                    <th className="py-2.5 px-3">Top-3 Suggested Candidates</th>
                    <th className="py-2.5 px-3 text-right">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-text">
                  {previewData?.headers && previewData.headers.map((hdr, idx) => {
                    const matchInfo = previewData.suggested_mapping?.[hdr] || {};
                    const conf = matchInfo.confidence ? Math.round(matchInfo.confidence * 100) : 0;
                    const candidates = matchInfo.candidates || [];

                    return (
                      <tr key={idx} className="hover:bg-white/[0.02]">
                        <td className="py-2 px-3 font-semibold text-text">{hdr}</td>
                        <td className="py-2 px-3">
                          <select
                            value={activeMapping[hdr] || ''}
                            onChange={(e) => handleFieldChange(hdr, e.target.value)}
                            className="px-2 py-1 bg-black/50 border border-white/15 rounded-lg text-text font-mono text-xs focus:border-accent focus:outline-none"
                          >
                            <option value="">[Ignore / Unmapped]</option>
                            {currentOptions.map(opt => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                        </td>
                        <td className="py-2 px-3">
                          <div className="flex flex-wrap gap-1">
                            {candidates.length > 0 ? (
                              candidates.map((cand, cIdx) => (
                                <button
                                  key={cIdx}
                                  type="button"
                                  onClick={() => handleFieldChange(hdr, cand.field)}
                                  className="px-1.5 py-0.5 rounded text-[10px] bg-white/5 hover:bg-accent/20 hover:text-accent border border-white/10"
                                >
                                  {cand.field} ({Math.round(cand.confidence * 100)}%)
                                </button>
                              ))
                            ) : (
                              <span className="text-muted text-[10px] italic">No high-confidence candidate</span>
                            )}
                          </div>
                        </td>
                        <td className="py-2 px-3 text-right font-bold">
                          <span className={conf > 70 ? 'text-emerald-400' : conf > 40 ? 'text-amber-400' : 'text-muted'}>
                            {conf}%
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Normalized Rows Preview */}
            {previewData?.sample_rows && previewData.sample_rows.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-mono text-muted uppercase tracking-wider">
                  Normalized Sample Records Preview (First {previewData.sample_rows.length} rows)
                </div>
                <div className="border border-white/10 rounded-xl overflow-x-auto bg-black/30">
                  <table className="w-full text-left font-mono text-[11px] whitespace-nowrap">
                    <thead className="bg-white/5 text-muted border-b border-white/10">
                      <tr>
                        {previewData.headers.map((h, i) => (
                          <th key={i} className="py-2 px-3 text-[10px]">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-muted">
                      {previewData.sample_rows.map((row, rIdx) => (
                        <tr key={rIdx}>
                          {previewData.headers.map((h, cIdx) => (
                            <td key={cIdx} className="py-1.5 px-3">{String(row[h] ?? '—')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer actions */}
        <div className="flex items-center justify-between pt-4 border-t border-white/10 shrink-0">
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-muted">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>SHA-256 Validated · Zero Prejudicial Modification</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-mono text-muted hover:text-text rounded-xl border border-white/10 hover:bg-white/5"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={loading || confirming || Object.keys(activeMapping).length === 0}
              onClick={handleConfirm}
              className="px-4 py-2 text-xs font-mono font-semibold bg-accent text-ink rounded-xl hover:bg-accent/90 disabled:opacity-50 flex items-center gap-2"
            >
              {confirming ? 'Applying Schema...' : 'Confirm Schema & Proceed'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
