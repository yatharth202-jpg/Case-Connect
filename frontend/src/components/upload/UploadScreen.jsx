import React, { useRef } from 'react';
import { useCaseFlow } from '../../context/CaseFlowContext';
import {
  Fingerprint,
  FileText,
  X,
  ArrowRight,
  Shield,
  Sparkles,
  AlertCircle,
  Clock,
  CheckCircle2,
  Lock,
  Terminal,
  FolderOpen,
  FileSpreadsheet,
  FileCode,
  Tag,
  BookOpen
} from 'lucide-react';

export const UploadScreen = () => {
  const fileInputRef = useRef(null);
  const {
    fileQueue,
    addFiles,
    removeFile,
    caseTitle,
    setCaseTitle,
    caseRefNumber,
    setCaseRefNumber,
    startDynamicAnalysis,
    loadSampleHawalaCase,
    loadCaseById,
    recentCases,
    error,
    setError
  } = useCaseFlow();

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  return (
    <div id="intake" className="w-full pt-6 pb-16 flex-1 relative bg-[#07090e] text-[#f1f5f9] select-none">
      
      {/* Interactive Tactical Cyber Topology Canvas & Background Vectors */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {/* Grid pattern base */}
        <div className="absolute inset-0 opacity-[0.035] bg-[radial-gradient(#00e5ff_1px,transparent_1px)] [background-size:28px_28px]" />
        
        {/* Soft tactical radial glows */}
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[980px] h-[580px] bg-gradient-to-b from-cyan-500/10 via-cyan-500/5 to-transparent blur-3xl opacity-60" />
        <div className="absolute top-1/3 -left-32 w-80 h-80 bg-teal-500/10 rounded-full blur-[100px]" />
        <div className="absolute top-1/4 -right-32 w-96 h-96 bg-cyan-400/10 rounded-full blur-[120px]" />

        {/* Abstract Cyber Topology Vector Network */}
        <svg className="absolute inset-0 w-full h-full opacity-35">
          <defs>
            <linearGradient id="cyberGrad" x1="0%" x2="100%" y1="0%" y2="100%">
              <stop offset="0%" stopColor="#00daf3" stopOpacity="0.7" />
              <stop offset="60%" stopColor="#00e5ff" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0.05" />
            </linearGradient>
            <pattern height="60" id="telemetryGrid" patternUnits="userSpaceOnUse" width="60">
              <circle cx="30" cy="30" fill="#00e5ff" fillOpacity="0.3" r="0.75" />
              <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#21262D" strokeOpacity="0.3" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect fill="url(#telemetryGrid)" height="100%" width="100%" />
          
          {/* Telemetry Radar Rings & Azimuth Circles */}
          <circle cx="50%" cy="38%" fill="none" r="220" stroke="#00e5ff" strokeDasharray="4 8" strokeOpacity="0.2" strokeWidth="0.5" />
          <circle cx="50%" cy="38%" fill="none" r="380" stroke="#00e5ff" strokeDasharray="2 12" strokeOpacity="0.12" strokeWidth="0.7" />
          <circle cx="50%" cy="38%" fill="none" r="540" stroke="#21262D" strokeOpacity="0.35" strokeWidth="1" />
          
          {/* Crosshairs */}
          <line stroke="#00daf3" strokeDasharray="3 6" strokeOpacity="0.15" strokeWidth="0.5" x1="50%" x2="50%" y1="6%" y2="70%" />
          <line stroke="#00daf3" strokeDasharray="3 6" strokeOpacity="0.15" strokeWidth="0.5" x1="15%" x2="85%" y1="38%" y2="38%" />
          
          {/* Constellation Nodes & Evidence Packet Routes */}
          <g fill="none" stroke="url(#cyberGrad)" strokeLinejoin="round" strokeWidth="1.2">
            <path className="animate-pulse" d="M 240 240 L 360 210 L 520 280 L 640 230 L 780 320 L 920 280 L 1080 340" />
            <path d="M 360 210 L 420 380 L 580 430 L 780 320 L 890 460" strokeDasharray="3 5" strokeOpacity="0.5" />
            <path d="M 180 420 L 320 460 L 420 380 L 640 230" strokeOpacity="0.3" />
            <path d="M 920 280 L 1020 200 L 1180 250 L 1080 340 L 1220 420" strokeOpacity="0.4" />
          </g>

          {/* Tactical Node Markers with Cyan Glow */}
          <g fill="#07090E" stroke="#00e5ff" strokeWidth="1.5">
            <circle cx="240" cy="240" r="3.5" />
            <circle cx="360" cy="210" r="4.5" />
            <circle cx="520" cy="280" r="5" />
            <circle cx="640" cy="230" r="4" />
            <circle cx="780" cy="320" r="6" />
            <circle cx="920" cy="280" r="4.5" />
            <circle cx="1080" cy="340" r="5" />
            <circle cx="420" cy="380" r="3.5" />
            <circle cx="580" cy="430" r="4.5" />
            <circle cx="890" cy="460" r="3.5" />
          </g>
        </svg>
      </div>

      {/* Main Hero Ingestion Section */}
      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col items-center">
        
        {/* STAGE 01 BADGE */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded border border-[#21262d] bg-[#0c0e13]/90 shadow-inner mb-5">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          <span className="font-mono text-[11px] tracking-wider uppercase text-cyan-400 font-semibold">
            CYBER FORENSIC INGESTION TERMINAL
          </span>
          <div className="h-3 w-px bg-slate-700 mx-1" />
          <span className="font-mono text-[10px] text-slate-400">PORTAL SEC-BSA-V4</span>
        </div>

        {/* MAIN EDITORIAL HEADLINE */}
        <h1 className="text-3xl sm:text-4xl md:text-[38px] font-bold text-white text-center tracking-tight mb-2 uppercase font-sans">
          Multi-Source Evidence Ingestion
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 text-center max-w-2xl mb-8 font-mono leading-relaxed">
          Upload CDR telecom dumps, IPDR logs, banking statements, and FIR case dockets for automated synthesis.
        </p>

        {/* Error Banner */}
        {error && (
          <div className="w-full max-w-3xl mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-mono flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-red-400/80 hover:text-red-300">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* INTAKE CONTAINER & FILE ZONE */}
        <div className="w-full max-w-3xl flex flex-col gap-6">
          
          {/* Drag & Drop Forensic Upload Zone */}
          <div
            id="drop-zone"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => fileInputRef.current?.click()}
            className="relative group cursor-pointer rounded-lg bg-[#0c0e13]/90 border border-[#21262d] p-6 sm:p-8 transition-all duration-300 shadow-xl hover:border-cyan-400/70 hover:shadow-[0_0_35px_rgba(0,229,255,0.15)]"
          >
            {/* 4 Tactical Corner Brackets */}
            <div className="absolute top-2 left-2 w-3 h-3 border-t-2 border-l-2 border-cyan-400" />
            <div className="absolute top-2 right-2 w-3 h-3 border-t-2 border-r-2 border-cyan-400" />
            <div className="absolute bottom-2 left-2 w-3 h-3 border-b-2 border-l-2 border-cyan-400" />
            <div className="absolute bottom-2 right-2 w-3 h-3 border-b-2 border-r-2 border-cyan-400" />

            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".csv,.xlsx,.xls,.pdf,.txt,.json,.pcap,.zip,.jpg,.jpeg,.png,.tiff,.webp"
              onChange={(e) => {
                if (e.target.files) addFiles(e.target.files);
              }}
              className="hidden"
            />

            <div className="flex flex-col items-center text-center relative z-10">
              <div className="relative w-14 h-14 rounded-lg bg-[#161b22] border border-[#30363d] flex items-center justify-center mb-3 shadow-inner group-hover:scale-105 transition-transform">
                <Fingerprint className="w-7 h-7 text-cyan-400" />
              </div>

              <h2 className="text-base sm:text-lg font-semibold text-white tracking-wide mb-1 uppercase font-sans">
                Select or drag forensic evidence artifacts
              </h2>
              <p className="text-xs text-slate-400 max-w-lg mb-4 font-mono">
                Supports Telecom CDR/IPDR, Axis/HDFC/SBI Ledger Dockets, Scanned FIR PDFs, and Cryptographic Enclosures
              </p>

              {/* File Format Chips */}
              <div className="flex flex-wrap items-center justify-center gap-2">
                <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#161b22] text-cyan-300 border border-[#30363d] uppercase font-semibold">
                  CDR / CSV / XLS
                </span>
                <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#161b22] text-slate-300 border border-[#30363d] uppercase">
                  SCANNED FIR PDF
                </span>
                <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#161b22] text-slate-300 border border-[#30363d] uppercase">
                  IP LOGS / TAR / ZIP
                </span>
                <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#161b22] text-slate-300 border border-[#30363d] uppercase">
                  MEDIA EVIDENCE
                </span>
                <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#161b22] text-slate-400 border border-[#30363d] uppercase">
                  LIMIT 200MB
                </span>
              </div>

              {/* Staged Files Preview Area */}
              {fileQueue.length > 0 && (
                <div className="w-full mt-5 pt-4 border-t border-dashed border-[#21262d] text-left">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[11px] text-cyan-400 font-semibold uppercase">
                      Ingestion Queue ({fileQueue.length} items buffered)
                    </span>
                    <span className="font-mono text-[10px] text-emerald-400 font-semibold">
                      SHA-256 CHECK READY
                    </span>
                  </div>

                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {fileQueue.map((item, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between px-3 py-1.5 rounded bg-[#161b22] text-white text-xs font-mono border border-[#30363d]"
                      >
                        <span className="flex items-center gap-2 truncate max-w-[400px]">
                          {item.type === 'BANK' ? (
                            <FileSpreadsheet className="w-4 h-4 text-emerald-400 shrink-0" />
                          ) : item.type === 'CDR' ? (
                            <FileCode className="w-4 h-4 text-cyan-400 shrink-0" />
                          ) : (
                            <FileText className="w-4 h-4 text-amber-400 shrink-0" />
                          )}
                          <span className="truncate">{item.name}</span>
                        </span>

                        <div className="flex items-center gap-2">
                          <span className="text-slate-400 text-[10px]">{item.size}</span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              removeFile(idx);
                            }}
                            className="text-slate-400 hover:text-red-400 p-0.5 transition-colors"
                            title="Remove file"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Case Metadata Configuration Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Case Title Field */}
            <div className="flex flex-col gap-1.5">
              <label className="font-mono text-[11px] text-slate-300 uppercase tracking-wider flex items-center justify-between" htmlFor="case-title">
                <span>CASE TITLE / DOCKET NAME</span>
                <span className="text-cyan-400 text-[9px] font-mono">[MANDATORY]</span>
              </label>
              <div className="relative flex items-center">
                <BookOpen className="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" />
                <input
                  id="case-title"
                  type="text"
                  value={caseTitle}
                  onChange={(e) => setCaseTitle(e.target.value)}
                  placeholder="e.g. Hawala Syndicate: North Corridor Ingestion"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#0d1117] text-white placeholder:text-slate-500 font-mono text-xs border border-[#30363d] focus:outline-none focus:border-cyan-400 focus:bg-[#161b22] transition-all shadow-inner"
                />
              </div>
            </div>

            {/* Case Reference Field */}
            <div className="flex flex-col gap-1.5">
              <label className="font-mono text-[11px] text-slate-400 uppercase tracking-wider flex items-center justify-between" htmlFor="case-ref">
                <span>CASE REFERENCE NUMBER (OPTIONAL)</span>
                <span className="text-slate-500 text-[9px] font-mono">POLICE CCMS / CCTNS</span>
              </label>
              <div className="relative flex items-center">
                <Tag className="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" />
                <input
                  id="case-ref"
                  type="text"
                  value={caseRefNumber}
                  onChange={(e) => setCaseRefNumber(e.target.value)}
                  placeholder="e.g. CR-2026-DEL-0412"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#0d1117] text-white placeholder:text-slate-500 font-mono text-xs border border-[#30363d] focus:outline-none focus:border-cyan-400 focus:bg-[#161b22] transition-all shadow-inner"
                />
              </div>
            </div>
          </div>

          {/* Quick Sample Case Action Bar & Primary CTA */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-1">
            {/* Sample Ingestion Shortcut Button */}
            <button
              id="sample-pill-btn"
              type="button"
              onClick={loadSampleHawalaCase}
              className="group flex items-center gap-2.5 px-4 py-2.5 rounded-lg bg-[#0d1117] hover:bg-[#161b22] border border-[#30363d] hover:border-amber-500/50 transition-all text-left shadow-sm"
            >
              <Sparkles className="w-4 h-4 text-amber-400 group-hover:rotate-12 transition-transform" />
              <span className="text-xs font-mono text-slate-300">
                Try sample case:{' '}
                <span className="underline decoration-amber-400/50 underline-offset-4 text-white group-hover:text-amber-300 font-semibold transition-colors">
                  Hawala syndicate dump (₹1.84 Cr)
                </span>
              </span>
            </button>

            {/* Primary High-Impact Tactical CTA Button */}
            <button
              id="analyse-btn"
              type="button"
              onClick={startDynamicAnalysis}
              disabled={fileQueue.length === 0}
              className={`w-full sm:w-auto px-6 py-2.5 rounded font-mono text-xs font-bold tracking-wider flex items-center justify-center gap-2 transition-all shadow-md uppercase ${
                fileQueue.length > 0
                  ? 'bg-cyan-400 text-slate-950 hover:bg-cyan-300 hover:shadow-[0_0_20px_rgba(0,229,255,0.4)] active:scale-95 cursor-pointer'
                  : 'bg-slate-800 text-slate-500 border border-slate-700/50 cursor-not-allowed'
              }`}
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>INITIATE CASE ANALYSIS</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Recent Stored Dockets Bar */}
          {recentCases && recentCases.length > 0 && (
            <div className="w-full mt-4 pt-4 border-t border-[#21262d]">
              <div className="flex items-center gap-2 text-xs font-mono text-slate-400 mb-2.5">
                <Clock className="w-3.5 h-3.5 text-cyan-400" />
                <span>Recent Stored Forensic Dockets:</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {recentCases.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => loadCaseById(c.id)}
                    className="px-3 py-1.5 rounded-lg bg-[#0d1117] hover:bg-[#161b22] border border-[#30363d] hover:border-cyan-400/40 text-xs font-mono text-slate-300 hover:text-white flex items-center gap-2 transition-all"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    <span className="truncate max-w-[220px]">{c.title || `Docket ${c.id.slice(0, 8)}`}</span>
                    <span className="text-[10px] text-cyan-400 font-bold">Open →</span>
                  </button>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Bottom System Compliance & Security Architecture Section */}
      <div className="relative z-10 w-full mt-8 bg-[#0c0e13]/90 border-t border-[#21262d] pt-5 pb-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto flex flex-col items-center text-center">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded bg-cyan-400" />
            <span className="font-mono text-xs text-cyan-400 tracking-widest uppercase font-bold">
              UNIT-X FORENSIC ENGINE
            </span>
            <span className="text-slate-600">•</span>
            <span className="font-mono text-xs text-slate-300 uppercase">
              CYBER CRIME &amp; INTELLIGENCE CELL
            </span>
          </div>
          <p className="font-mono text-xs text-slate-400 max-w-2xl mb-3">
            Automated CDR, Banking &amp; FIR Telemetry Engine • Section 63 BSA 2023 &amp; DPDP Compliant
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4 text-slate-400 font-mono text-[11px] pt-1">
            <span className="inline-flex items-center gap-1.5 text-cyan-400">
              <Shield className="w-3.5 h-3.5" />
              AIR-GAPPED LEDGER
            </span>
            <span className="text-slate-600">•</span>
            <span className="inline-flex items-center gap-1.5 text-slate-400">
              <Terminal className="w-3.5 h-3.5" />
              SHA-256 GENESIS ANCHORED
            </span>
            <span className="text-slate-600">•</span>
            <span className="inline-flex items-center gap-1.5 text-slate-400">
              <Lock className="w-3.5 h-3.5" />
              LEO AUTHORIZED INGESTION
            </span>
          </div>
        </div>
      </div>

    </div>
  );
};

export default UploadScreen;
