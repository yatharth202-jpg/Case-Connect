import React, { useState, useEffect } from 'react';
import { GitMerge, Check, AlertCircle, ArrowRight, ShieldCheck, X, RefreshCw } from 'lucide-react';
import { extractionV2Api } from '../../api/client';

export default function MergePreviewModal({
  isOpen,
  onClose,
  caseId,
  evidenceId,
  onApplied,
}) {
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [applying, setApplying] = useState(false);
  const [jobProgress, setJobProgress] = useState(0);
  const [jobStep, setJobStep] = useState('');

  useEffect(() => {
    if (isOpen && caseId && evidenceId) {
      loadMergePreview();
    }
  }, [isOpen, caseId, evidenceId]);

  const loadMergePreview = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await extractionV2Api.previewMerge(caseId, evidenceId);
      setPreview(res);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate dry-run merge preview.');
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    setApplying(true);
    setError('');
    setJobProgress(15);
    setJobStep('Acquiring case transaction lock...');

    try {
      const res = await extractionV2Api.applyMerge(caseId, evidenceId);
      const jobId = res.job_id || res.id;

      if (jobId) {
        // Poll job progress
        let active = true;
        const poll = setInterval(async () => {
          if (!active) return;
          try {
            const statusRes = await extractionV2Api.getJob(caseId, jobId);
            setJobProgress(statusRes.progress || 50);
            if (statusRes.steps && statusRes.steps.length > 0) {
              setJobStep(statusRes.steps[statusRes.steps.length - 1]);
            }

            if (statusRes.status === 'completed' || statusRes.status === 'done') {
              active = false;
              clearInterval(poll);
              setJobProgress(100);
              setJobStep('Merge committed and graph indexed.');
              setTimeout(() => {
                if (onApplied) onApplied(statusRes);
                onClose();
              }, 600);
            } else if (statusRes.status === 'failed') {
              active = false;
              clearInterval(poll);
              setError(statusRes.error_message || 'Ingest job failed to complete.');
              setApplying(false);
            }
          } catch (e) {
            // Fallback: poll error
          }
        }, 1000);
      } else {
        // Direct response
        setJobProgress(100);
        setTimeout(() => {
          if (onApplied) onApplied(res);
          onClose();
        }, 600);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to dispatch merge job.');
      setApplying(false);
    }
  };

  if (!isOpen) return null;

  const counts = preview?.counts || {
    new_records: 0,
    same_records: 0,
    updated: 0,
    new_fields: 0,
    conflicts: 0,
    rejected: 0,
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="glass w-full max-w-2xl p-6 rounded-2xl border border-white/10 shadow-2xl relative">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-2.5 text-accent">
            <GitMerge className="w-5 h-5 shrink-0" />
            <div>
              <h2 className="font-serif text-lg text-text font-bold">
                Dry-Run Merge Preview & Conflict Check
              </h2>
              <p className="text-xs font-mono text-muted">
                Deterministic claim evaluation against authoritative SQLite record store
              </p>
            </div>
          </div>
          {!applying && (
            <button onClick={onClose} className="p-1 rounded text-muted hover:text-text hover:bg-white/5">
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {loading ? (
          <div className="py-16 text-center space-y-3 font-mono text-xs">
            <div className="inline-block animate-spin w-6 h-6 border-2 border-white/20 border-t-accent rounded-full" />
            <p className="text-muted">Computing natural keys, claim trust orders, and delta counts...</p>
          </div>
        ) : error && !applying ? (
          <div className="py-8 text-center space-y-4">
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-xs font-mono">
              {error}
            </div>
            <button onClick={loadMergePreview} className="px-4 py-2 text-xs font-mono bg-white/5 text-text rounded-xl border border-white/10">
              Retry Calculation
            </button>
          </div>
        ) : applying ? (
          <div className="py-12 space-y-4 text-center font-mono">
            <div className="text-xs text-text font-semibold">{jobStep || 'Committing claims to SQLite...'}</div>
            <div className="w-full bg-white/5 h-2 rounded-full overflow-hidden border border-white/10 max-w-md mx-auto">
              <div
                className="bg-accent h-full transition-all duration-300"
                style={{ width: `${jobProgress}%` }}
              />
            </div>
            <div className="text-[11px] text-muted">{jobProgress}% completed</div>
          </div>
        ) : (
          <div className="py-5 space-y-5 font-mono">
            {/* Impact Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="p-3 rounded-xl glass-sm border border-emerald-800/40">
                <div className="text-[10px] text-muted uppercase">Genuinely New</div>
                <div className="text-xl font-bold text-emerald-400 mt-1">{counts.new_records}</div>
                <div className="text-[10px] text-muted mt-0.5">Novel records added</div>
              </div>

              <div className="p-3 rounded-xl glass-sm border border-white/10">
                <div className="text-[10px] text-muted uppercase">Identical / Same</div>
                <div className="text-xl font-bold text-text mt-1">{counts.same_records}</div>
                <div className="text-[10px] text-muted mt-0.5">Sources corroborated</div>
              </div>

              <div className="p-3 rounded-xl glass-sm border border-cyan-800/40">
                <div className="text-[10px] text-muted uppercase">New Fields</div>
                <div className="text-xl font-bold text-cyan-400 mt-1">{counts.new_fields}</div>
                <div className="text-[10px] text-muted mt-0.5">Appended to existing</div>
              </div>

              <div className="p-3 rounded-xl glass-sm border border-rose-800/40">
                <div className="text-[10px] text-muted uppercase">Merge Conflicts</div>
                <div className="text-xl font-bold text-rose-400 mt-1">{counts.conflicts}</div>
                <div className="text-[10px] text-muted mt-0.5">Requires officer decision</div>
              </div>

              <div className="p-3 rounded-xl glass-sm border border-amber-800/40">
                <div className="text-[10px] text-muted uppercase">Updated Claims</div>
                <div className="text-xl font-bold text-amber-400 mt-1">{counts.updated || 0}</div>
                <div className="text-[10px] text-muted mt-0.5">Higher trust win</div>
              </div>

              <div className="p-3 rounded-xl glass-sm border border-white/10">
                <div className="text-[10px] text-muted uppercase">Rejected Rows</div>
                <div className="text-xl font-bold text-muted mt-1">{counts.rejected || 0}</div>
                <div className="text-[10px] text-muted mt-0.5">Logged with reason</div>
              </div>
            </div>

            {/* Invariant Statement */}
            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/10 text-xs text-muted leading-relaxed">
              Applying this merge will commit claims within a single atomic SQLite transaction, recompute golden fields deterministically based on source trust order, update the disposable Neo4j/NetworkX projection, and record an immutable Section 63 BSA event in the audit chain.
            </div>
          </div>
        )}

        {/* Footer */}
        {!applying && !loading && (
          <div className="flex items-center justify-between pt-4 border-t border-white/10">
            <span className="text-[11px] font-mono text-muted flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Full Reversibility (Rollback Supported)</span>
            </span>
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
                onClick={handleApply}
                className="px-4 py-2 text-xs font-mono font-semibold bg-accent text-ink rounded-xl hover:bg-accent/90 flex items-center gap-2"
              >
                <span>Commit & Ingest Evidence</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
