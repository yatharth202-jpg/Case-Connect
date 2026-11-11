import React, { useState } from 'react';
import { ShieldAlert, Lock, CheckCircle, X, AlertCircle } from 'lucide-react';
import { extractionV2Api } from '../../api/client';

export default function RevealPiiModal({
  isOpen,
  onClose,
  caseId,
  entityId,
  recordId,
  fieldName,
  maskedValue,
  onSuccess,
}) {
  const [justification, setJustification] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [revealedData, setRevealedData] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!justification.trim() || justification.trim().length < 8) {
      setError('Statutory legal justification is required (minimum 8 characters, e.g. Section 63 BSA judicial warrant).');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const res = await extractionV2Api.revealPii(caseId, {
        entityId,
        recordId,
        justification: justification.trim(),
        fieldNames: [fieldName],
      });

      const unmasked = res.unmasked_value || res.revealed?.[fieldName] || res.data?.[fieldName] || res.value;
      setRevealedData({
        value: unmasked,
        auditEventId: res.audit_event_id || res.audit_id,
        officer: res.officer || 'Verified Officer',
        timestamp: res.timestamp || new Date().toISOString(),
      });

      if (onSuccess && unmasked) {
        onSuccess(unmasked);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to unmask identifier. Investigator/Admin role required.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="glass w-full max-w-lg p-6 rounded-2xl border border-white/10 shadow-2xl relative">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-2.5 text-accent">
            <ShieldAlert className="w-5 h-5 shrink-0" />
            <h2 className="font-serif text-lg text-text font-bold">
              Statutory PII Unmask Authorization
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-muted hover:text-text hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Warning Banner */}
        <div className="mt-4 p-3 rounded-xl bg-amber-950/40 border border-amber-800/60 text-[11px] font-mono text-amber-300 space-y-1">
          <div className="flex items-center gap-2 font-semibold text-amber-200">
            <Lock className="w-3.5 h-3.5 shrink-0" />
            <span>MANDATORY CHAIN OF CUSTODY NOTICE</span>
          </div>
          <p className="text-amber-200/80 leading-relaxed">
            Under Section 63 of Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023), unmasking PII records is an audited evidentiary operation. Your officer credentials, timestamp, and judicial justification will be permanently appended to the immutable SHA-256 audit ledger.
          </p>
        </div>

        {/* Target Field Info */}
        <div className="mt-4 p-3 rounded-xl glass-sm space-y-1 font-mono text-xs">
          <div className="flex justify-between text-muted">
            <span>Target Field:</span>
            <span className="text-text font-semibold uppercase">{fieldName}</span>
          </div>
          <div className="flex justify-between text-muted">
            <span>Masked Presentation:</span>
            <span className="text-accent font-semibold">{maskedValue}</span>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-4 p-3 rounded-xl bg-rose-950/50 border border-rose-800 text-rose-300 text-xs font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Form or Result */}
        {!revealedData ? (
          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div>
              <label className="block text-xs font-mono text-muted mb-1.5">
                Statutory Justification / Case Warrant Reference <span className="text-alert">*</span>
              </label>
              <textarea
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                rows={3}
                placeholder="e.g., Special Court Order No. 44/2026 for syndicate line attribution under BSA Sec 63"
                className="w-full px-3 py-2 rounded-xl bg-black/40 border border-white/10 text-text font-mono text-xs focus:outline-none focus:border-accent"
                required
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-mono text-muted hover:text-text rounded-xl border border-white/10 hover:bg-white/5"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 text-xs font-mono font-semibold bg-accent text-ink rounded-xl hover:bg-accent/90 disabled:opacity-50 flex items-center gap-2"
              >
                {submitting ? 'Verifying Credentials...' : 'Authorize & Unmask'}
              </button>
            </div>
          </form>
        ) : (
          <div className="mt-4 space-y-4">
            <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800 text-emerald-300 space-y-2 font-mono text-xs">
              <div className="flex items-center gap-2 text-emerald-200 font-semibold">
                <CheckCircle className="w-4 h-4" />
                <span>Unmasked Value Authorized</span>
              </div>
              <div className="text-base text-text font-bold tracking-wider bg-black/40 p-2.5 rounded-lg border border-emerald-800/60 select-all">
                {revealedData.value || 'Data unmasked on server'}
              </div>
              <div className="text-[10px] text-muted space-y-0.5 pt-1 border-t border-emerald-800/40">
                <div>Audit Event Ref: <span className="text-emerald-400">{revealedData.auditEventId || 'SHA-256 Recorded'}</span></div>
                <div>Authorized By: <span className="text-text">{revealedData.officer}</span></div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-mono bg-accent text-ink font-semibold rounded-xl hover:bg-accent/90"
              >
                Close & Return
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
