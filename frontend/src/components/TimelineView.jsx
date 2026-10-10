import React, { useState, useEffect } from 'react';
import { analyticsApi } from '../api/client';

const EVENT_TYPE_CONFIG = {
  document: {
    label: 'Document / FIR',
    badgeClass: 'bg-purple-950/60 text-purple-300 border-purple-800',
    dotColor: '#a855f7',
    tag: 'DOC',
  },
  transaction_wave: {
    label: 'Transfer Wave',
    badgeClass: 'bg-emerald-950/60 text-emerald-300 border-emerald-800',
    dotColor: '#34d399',
    tag: 'TXN',
  },
  call_spike: {
    label: 'Call Spike',
    badgeClass: 'bg-rose-950/60 text-rose-300 border-rose-800',
    dotColor: '#f43f5e',
    tag: 'CDR',
  },
  alert: {
    label: 'Pattern Alert',
    badgeClass: 'bg-amber-950/60 text-amber-300 border-amber-800',
    dotColor: '#f59e0b',
    tag: 'FLAG',
  },
  lead_decision: {
    label: 'Officer Decision',
    badgeClass: 'bg-sky-950/60 text-sky-300 border-sky-800',
    dotColor: '#38bdf8',
    tag: 'DEC',
  },
};

export default function TimelineView({ caseId, isViewer }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timelineData, setTimelineData] = useState({ total_events: 0, events: [], timing_insight: null });

  // Filters
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEvent, setSelectedEvent] = useState(null);

  const fetchTimeline = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await analyticsApi.getTimeline(caseId, {
        type: activeFilter !== 'all' ? activeFilter : undefined,
        entity: searchTerm || undefined,
        limit: 500,
      });
      setTimelineData(res);
    } catch (err) {
      console.error('Failed to load timeline:', err);
      setError(err.response?.data?.detail || 'Failed to compile chronological timeline.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchTimeline();
    }
  }, [caseId, activeFilter]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchTimeline();
  };

  const { events, timing_insight } = timelineData;

  return (
    <div className="space-y-6">
      {/* 1. Header Toolbar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#0b1120] border border-[#1e293b] p-4 rounded-lg">
        <div>
          <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
            <span>⏱️</span>
            Investigative Timeline & Chronology
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Unified chronological sequence of formal documents, money waves, call spikes & officer decisions
          </p>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Search entity, account, FIR..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-[#030712] border border-[#1e293b] rounded px-3 py-1.5 text-xs text-white placeholder-slate-500 outline-none w-56 font-mono focus:border-[#38bdf8]"
          />
          <button
            type="submit"
            className="px-3 py-1.5 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded transition-colors"
          >
            Filter
          </button>
          {searchTerm && (
            <button
              type="button"
              onClick={() => {
                setSearchTerm('');
                fetchTimeline();
              }}
              className="text-xs text-slate-400 hover:text-white"
            >
              Clear
            </button>
          )}
        </form>
      </div>

      {/* 2. Pre-FIR Activity vs FIR Registration Banner (Hero Feature) */}
      {timing_insight && (
        <div
          className={`border rounded-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 ${
            timing_insight.is_pre_document_anomaly
              ? 'bg-rose-950/30 border-rose-800'
              : 'bg-sky-950/30 border-sky-800'
          }`}
        >
          <div className="flex items-start gap-3">
            <div className={`w-6 h-6 rounded flex items-center justify-center shrink-0 ${timing_insight.is_pre_document_anomaly ? 'bg-rose-900/60 text-rose-300' : 'bg-sky-900/60 text-sky-300'}`}>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                  {timing_insight.is_pre_document_anomaly
                    ? 'PRE-FIR NETWORK COORDINATION DETECTED'
                    : 'CHRONOLOGICAL SEQUENCE OVERVIEW'}
                </span>
                {timing_insight.is_pre_document_anomaly && (
                  <span className="px-1.5 py-0.5 bg-rose-900 border border-rose-700 text-rose-200 text-[10px] font-mono font-bold rounded">
                    {timing_insight.delta_days} DAYS PRIOR TO COMPLAINT
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                {timing_insight.description}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono shrink-0 bg-[#030712]/60 px-3 py-1.5 rounded border border-[#1e293b]">
            <div>
              <span className="text-slate-500 block text-[10px]">EARLIEST ANOMALY</span>
              <span className="text-rose-400 font-bold">{timing_insight.earliest_anomaly_date}</span>
            </div>
            <span className="text-slate-600">→</span>
            <div>
              <span className="text-slate-500 block text-[10px]">FIRST FORMAL FIR</span>
              <span className="text-purple-400 font-bold">{timing_insight.earliest_document_date}</span>
            </div>
          </div>
        </div>
      )}

      {/* 3. Event Type Filter Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
        {[
          { id: 'all', label: `All Events (${timelineData.total_events})` },
          { id: 'document', label: 'Documents / FIRs' },
          { id: 'transaction_wave', label: 'Transfer Waves' },
          { id: 'call_spike', label: 'Call Spikes' },
          { id: 'alert', label: 'Pattern Alerts' },
          { id: 'lead_decision', label: 'Officer Decisions' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveFilter(tab.id)}
            className={`px-3 py-1 text-xs rounded transition-colors whitespace-nowrap ${
              activeFilter === tab.id
                ? 'bg-[#0284c7] text-white font-semibold'
                : 'bg-[#0b1120] text-slate-400 hover:text-white border border-[#1e293b]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 4. Timeline Stream */}
      {loading ? (
        <div className="flex flex-col items-center justify-center p-20 space-y-3">
          <div className="w-8 h-8 border-2 border-[#38bdf8] border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs text-slate-400 font-mono">ALIGNING TEMPORAL VECTORS...</p>
        </div>
      ) : events.length === 0 ? (
        <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg p-12 text-center">
          <p className="text-sm font-semibold text-white">No timeline events found.</p>
          <p className="text-xs text-slate-400 mt-1">
            Try adjusting your search query or upload evidence documents and transactions.
          </p>
        </div>
      ) : (
        <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:inset-0 before:left-3 sm:before:left-4 before:w-0.5 before:bg-[#1e293b]">
          {events.map((ev, idx) => {
            const cfg = EVENT_TYPE_CONFIG[ev.type] || {
              label: ev.type,
              badgeClass: 'bg-slate-800 text-slate-300 border-slate-700',
              dotColor: '#94a3b8',
              tag: 'EVT',
            };

            return (
              <div key={ev.id || idx} className="relative group">
                {/* Timeline Dot Marker */}
                <div
                  className="absolute -left-6 sm:-left-8 top-3 w-4 h-4 rounded-full border-2 border-[#030712] flex items-center justify-center transition-transform group-hover:scale-125"
                  style={{ backgroundColor: cfg.dotColor }}
                ></div>

                {/* Event Card */}
                <div
                  onClick={() => setSelectedEvent(ev)}
                  className="bg-[#0b1120] border border-[#1e293b] hover:border-[#38bdf8] rounded-lg p-4 transition-all cursor-pointer shadow-lg hover:shadow-cyan-950/20"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-[#1e293b]/60 mb-2.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 font-bold">
                        {cfg.tag || 'EVT'}
                      </span>
                      <span
                        className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border font-semibold ${cfg.badgeClass}`}
                      >
                        {cfg.label}
                      </span>
                      <span className="text-xs font-bold text-white tracking-tight">
                        {ev.title}
                      </span>
                    </div>

                    <div className="text-xs font-mono text-slate-400 bg-[#030712] px-2.5 py-0.5 rounded border border-[#1e293b] shrink-0 self-start sm:self-auto">
                      {ev.timestamp}
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">{ev.summary}</p>

                  {/* Entity Chips & Provenance Tag */}
                  <div className="flex items-center justify-between gap-2 mt-3 pt-2 text-[11px] text-slate-500 font-mono">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {ev.entities && ev.entities.length > 0 && (
                        <>
                          <span className="text-slate-500">Entities:</span>
                          {ev.entities.map((ent, eIdx) => (
                            <span
                              key={eIdx}
                              className="px-1.5 py-0.5 bg-[#030712] border border-[#1e293b] text-slate-300 rounded text-[10px]"
                            >
                              {ent}
                            </span>
                          ))}
                        </>
                      )}
                    </div>

                    {ev.source_file && (
                      <span className="text-slate-500 truncate max-w-[200px]" title={ev.source_file}>
                        SRC: {ev.source_file}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 5. Event Details Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg max-w-lg w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] mb-4">
              <div>
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">
                  Evidentiary Event Inspector
                </span>
                <h3 className="text-sm font-bold text-white mt-0.5">{selectedEvent.title}</h3>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-slate-400 hover:text-white text-xs font-mono"
              >
                ✕ CLOSE
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400 block font-mono text-[11px]">Timestamp</span>
                <span className="text-white font-mono font-semibold">{selectedEvent.timestamp}</span>
              </div>
              <div>
                <span className="text-slate-400 block font-mono text-[11px]">Event Type</span>
                <span className="text-[#38bdf8] font-mono uppercase">{selectedEvent.type}</span>
              </div>
              <div>
                <span className="text-slate-400 block font-mono text-[11px]">Summary & Narrative</span>
                <p className="text-slate-200 bg-[#030712] p-2.5 rounded border border-[#1e293b] mt-1 leading-relaxed">
                  {selectedEvent.summary}
                </p>
              </div>

              {selectedEvent.source_file && (
                <div>
                  <span className="text-slate-400 block font-mono text-[11px]">Source Provenance File</span>
                  <span className="text-emerald-400 font-mono">{selectedEvent.source_file}</span>
                </div>
              )}

              {selectedEvent.details && Object.keys(selectedEvent.details).length > 0 && (
                <div>
                  <span className="text-slate-400 block font-mono text-[11px]">Raw Event Metadata</span>
                  <pre className="bg-[#030712] p-2 rounded border border-[#1e293b] text-[10px] font-mono text-slate-300 overflow-x-auto mt-1">
                    {JSON.stringify(selectedEvent.details, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-white text-xs rounded transition-colors font-semibold"
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
