import React, { useState, useEffect } from 'react';
import { analyticsApi } from '../api/client';

export default function LeadAdvisor({ caseId, isViewer = false }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [summaryStats, setSummaryStats] = useState({ total: 0, high: 0, medium: 0, low: 0 });

  // Decision Modal State
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [decisionType, setDecisionType] = useState('accept');
  const [decisionNotes, setDecisionNotes] = useState('');
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [actionSuccess, setActionSuccess] = useState('');

  // Provenance / Why Modal State
  const [provenanceModalOpen, setProvenanceModalOpen] = useState(false);
  const [provenanceLoading, setProvenanceLoading] = useState(false);
  const [provenanceData, setProvenanceData] = useState(null);
  const [whyData, setWhyData] = useState(null);
  const [activeModalTab, setActiveModalTab] = useState('why'); // 'why' or 'provenance'

  const fetchLeads = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await analyticsApi.getLeads(caseId, { limit: 100 });
      setLeads(res.leads || []);
      setSummaryStats({
        total: res.total_count || res.leads?.length || 0,
        high: res.high_count || 0,
        medium: res.medium_count || 0,
        low: res.low_count || 0,
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to compute investigative leads.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchLeads();
    }
  }, [caseId]);

  const handleOpenDecision = (lead) => {
    setSelectedLead(lead);
    setDecisionType(lead.decision || 'accept');
    setDecisionNotes(lead.decision_notes || '');
    setDecisionModalOpen(true);
    setActionSuccess('');
  };

  const handleSaveDecision = async (e) => {
    e.preventDefault();
    if (!selectedLead) return;
    setSubmittingDecision(true);
    try {
      await analyticsApi.recordLeadDecision(caseId, selectedLead.id, {
        decision: decisionType,
        notes: decisionNotes,
      });
      setActionSuccess(`Decision '${decisionType}' recorded in cryptographic audit ledger.`);
      // Update local state
      setLeads((prev) =>
        prev.map((l) =>
          l.id === selectedLead.id
            ? { ...l, decision: decisionType, decision_notes: decisionNotes }
            : l
        )
      );
      setTimeout(() => {
        setDecisionModalOpen(false);
        setActionSuccess('');
      }, 1000);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to record decision');
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleInspectEntity = async (lead) => {
    setSelectedLead(lead);
    setProvenanceModalOpen(true);
    setProvenanceLoading(true);
    setActiveModalTab('why');
    try {
      const [whyRes, provRes] = await Promise.all([
        analyticsApi.getEntityWhy(caseId, lead.entity_id),
        analyticsApi.getProvenance(caseId, { nodeId: lead.entity_id }),
      ]);
      setWhyData(whyRes);
      setProvenanceData(provRes);
    } catch (err) {
      console.error(err);
    } finally {
      setProvenanceLoading(false);
    }
  };

  // Filtered Leads
  const filteredLeads = leads.filter((l) => {
    if (activeFilter !== 'ALL' && l.level !== activeFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const name = (l.display_name || '').toLowerCase();
      const id = (l.entity_id || '').toLowerCase();
      const pat = (l.matched_pattern?.name || '').toLowerCase();
      return name.includes(q) || id.includes(q) || pat.includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* 1. Legal Standard & Disclaimer Notice Banner */}
      <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded bg-cyan-950/70 border border-cyan-800 flex items-center justify-center text-[#38bdf8] flex-shrink-0 mt-0.5">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white tracking-tight">
                Hero Feature #3: Explainable Lead Advisor Engine
              </h2>
              <span className="text-[10px] font-mono uppercase bg-[#030712] border border-[#1e293b] text-cyan-400 px-2 py-0.5 rounded">
                Section 63 BSA 2023 Verified
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl">
              <strong className="text-amber-400">Statutory Notice:</strong> Lead for review — not a finding of wrongdoing.
              Rankings are 100% deterministic and rule-derived with zero predictive AI models. Weights dynamically normalized across available evidence types.
            </p>
          </div>
        </div>

        <button
          onClick={fetchLeads}
          disabled={loading}
          className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-white text-xs font-medium rounded border border-[#334155] flex items-center gap-2 transition-colors self-start md:self-auto"
        >
          <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Recompute Leads
        </button>
      </div>

      {/* 2. Priority Summary Metric Chips */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <button
          onClick={() => setActiveFilter('ALL')}
          className={`p-4 rounded-lg border text-left transition-all ${
            activeFilter === 'ALL'
              ? 'bg-[#0f172a] border-[#38bdf8] ring-1 ring-[#38bdf8]'
              : 'bg-[#0b1120] border-[#1e293b] hover:border-slate-600'
          }`}
        >
          <span className="text-[11px] font-mono text-slate-400 block mb-1">TOTAL IDENTIFIED LEADS</span>
          <span className="text-2xl font-bold font-mono text-white">{summaryStats.total}</span>
          <span className="text-[10px] text-slate-500 block mt-1">Multi-modal candidates</span>
        </button>

        <button
          onClick={() => setActiveFilter('HIGH')}
          className={`p-4 rounded-lg border text-left transition-all ${
            activeFilter === 'HIGH'
              ? 'bg-rose-950/40 border-rose-500 ring-1 ring-rose-500'
              : 'bg-[#0b1120] border-[#1e293b] hover:border-rose-900/60'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-mono text-rose-300">HIGH PRIORITY</span>
            <span className="w-2 h-2 rounded-full bg-rose-500"></span>
          </div>
          <span className="text-2xl font-bold font-mono text-rose-400">{summaryStats.high}</span>
          <span className="text-[10px] text-rose-300/70 block mt-1">Priority score &ge; 70</span>
        </button>

        <button
          onClick={() => setActiveFilter('MEDIUM')}
          className={`p-4 rounded-lg border text-left transition-all ${
            activeFilter === 'MEDIUM'
              ? 'bg-amber-950/40 border-amber-500 ring-1 ring-amber-500'
              : 'bg-[#0b1120] border-[#1e293b] hover:border-amber-900/60'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-mono text-amber-300">MEDIUM PRIORITY</span>
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
          </div>
          <span className="text-2xl font-bold font-mono text-amber-400">{summaryStats.medium}</span>
          <span className="text-[10px] text-amber-300/70 block mt-1">Priority score 40 - 69</span>
        </button>

        <button
          onClick={() => setActiveFilter('LOW')}
          className={`p-4 rounded-lg border text-left transition-all ${
            activeFilter === 'LOW'
              ? 'bg-emerald-950/40 border-emerald-500 ring-1 ring-emerald-500'
              : 'bg-[#0b1120] border-[#1e293b] hover:border-emerald-900/60'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-mono text-emerald-300">LOW PRIORITY</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          </div>
          <span className="text-2xl font-bold font-mono text-emerald-400">{summaryStats.low}</span>
          <span className="text-[10px] text-emerald-300/70 block mt-1">Priority score &lt; 40</span>
        </button>
      </div>

      {/* 3. Search Bar and Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-[#0b1120] border border-[#1e293b] p-3 rounded-lg">
        <div className="relative w-full sm:w-80">
          <input
            type="text"
            placeholder="Search candidate name, ID, or archetype..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#030712] border border-[#1e293b] rounded px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#38bdf8]"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-2 text-slate-500 hover:text-white text-xs"
            >
              &times;
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto text-xs text-slate-400">
          <span>Showing:</span>
          <span className="font-mono font-bold text-white">{filteredLeads.length}</span>
          <span>of</span>
          <span className="font-mono text-white">{leads.length}</span>
        </div>
      </div>

      {/* 4. Leads List */}
      {loading ? (
        <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg p-16 text-center">
          <div className="inline-block animate-spin w-8 h-8 border-2 border-slate-600 border-t-[#38bdf8] rounded-full mb-3"></div>
          <p className="text-xs text-slate-400 font-medium">Computing multi-modal graph centrality & score breakdown...</p>
          <p className="text-[10px] text-slate-500 mt-1">Evaluating Louvain community bridging, MAD spike ratios, and transaction percentiles</p>
        </div>
      ) : error ? (
        <div className="bg-rose-950/40 border border-rose-800 rounded-lg p-6 text-center text-rose-300 text-xs">
          {error}
        </div>
      ) : filteredLeads.length === 0 ? (
        <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg p-16 text-center">
          <svg className="w-10 h-10 text-slate-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h4 className="text-xs font-bold text-white">No investigative leads match current filter criteria</h4>
          <p className="text-[11px] text-slate-400 mt-1">Upload evidence files (CDRs, Bank Statements, FIRs) to generate actionable leads.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredLeads.map((lead, idx) => {
            const isHigh = lead.level === 'HIGH';
            const isMed = lead.level === 'MEDIUM';

            return (
              <div
                key={lead.id}
                className={`bg-[#0b1120] border rounded-lg p-5 transition-all ${
                  isHigh
                    ? 'border-rose-900/50 hover:border-rose-700/80 shadow-sm shadow-rose-950/20'
                    : isMed
                    ? 'border-amber-900/50 hover:border-amber-700/80'
                    : 'border-[#1e293b] hover:border-slate-700'
                }`}
              >
                {/* Lead Header */}
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-4 border-b border-[#1e293b]">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded bg-[#030712] border border-[#1e293b] flex items-center justify-center font-mono text-xs font-bold text-slate-300 flex-shrink-0">
                      #{idx + 1}
                    </div>

                    <div>
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span
                          className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border font-bold ${
                            isHigh
                              ? 'bg-rose-950/60 text-rose-300 border-rose-800'
                              : isMed
                              ? 'bg-amber-950/60 text-amber-300 border-amber-800'
                              : 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                          }`}
                        >
                          {lead.level} PRIORITY ({lead.priority})
                        </span>

                        <span className="text-[10px] font-mono text-slate-300 bg-[#030712] px-2 py-0.5 rounded border border-[#1e293b]">
                          {lead.entity_type}
                        </span>

                        <span className="text-[10px] font-mono text-slate-400 bg-[#030712] px-2 py-0.5 rounded border border-[#1e293b]">
                          Confidence: <strong className="text-white">{lead.confidence}</strong>
                        </span>

                        {lead.decision && (
                          <span
                            className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border font-semibold ${
                              lead.decision === 'accept'
                                ? 'bg-cyan-950/60 text-cyan-300 border-cyan-800'
                                : lead.decision === 'reject'
                                ? 'bg-slate-800 text-slate-300 border-slate-700'
                                : 'bg-amber-950/60 text-amber-300 border-amber-800'
                            }`}
                          >
                            Officer Decision: {lead.decision.replace('_', ' ')}
                          </span>
                        )}
                      </div>

                      <h3 className="text-base font-bold text-white tracking-tight">
                        {lead.display_name}
                      </h3>
                      <p className="text-xs font-mono text-slate-400 mt-0.5">
                        Canonical ID: <span className="text-[#38bdf8]">{lead.entity_id}</span>
                      </p>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 self-start md:self-auto flex-wrap">
                    <button
                      onClick={() => handleInspectEntity(lead)}
                      className="px-2.5 py-1.5 bg-[#030712] hover:bg-[#1e293b] text-[#38bdf8] text-xs font-medium rounded border border-[#1e293b] hover:border-[#38bdf8] transition-colors flex items-center gap-1.5"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Why this entity?
                    </button>

                    {!isViewer && (
                      <button
                        onClick={() => handleOpenDecision(lead)}
                        className="px-2.5 py-1.5 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-medium rounded transition-colors flex items-center gap-1.5"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {lead.decision ? 'Update Decision' : 'Record Decision'}
                      </button>
                    )}
                  </div>
                </div>

                {/* Score Breakdown (5 Signals) */}
                <div className="mt-4">
                  <h4 className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-2.5">
                    Signal Contribution & Availability Normalization
                  </h4>

                  <div className="space-y-3">
                    {lead.signals?.map((sig) => {
                      const isAvail = sig.is_available;
                      const scorePct = isAvail ? Math.round(sig.score * 100) : 0;

                      return (
                        <div key={sig.name} className="bg-[#030712] border border-[#1e293b] p-3 rounded">
                          <div className="flex items-center justify-between text-xs mb-1.5">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-slate-200">{sig.label}</span>
                              <span className="text-[10px] font-mono text-slate-500">
                                (Weight: {sig.weight}%)
                              </span>
                            </div>

                            {isAvail ? (
                              <span className="font-mono text-xs font-bold text-white">
                                {scorePct}% score
                              </span>
                            ) : (
                              <span className="text-[10px] font-mono text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-900/60">
                                Not Available
                              </span>
                            )}
                          </div>

                          {/* Progress bar */}
                          <div className="w-full bg-[#1e293b] h-1.5 rounded-full overflow-hidden mb-1.5">
                            {isAvail ? (
                              <div
                                className={`h-full transition-all rounded-full ${
                                  scorePct >= 70
                                    ? 'bg-rose-500'
                                    : scorePct >= 40
                                    ? 'bg-amber-500'
                                    : 'bg-cyan-500'
                                }`}
                                style={{ width: `${Math.max(scorePct, 3)}%` }}
                              ></div>
                            ) : (
                              <div className="h-full w-full bg-slate-800 border-dashed"></div>
                            )}
                          </div>

                          {/* Fact explanation */}
                          <p className="text-[11px] text-slate-400 leading-relaxed font-sans">
                            {sig.explanation}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Matched Pattern & Next Steps Section */}
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Pattern & Missing Data */}
                  <div className="bg-[#030712] border border-[#1e293b] rounded p-3">
                    <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                      Matched Pattern Archetype
                    </span>
                    {lead.matched_pattern ? (
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-bold text-white">
                            {lead.matched_pattern.name}
                          </span>
                          <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/40 px-1.5 py-0.5 rounded border border-cyan-800">
                            {lead.matched_pattern.id}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400">
                          {lead.matched_pattern.description}
                        </p>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic">
                        No specific recurring archetype template matched. Ranked via general composite signals.
                      </p>
                    )}

                    {lead.missing_data && lead.missing_data.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-[#1e293b]">
                        <span className="text-[10px] font-mono uppercase text-amber-400 block mb-1">
                          Missing Data Checklist
                        </span>
                        <ul className="text-[11px] text-slate-300 space-y-1">
                          {lead.missing_data.map((md, idx) => (
                            <li key={idx} className="flex items-start gap-1.5">
                              <span className="text-amber-500 mt-0.5">&#x26A0;</span>
                              <span>{md}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Suggested Next Steps */}
                  <div className="bg-[#030712] border border-[#1e293b] rounded p-3">
                    <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                      Statutory Investigative Next Steps
                    </span>
                    <ul className="text-[11px] text-slate-300 space-y-1.5">
                      {lead.suggested_next_steps?.map((step, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="text-[#38bdf8] font-mono font-bold mt-0.5">#{idx + 1}</span>
                          <span className="leading-snug">{step}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Lead Decision Notes if present */}
                {lead.decision_notes && (
                  <div className="mt-3 bg-[#030712] border border-[#1e293b] rounded p-3 text-xs">
                    <span className="text-[10px] font-mono uppercase text-slate-500 block mb-1">
                      Case Diary Note by Investigating Officer
                    </span>
                    <p className="text-slate-300 italic font-serif">
                      "{lead.decision_notes}"
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* 5. Officer Decision Modal */}
      {decisionModalOpen && selectedLead && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg max-w-lg w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] mb-4">
              <div>
                <h3 className="text-sm font-bold text-white">Record Investigative Lead Decision</h3>
                <p className="text-xs text-slate-400">
                  Target candidate: <strong className="text-white">{selectedLead.display_name}</strong>
                </p>
              </div>
              <button
                onClick={() => setDecisionModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs font-mono"
              >
                [ESC / CLOSE]
              </button>
            </div>

            {actionSuccess ? (
              <div className="py-8 text-center text-emerald-400 font-mono text-xs">
                &#x2713; {actionSuccess}
              </div>
            ) : (
              <form onSubmit={handleSaveDecision} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-2">
                    Investigative Decision
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: 'accept', label: 'Accept Lead', desc: 'Active line of inquiry' },
                      { id: 'reject', label: 'Reject / Decoy', desc: 'Benign / ruled out' },
                      { id: 'need_more_data', label: 'Need More Data', desc: 'Pending requisition' },
                    ].map((opt) => (
                      <button
                        type="button"
                        key={opt.id}
                        onClick={() => setDecisionType(opt.id)}
                        className={`p-2.5 rounded border text-left text-xs transition-colors ${
                          decisionType === opt.id
                            ? 'bg-[#0284c7] border-[#38bdf8] text-white font-semibold'
                            : 'bg-[#030712] border-[#1e293b] text-slate-400 hover:text-white'
                        }`}
                      >
                        <span className="block font-medium">{opt.label}</span>
                        <span className="text-[10px] opacity-80 block mt-0.5">{opt.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">
                    Case Diary Rationale / Officer Notes (Mandatory for Audit Trail)
                  </label>
                  <textarea
                    rows={4}
                    value={decisionNotes}
                    onChange={(e) => setDecisionNotes(e.target.value)}
                    placeholder="Document evidentiary justification for accepting, rejecting, or marking pending..."
                    className="w-full bg-[#030712] border border-[#1e293b] rounded p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#38bdf8]"
                  ></textarea>
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#1e293b]">
                  <button
                    type="button"
                    onClick={() => setDecisionModalOpen(false)}
                    className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 text-xs rounded transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingDecision}
                    className="px-4 py-1.5 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded transition-colors"
                  >
                    {submittingDecision ? 'Submitting...' : 'Commit to Audit Ledger'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* 6. Entity "Why" & Forensic Provenance Inspector Modal */}
      {provenanceModalOpen && selectedLead && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg max-w-3xl w-full p-6 shadow-2xl my-8">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] mb-4">
              <div>
                <h3 className="text-sm font-bold text-white">
                  Entity Forensic Inspection & Provenance Card
                </h3>
                <p className="text-xs text-slate-400">
                  Target candidate: <strong className="text-white">{selectedLead.display_name}</strong> ({selectedLead.entity_id})
                </p>
              </div>
              <button
                onClick={() => setProvenanceModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs font-mono"
              >
                [CLOSE]
              </button>
            </div>

            {/* Modal Tabs */}
            <div className="flex items-center gap-2 border-b border-[#1e293b] pb-2 mb-4">
              <button
                onClick={() => setActiveModalTab('why')}
                className={`px-3 py-1 text-xs font-medium rounded ${
                  activeModalTab === 'why'
                    ? 'bg-[#0284c7] text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Why is this entity important?
              </button>
              <button
                onClick={() => setActiveModalTab('provenance')}
                className={`px-3 py-1 text-xs font-medium rounded ${
                  activeModalTab === 'provenance'
                    ? 'bg-[#0284c7] text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Evidentiary Provenance
              </button>
            </div>

            {provenanceLoading ? (
              <div className="py-12 text-center text-xs text-slate-400">
                <div className="inline-block animate-spin w-6 h-6 border-2 border-slate-600 border-t-[#38bdf8] rounded-full mb-2"></div>
                <p>Retrieving cryptographic evidence hashes & raw records...</p>
              </div>
            ) : activeModalTab === 'why' && whyData ? (
              <div className="space-y-4">
                <div className="bg-[#030712] border border-[#1e293b] p-4 rounded-lg">
                  <span className="text-[10px] font-mono uppercase text-[#38bdf8] block mb-1">
                    Plain-English Deterministic Synthesis (Zero LLM)
                  </span>
                  <p className="text-xs text-slate-200 leading-relaxed font-sans">
                    {whyData.narrative}
                  </p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="bg-[#030712] border border-[#1e293b] p-3 rounded">
                    <span className="text-[10px] font-mono text-slate-400 block mb-0.5">PRIORITY SCORE</span>
                    <span className="text-lg font-bold font-mono text-white">{whyData.priority}</span>
                    <span className="text-[10px] text-slate-500 block">Level: {whyData.level}</span>
                  </div>

                  <div className="bg-[#030712] border border-[#1e293b] p-3 rounded">
                    <span className="text-[10px] font-mono text-slate-400 block mb-0.5">NETWORK DEGREE</span>
                    <span className="text-lg font-bold font-mono text-white">{whyData.degree}</span>
                    <span className="text-[10px] text-slate-500 block">Relational links</span>
                  </div>

                  <div className="bg-[#030712] border border-[#1e293b] p-3 rounded">
                    <span className="text-[10px] font-mono text-slate-400 block mb-0.5">TELECOM CALLS</span>
                    <span className="text-lg font-bold font-mono text-white">{whyData.calls_count}</span>
                    <span className="text-[10px] text-slate-500 block">In CDR logs</span>
                  </div>

                  <div className="bg-[#030712] border border-[#1e293b] p-3 rounded">
                    <span className="text-[10px] font-mono text-slate-400 block mb-0.5">TOTAL VOLUME</span>
                    <span className="text-lg font-bold font-mono text-white">Rs. {whyData.financial_volume_rs?.toLocaleString()}</span>
                    <span className="text-[10px] text-slate-500 block">In & Out flow</span>
                  </div>
                </div>

                {whyData.alerts_count > 0 && (
                  <div className="bg-amber-950/20 border border-amber-900/40 p-3 rounded text-xs text-amber-300">
                    Flagged in {whyData.alerts_count} active anomaly detection alert(s).
                  </div>
                )}
              </div>
            ) : provenanceData ? (
              <div className="space-y-4">
                <div className="bg-[#030712] border border-[#1e293b] p-3 rounded text-xs space-y-2 font-mono">
                  <div className="flex justify-between border-b border-[#1e293b] pb-1.5">
                    <span className="text-slate-400">Source Evidence File:</span>
                    <span className="text-white">{provenanceData.source_file}</span>
                  </div>
                  <div className="flex justify-between border-b border-[#1e293b] pb-1.5">
                    <span className="text-slate-400">Reference Index:</span>
                    <span className="text-white">{provenanceData.source_ref}</span>
                  </div>
                  <div className="flex justify-between border-b border-[#1e293b] pb-1.5">
                    <span className="text-slate-400">Extraction Method:</span>
                    <span className="text-white">{provenanceData.method}</span>
                  </div>
                  <div className="flex justify-between border-b border-[#1e293b] pb-1.5">
                    <span className="text-slate-400">Confidence Rating:</span>
                    <span className="text-white">{(provenanceData.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between items-center pt-0.5">
                    <span className="text-slate-400">Evidence SHA-256:</span>
                    <span className="text-[11px] text-[#38bdf8] truncate max-w-xs">{provenanceData.evidence_sha256}</span>
                  </div>
                </div>

                <p className="text-xs text-slate-300 font-sans">
                  {provenanceData.explanation}
                </p>
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-slate-400">
                No provenance data available.
              </div>
            )}

            <div className="mt-6 pt-3 border-t border-[#1e293b] flex justify-end">
              <button
                onClick={() => setProvenanceModalOpen(false)}
                className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-white text-xs rounded transition-colors"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
