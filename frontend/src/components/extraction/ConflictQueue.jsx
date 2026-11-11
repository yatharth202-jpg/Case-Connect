import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, ShieldCheck, Lock, User, Clock, ArrowRight, RefreshCw, Filter } from 'lucide-react';
import { extractionV2Api } from '../../api/client';

export default function ConflictQueue({ caseId, isViewer = false }) {
  const [conflicts, setConflicts] = useState([]);
  const [statusFilter, setStatusFilter] = useState('open');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [resolvingId, setResolvingId] = useState(null);
  const [selectedClaimId, setSelectedClaimId] = useState({});
  const [officerNotes, setOfficerNotes] = useState({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (caseId) {
      loadConflicts();
    }
  }, [caseId, statusFilter]);

  const loadConflicts = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await extractionV2Api.getConflicts(caseId, statusFilter);
      const list = res.conflicts || res.items || res || [];
      setConflicts(Array.isArray(list) ? list : []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to retrieve case merge conflicts.');
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async (conflictId) => {
    const claimId = selectedClaimId[conflictId];
    if (!claimId) {
      alert('Please select one of the competing candidate claims.');
      return;
    }

    const note = officerNotes[conflictId] || 'Officer resolution confirmed under forensic review.';
    setSubmitting(true);

    try {
      await extractionV2Api.resolveConflict(conflictId, { claimId, note });
      // Remove from list or refresh
      setConflicts(prev => prev.filter(c => c.id !== conflictId));
      setResolvingId(null);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to resolve conflict.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Action / Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl glass-sm border border-white/10">
        <div>
          <h3 className="font-serif text-base text-text font-bold">
            Merge Conflicts & Competing Claims Queue
          </h3>
          <p className="text-[11px] text-muted">
            Discrepancies where sources hold conflicting values within the defined confidence margin
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex bg-black/40 p-0.5 rounded-lg border border-white/10 text-[11px]">
            <button
              onClick={() => setStatusFilter('open')}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                statusFilter === 'open' ? 'bg-accent text-ink font-semibold' : 'text-muted hover:text-text'
              }`}
            >
              Open ({conflicts.length})
            </button>
            <button
              onClick={() => setStatusFilter('resolved')}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                statusFilter === 'resolved' ? 'bg-accent text-ink font-semibold' : 'text-muted hover:text-text'
              }`}
            >
              Resolved History
            </button>
          </div>
          <button
            onClick={loadConflicts}
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-muted hover:text-text border border-white/10"
            title="Refresh conflict queue"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="py-16 text-center space-y-2">
          <div className="inline-block animate-spin w-5 h-5 border-2 border-white/20 border-t-accent rounded-full" />
          <p className="text-muted text-[11px]">Querying merge conflict ledger...</p>
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300">
          {error}
        </div>
      ) : conflicts.length === 0 ? (
        /* Actionable Empty State */
        <div className="p-12 text-center rounded-2xl glass-sm border border-dashed border-white/10 space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-emerald-950/40 border border-emerald-800/60 flex items-center justify-center text-emerald-400 mx-auto">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div className="font-serif text-lg text-text">
            {statusFilter === 'open' ? 'Zero Unresolved Merge Conflicts' : 'No Resolved Conflicts Logged'}
          </div>
          <p className="text-muted text-xs max-w-md mx-auto leading-relaxed">
            All extracted evidence records and entity fields are deterministically harmonized across the case docket according to the configured source trust hierarchy.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {conflicts.map((conflict) => {
            const claims = conflict.claims || conflict.candidate_claims || [];
            const isSelected = resolvingId === conflict.id;

            return (
              <div
                key={conflict.id}
                className="p-5 rounded-2xl glass border border-white/10 shadow-lg space-y-4"
              >
                {/* Conflict Card Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-rose-400 animate-pulse" />
                    <span className="text-muted">Target Entity:</span>
                    <span className="text-text font-bold uppercase">{conflict.subject_type || 'Entity'}</span>
                    <span className="text-accent">({conflict.field_name})</span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-muted">
                    <span>ID: <code className="text-text">{conflict.id.slice(0, 10)}...</code></span>
                    {conflict.status === 'resolved' && (
                      <span className="inline-flex items-center gap-1 text-emerald-400">
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Resolved by {conflict.resolved_by || 'Officer'}</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Candidate Claims Comparison Table */}
                <div className="border border-white/10 rounded-xl overflow-x-auto bg-black/30">
                  <table className="w-full text-left font-mono text-xs whitespace-nowrap">
                    <thead className="bg-white/5 text-muted uppercase text-[10px] tracking-wider border-b border-white/10">
                      <tr>
                        <th className="py-2.5 px-3">Select</th>
                        <th className="py-2.5 px-3">Candidate Value</th>
                        <th className="py-2.5 px-3">Source Kind / File</th>
                        <th className="py-2.5 px-3">Extraction Method</th>
                        <th className="py-2.5 px-3">Trust Rank</th>
                        <th className="py-2.5 px-3">Confidence</th>
                        <th className="py-2.5 px-3">Validator Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-text">
                      {claims.map((claim) => {
                        const isChosen = selectedClaimId[conflict.id] === claim.id || conflict.resolution_claim_id === claim.id;

                        return (
                          <tr
                            key={claim.id}
                            onClick={() => {
                              if (conflict.status === 'open' && !isViewer) {
                                setSelectedClaimId(prev => ({ ...prev, [conflict.id]: claim.id }));
                                setResolvingId(conflict.id);
                              }
                            }}
                            className={`cursor-pointer transition-colors ${
                              isChosen
                                ? 'bg-accent/10 border-l-2 border-accent'
                                : 'hover:bg-white/[0.03]'
                            }`}
                          >
                            <td className="py-2 px-3">
                              <input
                                type="radio"
                                name={`claim_${conflict.id}`}
                                checked={isChosen}
                                disabled={conflict.status !== 'open' || isViewer}
                                onChange={() => {
                                  setSelectedClaimId(prev => ({ ...prev, [conflict.id]: claim.id }));
                                  setResolvingId(conflict.id);
                                }}
                                className="accent-accent"
                              />
                            </td>
                            <td className="py-2 px-3 font-bold text-text">
                              {claim.value_norm || claim.value_raw || '—'}
                            </td>
                            <td className="py-2 px-3 text-muted">
                              {claim.source_kind || 'Structured File'}
                              {claim.evidence_id && (
                                <span className="text-[10px] block opacity-70">Doc: {claim.evidence_id.slice(0, 8)}</span>
                              )}
                            </td>
                            <td className="py-2 px-3 text-muted">{claim.method || 'regex'}</td>
                            <td className="py-2 px-3">
                              <span className="px-1.5 py-0.5 rounded text-[10px] bg-white/5 border border-white/10">
                                Rank #{claim.trust_rank || 1}
                              </span>
                            </td>
                            <td className="py-2 px-3">
                              <span className="font-semibold text-accent">
                                {claim.confidence ? Math.round(claim.confidence * 100) : 90}%
                              </span>
                            </td>
                            <td className="py-2 px-3">
                              {claim.validator_ok !== false ? (
                                <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
                                  <ShieldCheck className="w-3.5 h-3.5" />
                                  <span>Passed</span>
                                </span>
                              ) : (
                                <span className="text-amber-400 text-[11px]">Warning</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Resolution Action Area */}
                {conflict.status === 'open' && !isViewer && (
                  <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white/[0.02] p-3 rounded-xl border border-white/5">
                    <div className="flex-1">
                      <input
                        type="text"
                        placeholder="Forensic justification for selected value (optional)..."
                        value={officerNotes[conflict.id] || ''}
                        onChange={(e) => setOfficerNotes(prev => ({ ...prev, [conflict.id]: e.target.value }))}
                        className="w-full px-3 py-1.5 rounded-lg bg-black/40 border border-white/10 text-text text-xs focus:outline-none focus:border-accent"
                      />
                    </div>
                    <button
                      type="button"
                      disabled={submitting || !selectedClaimId[conflict.id]}
                      onClick={() => handleResolve(conflict.id)}
                      className="px-4 py-2 bg-accent text-ink font-semibold rounded-xl hover:bg-accent/90 disabled:opacity-50 transition-colors flex items-center justify-center gap-1.5 shrink-0"
                    >
                      <Lock className="w-3.5 h-3.5" />
                      <span>Lock Golden Decision</span>
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
