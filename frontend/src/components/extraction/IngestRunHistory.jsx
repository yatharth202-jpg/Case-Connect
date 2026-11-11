import React, { useState, useEffect } from 'react';
import { History, RotateCcw, AlertTriangle, ShieldCheck, Check, Clock, RefreshCw } from 'lucide-react';
import { extractionV2Api } from '../../api/client';

export default function IngestRunHistory({ caseId, isViewer = false }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rollingBackId, setRollingBackId] = useState(null);
  const [confirmModalData, setConfirmModalData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (caseId) {
      loadRuns();
    }
  }, [caseId]);

  const loadRuns = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await extractionV2Api.getIngestRuns(caseId);
      const list = res.runs || res || [];
      setRuns(Array.isArray(list) ? list : []);
    } catch (e) {
      setError('Could not load ingest history runs.');
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!confirmModalData) return;
    const { runId, evidenceId } = confirmModalData;
    setRollingBackId(runId);

    try {
      await extractionV2Api.rollbackMerge(caseId, evidenceId);
      setConfirmModalData(null);
      await loadRuns();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to execute rollback operation.');
    } finally {
      setRollingBackId(null);
    }
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      <div className="flex items-center justify-between p-4 rounded-xl glass-sm border border-white/10">
        <div>
          <h3 className="font-serif text-base text-text font-bold">
            Evidence Ingestion Changelog & Provenance Runs
          </h3>
          <p className="text-[11px] text-muted">
            Atomic batch history with point-in-time forensic rollback capability
          </p>
        </div>
        <button
          onClick={loadRuns}
          className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-muted hover:text-text border border-white/10"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading ? (
        <div className="py-16 text-center text-muted">
          <div className="inline-block animate-spin w-5 h-5 border-2 border-white/20 border-t-accent rounded-full mb-2" />
          <p>Querying run history log...</p>
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300">
          {error}
        </div>
      ) : runs.length === 0 ? (
        <div className="p-12 text-center rounded-2xl glass-sm border border-dashed border-white/10 space-y-2">
          <div className="font-serif text-base text-text">No Historical Ingest Runs Recorded</div>
          <p className="text-muted text-xs max-w-sm mx-auto">
            Ingestion changelogs and audit runs will populate here as evidence files are processed.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {runs.map((run) => {
            const counts = run.counts_json ? (typeof run.counts_json === 'string' ? JSON.parse(run.counts_json) : run.counts_json) : {};

            return (
              <div
                key={run.id}
                className="p-4 rounded-2xl glass border border-white/10 flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-text">Run #{run.id?.slice(0, 8)}</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-white/5 text-muted uppercase">
                      Mode: {run.mode || 'apply'}
                    </span>
                    <span className="text-muted text-[10px]">
                      Version: {run.extractor_version || '1.0.0'}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-muted">
                    <span>Evidence: <code className="text-text">{run.evidence_id?.slice(0, 8)}</code></span>
                    <span>Started: {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-[10px]">
                  <span className="px-2 py-1 rounded bg-emerald-950/50 text-emerald-400 border border-emerald-800/40">
                    +{counts.new_records || 0} New
                  </span>
                  <span className="px-2 py-1 rounded bg-white/5 text-text border border-white/10">
                    {counts.same_records || 0} Same
                  </span>
                  {counts.conflicts > 0 && (
                    <span className="px-2 py-1 rounded bg-rose-950/50 text-rose-300 border border-rose-800/40">
                      {counts.conflicts} Conflicts
                    </span>
                  )}
                </div>

                {!isViewer && run.mode === 'apply' && (
                  <button
                    disabled={rollingBackId === run.id}
                    onClick={() => setConfirmModalData({ runId: run.id, evidenceId: run.evidence_id })}
                    className="px-3 py-1.5 rounded-xl border border-rose-800/60 bg-rose-950/30 text-rose-300 hover:bg-rose-950/60 flex items-center gap-1.5 text-xs transition-colors self-start md:self-auto shrink-0"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Rollback</span>
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Rollback Confirmation Modal */}
      {confirmModalData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="glass w-full max-w-md p-6 rounded-2xl border border-rose-800 shadow-2xl relative space-y-4">
            <div className="flex items-center gap-2.5 text-rose-400">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <h3 className="font-serif text-lg font-bold text-text">Confirm Evidence Rollback</h3>
            </div>

            <p className="text-xs text-muted leading-relaxed">
              Are you sure you want to retract claims from evidence file <code className="text-text font-bold">{confirmModalData.evidenceId?.slice(0, 10)}</code>?
            </p>
            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/10 text-[11px] text-muted space-y-1">
              <div>• Only claims originating from this specific file will be retracted.</div>
              <div>• Golden fields will be deterministically recalculated from remaining evidence.</div>
              <div>• A cryptographic rollback event will be logged to Section 63 BSA audit chain.</div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
              <button
                type="button"
                onClick={() => setConfirmModalData(null)}
                className="px-4 py-2 text-xs rounded-xl border border-white/10 text-muted hover:text-text"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRollback}
                className="px-4 py-2 text-xs font-semibold bg-rose-600 text-white rounded-xl hover:bg-rose-500"
              >
                Confirm Rollback
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
