import React, { useState } from 'react';

export default function SuspectHierarchyTree({ hierarchy = [], onFocusSuspect = null }) {
  const [expandedRank, setExpandedRank] = useState(1);

  if (!hierarchy || hierarchy.length === 0) {
    return null;
  }

  return (
    <div className="bg-[#080d1d] border border-[#192742] rounded-2xl p-5 shadow-2xl space-y-4 select-none animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#142038] pb-3">
        <div className="flex items-center gap-2.5">
          <span className="text-xl">🦹</span>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Syndicate Command Hierarchy & Top 5 Network Ranking
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              Dynamic Tier Structure based on Graph Centrality, Fund Routing, and Network Attribution
            </p>
          </div>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800">
          Ranked 1 to {hierarchy.length}
        </span>
      </div>

      {/* Tiered Entity Cards */}
      <div className="space-y-3">
        {hierarchy.map((item) => {
          const isExpanded = expandedRank === item.rank;
          const isRank1 = item.rank === 1;

          return (
            <div
              key={item.id || item.rank}
              className={`rounded-xl border transition-all duration-300 overflow-hidden ${
                isRank1
                  ? 'bg-gradient-to-r from-[#170a14] via-[#0d1224] to-[#070b1a] border-rose-800/80 shadow-lg shadow-rose-950/30'
                  : 'bg-[#060a17] border-[#16233d] hover:border-[#253961]'
              }`}
            >
              {/* Collapsed Header Bar */}
              <div
                onClick={() => setExpandedRank(isExpanded ? null : item.rank)}
                className="p-3.5 flex flex-wrap items-center justify-between gap-3 cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  {/* Rank Badge */}
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center font-mono font-bold text-xs shrink-0 shadow-md"
                    style={{
                      backgroundColor: isRank1 ? '#f43f5e' : item.tier_color || '#3b82f6',
                      color: '#ffffff'
                    }}
                  >
                    #{item.rank}
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-white font-mono hover:text-cyan-300 transition-colors">
                        {item.name}
                      </span>
                      <span
                        className="text-[9px] font-mono px-2 py-0.5 rounded font-bold uppercase tracking-wider"
                        style={{
                          backgroundColor: `${item.tier_color}22`,
                          color: item.tier_color,
                          border: `1px solid ${item.tier_color}55`
                        }}
                      >
                        {item.threat_level} THREAT
                      </span>
                    </div>

                    <div className="text-[10px] font-mono text-slate-400 mt-0.5 flex flex-wrap items-center gap-2">
                      <span className="text-cyan-300 font-semibold">{item.tier}</span>
                      <span>•</span>
                      <span>{item.role}</span>
                      <span>•</span>
                      <span>{item.connected_count || item.degree || 1} Links</span>
                    </div>
                  </div>
                </div>

                {/* Right Threat Score & Toggle */}
                <div className="flex items-center gap-4">
                  {/* Mini Risk Bar */}
                  <div className="hidden sm:flex flex-col items-end text-right">
                    <span className="text-xs font-bold font-mono text-white">
                      {item.risk_score}% Risk
                    </span>
                    <div className="w-20 h-1.5 bg-[#152340] rounded-full mt-1 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${item.risk_score}%`,
                          backgroundColor: isRank1 ? '#f43f5e' : item.tier_color || '#3b82f6'
                        }}
                      />
                    </div>
                  </div>

                  <span className="text-xs font-mono text-slate-400 hover:text-white transition-colors">
                    {isExpanded ? '▲ Hide Details' : '▼ Expand'}
                  </span>
                </div>
              </div>

              {/* Expanded Detailed Forensic Dossier */}
              {isExpanded && (
                <div className="px-4 pb-4 pt-1 border-t border-[#142038] space-y-3.5 animate-fadeIn bg-[#050814]/70">
                  {/* Reasons Section */}
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-wider text-amber-400 font-bold mb-1.5 flex items-center gap-1.5">
                      <span>📌</span>
                      <span>Evidentiary Reasons & Forensic Justification:</span>
                    </div>
                    <ul className="space-y-1 text-xs text-slate-300 bg-[#070d1d] p-3 rounded-xl border border-[#16233d]">
                      {(item.rationale || []).map((reason, i) => (
                        <li key={i} className="flex items-start gap-1.5 leading-relaxed font-mono">
                          <span className="text-rose-400 mt-0.5">▸</span>
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Connected Entity Links & Timeline */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                    {/* Direct Links */}
                    <div className="bg-[#070d1d] p-3 rounded-xl border border-[#16233d]">
                      <div className="text-[10px] uppercase text-slate-400 mb-1.5 font-bold">
                        Direct Operational Links ({item.connections?.length || 0}):
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {(item.connections || []).map((conn, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 rounded text-[10px] bg-[#0c1426] border border-[#1c2c49] text-cyan-300 truncate max-w-[170px]"
                          >
                            {conn.id} <span className="text-slate-500">({conn.rel})</span>
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Timeline & Actions */}
                    <div className="bg-[#070d1d] p-3 rounded-xl border border-[#16233d] flex flex-col justify-between">
                      <div>
                        <div className="text-[10px] uppercase text-slate-400 mb-1 font-bold">
                          Forensic Provenance & Status:
                        </div>
                        <div className="text-slate-300 text-[11px] leading-relaxed">
                          {item.timeline || 'Logged across case evidence records.'}
                        </div>
                      </div>

                      {/* Focus In Graph Button */}
                      {onFocusSuspect && (
                        <div className="mt-3 pt-2 border-t border-[#131f36] flex justify-end">
                          <button
                            onClick={() => onFocusSuspect(item.id)}
                            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition-all shadow-md shadow-blue-600/30 flex items-center gap-1.5"
                          >
                            <span>🎯 Focus & Glow in Graph &rarr;</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
