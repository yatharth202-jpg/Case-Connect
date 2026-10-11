import React, { useState, useEffect } from 'react';
import { analyticsApi, graphApi, evidenceApi } from '../api/client';

function formatCurrency(val) {
  if (val === undefined || val === null || isNaN(val)) return '₹0';
  const num = Number(val);
  if (num >= 10000000) {
    return `₹${(num / 10000000).toFixed(2)} Cr`;
  } else if (num >= 100000) {
    return `₹${(num / 100000).toFixed(2)} L`;
  } else if (num >= 1000) {
    return `₹${(num / 1000).toFixed(1)} K`;
  }
  return `₹${num.toLocaleString('en-IN')}`;
}

export default function HawalaSyndicateExplorer({ caseId, onOpenTab }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Dynamic Case Data
  const [overview, setOverview] = useState(null);
  const [leads, setLeads] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [graphNodes, setGraphNodes] = useState([]);
  const [graphEdges, setGraphEdges] = useState([]);
  const [evidenceFiles, setEvidenceFiles] = useState([]);

  // Selected State
  const [selectedLeadIndex, setSelectedLeadIndex] = useState(0);
  const [selectedVehicleId, setSelectedVehicleId] = useState(null);
  const [activeFilter, setActiveFilter] = useState('ALL');

  useEffect(() => {
    let mounted = true;
    async function fetchCaseIntelligence() {
      if (!caseId) return;
      setLoading(true);
      setError(null);
      try {
        const [ovRes, leadsRes, alertsRes, graphRes, evRes] = await Promise.all([
          analyticsApi.getOverview(caseId).catch(() => null),
          analyticsApi.getLeads(caseId, { limit: 50 }).catch(() => ({ leads: [] })),
          analyticsApi.getAlerts(caseId).catch(() => ({ alerts: [] })),
          graphApi.search(caseId, { hops: 2, limit: 150 }).catch(() => ({ nodes: [], edges: [] })),
          evidenceApi.list(caseId).catch(() => [])
        ]);

        if (!mounted) return;
        setOverview(ovRes);
        setLeads(leadsRes.leads || []);
        setAlerts(alertsRes.alerts || []);
        setGraphNodes(graphRes.nodes || []);
        setGraphEdges(graphRes.edges || []);
        setEvidenceFiles(evRes || []);

        if (leadsRes.leads && leadsRes.leads.length > 0) {
          setSelectedLeadIndex(0);
        }
      } catch (err) {
        console.error('Failed to load dynamic case intelligence', err);
        if (mounted) setError('Failed to retrieve case analytics from forensic database.');
      } finally {
        if (mounted) setLoading(false);
      }
    }

    fetchCaseIntelligence();
    return () => {
      mounted = false;
    };
  }, [caseId]);

  if (loading) {
    return (
      <div className="bg-[#080d19] border border-[#1e293b] rounded-xl p-12 text-center shadow-xl">
        <div className="w-8 h-8 border-2 border-[#38bdf8] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        <p className="text-xs text-slate-400 font-mono tracking-wider">
          COMPILING DYNAMIC CASE DOSSIER FROM FORENSIC DATABASE...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-950/40 border border-rose-800 rounded-xl p-6 text-center my-4">
        <p className="text-xs text-rose-300 font-mono">{error}</p>
      </div>
    );
  }

  // If no leads or entities have been computed yet for this case
  if (!leads || leads.length === 0) {
    return (
      <div className="bg-[#080d19] border border-[#1e293b] rounded-xl p-10 text-center shadow-xl">
        <div className="w-12 h-12 rounded-lg bg-slate-900 border border-slate-800 mx-auto mb-3 flex items-center justify-center text-slate-500">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3 className="text-sm font-bold text-white mb-1">No Evidence Records Ingested in this Case</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto mb-4">
          Upload telecom CDRs, banking statements, or FIR police reports above to trigger automated entity extraction, BFS money trail layering, and lead scoring.
        </p>
      </div>
    );
  }

  // Active Selected Lead
  const activeLead = leads[selectedLeadIndex] || leads[0];

  // Derive Linked Entities from the real Graph
  const activeEntityId = activeLead.entity_id;
  const connectedEdges = graphEdges.filter(
    (e) => e.source === activeEntityId || e.target === activeEntityId
  );
  const connectedNodeIds = new Set(
    connectedEdges.map((e) => (e.source === activeEntityId ? e.target : e.source))
  );
  const connectedNodes = graphNodes.filter((n) => connectedNodeIds.has(n.id));

  // Extract Vehicles and Phones actually connected to this lead or in case
  const caseVehicles = graphNodes.filter((n) => n.label === 'Vehicle');
  const casePhones = graphNodes.filter((n) => n.label === 'Phone');
  const caseAccounts = graphNodes.filter((n) => n.label === 'BankAccount');

  // Related anomalies for this entity
  const entityAlerts = alerts.filter(
    (a) => a.entity_id === activeEntityId || connectedNodeIds.has(a.entity_id)
  );

  return (
    <div className="space-y-6 select-none font-sans">
      {/* 1. TOP STATISTICAL KPI STRIP */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="bg-[#0b1325] border border-[#1a2942] rounded-lg p-3.5 shadow-sm">
          <div className="text-[11px] font-mono text-slate-400">Total Entities</div>
          <div className="text-lg font-bold text-white mt-0.5 font-mono">
            {overview?.total_entities || graphNodes.length || 0}
          </div>
          <div className="text-[10px] text-cyan-400 font-mono mt-1">Staged in Graph</div>
        </div>

        <div className="bg-[#0b1325] border border-[#1a2942] rounded-lg p-3.5 shadow-sm">
          <div className="text-[11px] font-mono text-slate-400">Transactions</div>
          <div className="text-lg font-bold text-white mt-0.5 font-mono">
            {overview?.total_txns || 0}
          </div>
          <div className="text-[10px] text-emerald-400 font-mono mt-1">
            {formatCurrency(overview?.total_money_volume_rs || 0)}
          </div>
        </div>

        <div className="bg-[#0b1325] border border-[#1a2942] rounded-lg p-3.5 shadow-sm">
          <div className="text-[11px] font-mono text-slate-400">Call Records</div>
          <div className="text-lg font-bold text-white mt-0.5 font-mono">
            {overview?.total_calls || 0}
          </div>
          <div className="text-[10px] text-sky-400 font-mono mt-1">Telecom Ingested</div>
        </div>

        <div className="bg-[#0b1325] border border-[#1a2942] rounded-lg p-3.5 shadow-sm">
          <div className="text-[11px] font-mono text-slate-400">Tracked Vehicles</div>
          <div className="text-lg font-bold text-white mt-0.5 font-mono">
            {caseVehicles.length}
          </div>
          <div className="text-[10px] text-amber-400 font-mono mt-1">ANPR / Staged</div>
        </div>

        <div className="bg-[#0b1325] border border-[#1a2942] rounded-lg p-3.5 shadow-sm">
          <div className="text-[11px] font-mono text-slate-400">Pattern Alerts</div>
          <div className="text-lg font-bold text-rose-400 mt-0.5 font-mono">
            {alerts.length}
          </div>
          <div className="text-[10px] text-rose-400 font-mono mt-1">Anomalies Detected</div>
        </div>

        <div className="bg-[#0b1325] border border-[#1a2942] rounded-lg p-3.5 shadow-sm">
          <div className="text-[11px] font-mono text-slate-400">Evidence Files</div>
          <div className="text-lg font-bold text-white mt-0.5 font-mono">
            {evidenceFiles.length}
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-1">SHA-256 Anchored</div>
        </div>
      </div>

      {/* 2. DYNAMIC LEAD SELECTION & IDENTIFIED TARGET DOSSIER */}
      <div className="bg-[#080d19] border border-[#1a2742] rounded-xl p-5 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#16233a] pb-4 mb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Investigative Target Dossier (Ranked by Mathematical Lead Scoring)
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Rankings computed dynamically from 5 independent signals across active case data.
            </p>
          </div>

          {/* Quick Target Carousel / Switcher */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
            {leads.slice(0, 6).map((lead, idx) => (
              <button
                key={lead.id || idx}
                onClick={() => setSelectedLeadIndex(idx)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all whitespace-nowrap flex items-center gap-1.5 ${
                  selectedLeadIndex === idx
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-[#0d1629] text-slate-300 hover:text-white border border-[#19263f]'
                }`}
              >
                <span>#{idx + 1}</span>
                <span className="truncate max-w-[120px]">{lead.display_name || lead.entity_id}</span>
                <span
                  className={`text-[9px] px-1 py-0.2 rounded font-bold ${
                    lead.level === 'HIGH'
                      ? 'bg-rose-900 text-rose-200'
                      : lead.level === 'MEDIUM'
                      ? 'bg-amber-900 text-amber-200'
                      : 'bg-slate-800 text-slate-300'
                  }`}
                >
                  {lead.priority !== undefined ? `${Math.round(lead.priority)}%` : lead.level}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* 2-Column Split Dossier */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Target Profile Card (5 Cols) */}
          <div className="lg:col-span-5 bg-[#0b1426] border border-[#1b2b48] rounded-xl p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between gap-3 mb-4">
                <div>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border font-semibold bg-rose-950/70 border-rose-800 text-rose-300">
                    {activeLead.level || 'SCORED'} PRIORITY TARGET
                  </span>
                  <h3 className="text-lg font-bold text-white mt-1.5 tracking-tight">
                    {activeLead.display_name || activeLead.entity_id}
                  </h3>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">
                    Entity Type: <span className="text-cyan-400 font-semibold">{activeLead.entity_type || 'Entity'}</span> • ID: {activeLead.entity_id}
                  </p>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-xs text-slate-400 font-mono">Forensic Score</div>
                  <div className="text-2xl font-bold font-mono text-rose-400">
                    {activeLead.priority !== undefined ? `${Math.round(activeLead.priority)}%` : activeLead.confidence || 'N/A'}
                  </div>
                </div>
              </div>

              {/* Matched Anomaly Pattern if any */}
              {activeLead.matched_pattern && (
                <div className="p-3 bg-[#0d1b33] border border-blue-900/60 rounded-lg text-xs mb-4">
                  <span className="text-[10px] font-mono text-cyan-400 uppercase font-bold block">
                    Matched Crime Pattern:
                  </span>
                  <div className="text-white font-semibold mt-0.5">
                    {activeLead.matched_pattern.name || activeLead.matched_pattern.id}
                  </div>
                  <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">
                    {activeLead.matched_pattern.description}
                  </p>
                </div>
              )}

              {/* Connected Identifiers Table from Graph */}
              <div className="space-y-2 mb-4">
                <div className="text-[11px] font-mono text-slate-400 uppercase font-bold">
                  Directly Linked Entities ({connectedNodes.length}):
                </div>
                {connectedNodes.length > 0 ? (
                  <div className="grid grid-cols-1 gap-1.5 max-h-48 overflow-y-auto pr-1">
                    {connectedNodes.map((n, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between p-2 rounded bg-[#070e1c] border border-[#16233b] text-xs font-mono"
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              n.label === 'Vehicle'
                                ? 'bg-amber-400'
                                : n.label === 'Phone'
                                ? 'bg-cyan-400'
                                : n.label === 'BankAccount'
                                ? 'bg-emerald-400'
                                : 'bg-purple-400'
                            }`}
                          ></span>
                          <span className="text-slate-300 font-medium truncate max-w-[170px]">
                            {n.name || n.id}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-400 px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800">
                          {n.label}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 font-mono italic">
                    No direct peripheral entity links staged in graph.
                  </p>
                )}
              </div>
            </div>

            {/* Evidence References */}
            <div className="pt-3 border-t border-[#16233b] flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span>Evidentiary Sources: {activeLead.evidence_ids?.length || 0} File(s)</span>
              <button
                onClick={() => onOpenTab && onOpenTab('graph')}
                className="text-cyan-400 hover:text-cyan-300 underline font-semibold"
              >
                Inspect in Graph &rarr;
              </button>
            </div>
          </div>

          {/* 5-Signal Mathematical Breakdown (7 Cols) */}
          <div className="lg:col-span-7 bg-[#0b1426] border border-[#1b2b48] rounded-xl p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-[#16233b] pb-2.5 mb-4">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                  5-Signal Mathematical Verification Breakdown
                </h4>
                <span className="text-[10px] text-slate-400 font-mono">
                  Availability Principle Enforced
                </span>
              </div>

              {/* Signal Bars */}
              <div className="space-y-3.5">
                {(activeLead.signals || []).map((sig, i) => (
                  <div key={i} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-200 font-medium flex items-center gap-2">
                        <span>{sig.label || sig.name}</span>
                        {!sig.is_available && (
                          <span className="text-[9px] font-mono text-slate-500 bg-slate-900 px-1 py-0.2 rounded border border-slate-800">
                            NOT UPLOADED
                          </span>
                        )}
                      </span>
                      <span className="font-mono text-slate-300 font-semibold">
                        {sig.is_available ? `${Math.round((sig.score || 0) * 100)}%` : 'N/A'}
                      </span>
                    </div>

                    <div className="w-full bg-[#070e1c] h-2 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          !sig.is_available
                            ? 'bg-slate-700'
                            : sig.score > 0.6
                            ? 'bg-rose-500'
                            : sig.score > 0.3
                            ? 'bg-amber-500'
                            : 'bg-blue-500'
                        }`}
                        style={{ width: sig.is_available ? `${Math.max(5, (sig.score || 0) * 100)}%` : '0%' }}
                      ></div>
                    </div>

                    <p className="text-[11px] text-slate-400 leading-tight">
                      {sig.explanation}
                    </p>
                  </div>
                ))}
              </div>

              {/* Recommended Police Actions */}
              {activeLead.suggested_next_steps && activeLead.suggested_next_steps.length > 0 && (
                <div className="mt-5 p-3 bg-[#070e1c] border border-[#16233b] rounded-lg">
                  <div className="text-[10px] font-mono text-amber-400 uppercase font-bold mb-1.5">
                    Statutory Recommended Next Steps:
                  </div>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {activeLead.suggested_next_steps.map((step, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <span className="text-amber-400 text-xs mt-0.5">&bull;</span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-[#16233b] flex items-center justify-between text-xs">
              <span className="text-slate-400 font-mono text-[11px]">
                {activeLead.disclaimer || 'Lead computed via deterministic algorithms.'}
              </span>
              <button
                onClick={() => onOpenTab && onOpenTab('leads')}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg text-xs transition-colors"
              >
                Record Officer Decision &rarr;
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 3. DYNAMIC DETECTED ANOMALIES & CASE VEHICLES GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (6 Cols): Real Detected Flow Anomalies */}
        <div className="lg:col-span-6 bg-[#080d19] border border-[#1a2742] rounded-xl p-5 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-[#16233b] pb-2.5 mb-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Detected Flow & Telephonic Anomalies ({alerts.length})
              </h3>
              <span className="text-[10px] font-mono text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800 font-semibold">
                Algorithmic Flags
              </span>
            </div>

            {alerts.length > 0 ? (
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {alerts.map((al, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-[#0b1426] border border-[#1b2b48] rounded-lg text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white font-mono">{al.entity_id}</span>
                      <span
                        className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border uppercase ${
                          al.severity === 'high'
                            ? 'bg-rose-950 text-rose-300 border-rose-800'
                            : 'bg-amber-950 text-amber-300 border-amber-800'
                        }`}
                      >
                        {al.pattern_type}
                      </span>
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed">
                      {al.explanation}
                    </p>
                    {al.alert_date && (
                      <div className="text-[10px] text-slate-500 font-mono">
                        Incident Date: {al.alert_date}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 font-mono py-6 text-center italic">
                No financial or telephonic anomaly patterns flagged above configured thresholds.
              </p>
            )}
          </div>

          <div className="pt-3 border-t border-[#16233b] text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Pattern Engine: BFS Directed & MAD Call Spikes</span>
            <button
              onClick={() => onOpenTab && onOpenTab('money')}
              className="text-amber-400 hover:text-amber-300 font-medium"
            >
              Inspect Money Trail &rarr;
            </button>
          </div>
        </div>

        {/* Right Column (6 Cols): Tracked Vehicles from Uploaded Case Data */}
        <div className="lg:col-span-6 bg-[#080d19] border border-[#1a2742] rounded-xl p-5 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-[#16233b] pb-2.5 mb-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Identified Transport & Vehicle Registrations ({caseVehicles.length})
              </h3>
              <span className="text-[10px] font-mono text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800 font-semibold">
                Entity Extracted
              </span>
            </div>

            {caseVehicles.length > 0 ? (
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {caseVehicles.map((v, idx) => {
                  // Find driver or owner edges for this vehicle
                  const vEdges = graphEdges.filter((e) => e.target === v.id || e.source === v.id);
                  const drivers = vEdges.filter((e) => e.type === 'DRIVES').map((e) => e.source);
                  const owners = vEdges.filter((e) => e.type === 'OWNS').map((e) => e.source);

                  return (
                    <div
                      key={v.id || idx}
                      className="p-3 bg-[#0b1426] border border-[#1b2b48] rounded-lg text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-white font-bold font-mono text-xs">{v.name || v.id}</span>
                        <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
                          REG: {v.id}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400 bg-[#070e1c] p-2 rounded">
                        <div>
                          <span>Owner(s): </span>
                          <span className="text-slate-200 font-semibold">
                            {owners.length > 0 ? owners.join(', ') : 'Not stated'}
                          </span>
                        </div>
                        <div>
                          <span>Driver(s): </span>
                          <span className="text-amber-300 font-semibold">
                            {drivers.length > 0 ? drivers.join(', ') : 'Not stated'}
                          </span>
                        </div>
                      </div>

                      {v.source_file && (
                        <div className="text-[10px] text-slate-500 font-mono">
                          Source: {v.source_file}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-slate-500 font-mono py-6 text-center italic">
                No vehicle entities identified in the uploaded evidence for this case.
              </p>
            )}
          </div>

          <div className="pt-3 border-t border-[#16233b] text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Extracted via Deterministic Vahan Plate Regex & NER</span>
            <button
              onClick={() => onOpenTab && onOpenTab('graph')}
              className="text-cyan-400 hover:text-cyan-300 font-medium"
            >
              Explore Node Links &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
