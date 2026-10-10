import React, { useState } from 'react';

export default function DynamicSuspectCard({ suspects = [], primeSuspect = null, fileInfo = null }) {
  const [selectedIdx, setSelectedIdx] = useState(0);

  const active = (suspects && suspects.length > 0) ? suspects[selectedIdx] : primeSuspect;

  if (!active) {
    return (
      <div className="bg-[#080d1d] border border-[#1b2b48] rounded-2xl p-6 text-center text-slate-400 font-mono text-xs">
        No suspect identified yet. Upload an investigative file to trigger autonomous criminal attribution.
      </div>
    );
  }

  // Circular gauge circumference for risk percentage
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - ((active.risk_score || 85) / 100) * circumference;

  return (
    <div className="bg-gradient-to-br from-[#0c1326] via-[#091024] to-[#060a17] border border-[#1f2f52] rounded-2xl p-5 shadow-2xl relative overflow-hidden select-none">
      {/* Background glowing ambient light */}
      <div className="absolute -top-16 -right-16 w-48 h-48 bg-rose-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-16 -left-16 w-48 h-48 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header Bar & Target Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#182642] pb-3.5 mb-4">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse"></span>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
              Criminal Nexus & Potential Criminal Attribution
            </h3>
            <p className="text-[10px] text-slate-400 font-mono">
              Forensic scoring based on graph centrality, role keywords, and evidence correlation
            </p>
          </div>
        </div>

        {/* Multi-Suspect Selector Tabs */}
        {suspects && suspects.length > 1 && (
          <div className="flex items-center gap-1 overflow-x-auto pb-0.5">
            {suspects.slice(0, 4).map((s, idx) => (
              <button
                key={s.id || idx}
                onClick={() => setSelectedIdx(idx)}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-mono transition-all whitespace-nowrap flex items-center gap-1.5 ${
                  selectedIdx === idx
                    ? 'bg-rose-600 text-white font-bold shadow-md shadow-rose-900/40'
                    : 'bg-[#0e172c] text-slate-400 hover:text-white border border-[#1b2b48]'
                }`}
              >
                <span>#{idx + 1}</span>
                <span className="truncate max-w-[90px]">{s.name}</span>
                <span className="text-[9px] opacity-75">{s.risk_score}%</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main Grid: Visual Dossier Card */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-center">
        {/* Left Column: Visual Avatar & Threat Radial Gauge (4 cols) */}
        <div className="md:col-span-4 flex items-center justify-center p-3 bg-[#070b17] border border-[#192742] rounded-xl relative">
          <div className="relative flex items-center justify-center">
            {/* SVG Circular Progress Meter */}
            <svg className="w-28 h-28 transform -rotate-90">
              <circle
                cx="56"
                cy="56"
                r={radius}
                stroke="#1e293b"
                strokeWidth="7"
                fill="transparent"
              />
              <circle
                cx="56"
                cy="56"
                r={radius}
                stroke={active.threat_level === 'CRITICAL' ? '#f43f5e' : '#f59e0b'}
                strokeWidth="7"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
                className="transition-all duration-1000 ease-out"
              />
            </svg>

            {/* Inner Avatar Graphic */}
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <div className="w-14 h-14 rounded-full bg-gradient-to-tr from-[#131d36] to-[#1f2f54] border border-[#2b3f6c] flex items-center justify-center text-rose-400 shadow-inner">
                <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.8}
                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                  />
                </svg>
              </div>
            </div>
          </div>

          <div className="ml-4">
            <span
              className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded font-bold tracking-wider inline-block ${
                active.threat_level === 'CRITICAL'
                  ? 'bg-rose-950 text-rose-300 border border-rose-800'
                  : 'bg-amber-950 text-amber-300 border border-amber-800'
              }`}
            >
              {active.threat_level || 'HIGH'} THREAT
            </span>
            <div className="text-2xl font-bold font-mono text-white mt-1">
              {active.risk_score}%
            </div>
            <div className="text-[10px] text-slate-400 font-mono">Criminal Probability</div>
          </div>
        </div>

        {/* Right Column: Suspect Details, Role, and Evidence Rationale (8 cols) */}
        <div className="md:col-span-8 space-y-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-white tracking-tight">
                {active.name}
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-950/80 text-blue-300 border border-blue-800">
                {active.role}
              </span>
            </div>
            <p className="text-[11px] font-mono text-slate-400 mt-0.5">
              Subject ID: <span className="text-slate-200">{active.id}</span> • Graph Centrality: <span className="text-cyan-400 font-bold">{active.degree || 1} links</span>
            </p>
          </div>

          {/* Rationale Checklist */}
          <div className="bg-[#070c1a] border border-[#16243d] rounded-xl p-3">
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-1.5 font-bold flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Why This Entity Is The Potential Criminal:
            </div>
            <ul className="space-y-1 text-xs text-slate-300">
              {(active.rationale || []).map((item, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-rose-400 mt-0.5">▸</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Footer Metadata */}
          {fileInfo && (
            <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[10px] font-mono text-slate-500 border-t border-[#132038]">
              <span>Source File: <span className="text-slate-300">{fileInfo.filename}</span></span>
              <span>SHA-256 Digest: <span className="text-slate-400">{fileInfo.sha256?.slice(0, 16)}...</span></span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
