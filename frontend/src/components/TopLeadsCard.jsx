import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  TrendingUp,
  RefreshCw,
  FileText,
  Activity,
  Layers,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Info,
} from 'lucide-react';
import { leadsApi } from '../api/client';

export default function TopLeadsCard({ caseId, onSelectEntity }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedIndex, setExpandedIndex] = useState(0);

  const fetchLeads = async (forceRecompute = false) => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await leadsApi.getTopLeads(caseId, 5, forceRecompute);
      setLeads(data.leads || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load primary attributed leads');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads(false);
  }, [caseId]);

  const formatPaise = (paise) => {
    if (!paise) return 'Rs. 0.00';
    const rupees = Math.floor(paise / 100);
    const p = Math.abs(paise % 100);
    return `Rs. ${rupees.toLocaleString('en-IN')}.${p.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 space-y-5 text-slate-100">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold tracking-wide text-white flex items-center gap-2">
              Primary Attributed Leads
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                Top {leads.length}
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Explainable topological prioritization based on network centrality, money flow, and cross-case intelligence.
            </p>
          </div>
        </div>

        <button
          onClick={() => fetchLeads(true)}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs font-medium rounded border border-slate-700 text-slate-200 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Recompute
        </button>
      </div>

      {/* Mandatory Statutory Notice */}
      <div className="flex items-start gap-2.5 p-3 bg-amber-950/20 border border-amber-900/40 rounded-md text-xs text-amber-200/90 leading-relaxed">
        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <p>
          <span className="font-semibold text-amber-300">Statutory Notice:</span> Rank is a statistical indicator for investigative prioritisation, not a finding of culpability.
        </p>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="py-8 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
          <RefreshCw className="w-5 h-5 animate-spin text-rose-400" />
          <span>Evaluating topological signals and cross-case associations...</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-950/30 border border-red-800 rounded text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && leads.length === 0 && (
        <div className="py-8 text-center text-xs text-slate-400">
          No candidates available for lead attribution. Stage evidence to evaluate graph signals.
        </div>
      )}

      {/* Leads List */}
      {!loading && !error && leads.length > 0 && (
        <div className="space-y-3">
          {leads.map((lead, idx) => {
            const isExpanded = expandedIndex === idx;
            const bk = lead.breakdown || {};
            const scorePercent = Math.round(lead.score * 100);

            return (
              <div
                key={lead.entity_id}
                className="bg-slate-950/60 border border-slate-800 hover:border-slate-700 rounded-lg overflow-hidden transition"
              >
                {/* Summary Row */}
                <div
                  onClick={() => setExpandedIndex(isExpanded ? -1 : idx)}
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer select-none"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-7 h-7 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-300 font-mono text-xs font-bold flex items-center justify-center shrink-0">
                      #{lead.rank}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-white font-mono">
                          {lead.display_name || lead.entity_id}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono uppercase">
                          {lead.label}
                        </span>
                        {bk.pass_through_flag && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono font-medium">
                            Rapid Pass-Through
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5 font-mono">
                        {lead.designation}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-5">
                    {/* Score Bar */}
                    <div className="flex items-center gap-2.5">
                      <div className="w-24 bg-slate-800 rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-rose-500 h-2 rounded-full transition-all"
                          style={{ width: `${Math.min(100, Math.max(5, scorePercent))}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono font-bold text-rose-300 w-10 text-right">
                        {scorePercent}%
                      </span>
                    </div>

                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    )}
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-2 border-t border-slate-900 bg-slate-950/90 space-y-4 text-xs">
                    {/* Signal Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-center">
                      <div className="p-2.5 bg-slate-900/80 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Direct Degree</span>
                        <span className="text-white font-mono font-bold text-sm mt-0.5 block">
                          {bk.degree ?? 0}
                        </span>
                      </div>

                      <div className="p-2.5 bg-slate-900/80 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Betweenness</span>
                        <span className="text-white font-mono font-bold text-sm mt-0.5 block">
                          {bk.betweenness ? bk.betweenness.toFixed(3) : '0.000'}
                        </span>
                      </div>

                      <div className="p-2.5 bg-slate-900/80 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">PageRank</span>
                        <span className="text-white font-mono font-bold text-sm mt-0.5 block">
                          {bk.pagerank ? bk.pagerank.toFixed(3) : '0.000'}
                        </span>
                      </div>

                      <div className="p-2.5 bg-slate-900/80 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Pass-Through</span>
                        <span className={`font-mono font-bold text-sm mt-0.5 block ${bk.pass_through_flag ? 'text-amber-400' : 'text-slate-300'}`}>
                          {bk.pass_through_flag ? 'Detected' : 'None'}
                        </span>
                      </div>

                      <div className="p-2.5 bg-slate-900/80 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Total Volume</span>
                        <span className="text-white font-mono font-bold text-xs mt-1 block truncate">
                          {formatPaise(bk.total_paise)}
                        </span>
                      </div>

                      <div className="p-2.5 bg-slate-900/80 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Cross-Case Hits</span>
                        <span className="text-white font-mono font-bold text-sm mt-0.5 block">
                          {bk.cross_case_hits ?? 0}
                        </span>
                      </div>
                    </div>

                    {/* Evidence Sources */}
                    {lead.evidence_sources && lead.evidence_sources.length > 0 && (
                      <div className="space-y-1.5">
                        <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1.5">
                          <FileText className="w-3.5 h-3.5 text-slate-400" />
                          Correlated Evidence Files ({lead.evidence_sources.length}):
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {lead.evidence_sources.map((src, sIdx) => (
                            <span
                              key={sIdx}
                              className="px-2 py-0.5 bg-slate-900 border border-slate-700/80 rounded text-[11px] font-mono text-slate-300"
                            >
                              {src}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
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
