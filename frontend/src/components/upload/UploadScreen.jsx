import React, { useRef } from 'react';
import { useCaseFlow } from '../../context/CaseFlowContext';
import { UploadCloud, FileText, X, ArrowRight, Shield, Database, Sparkles, AlertCircle, Clock } from 'lucide-react';

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
    <div id="intake" className="relative z-10 min-h-[calc(100vh-80px)] flex flex-col justify-center items-center px-4 sm:px-6 py-12 max-w-4xl mx-auto w-full">
      {/* Editorial Header */}
      <div className="text-center space-y-3 mb-8 max-w-xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass-sm text-[11px] font-mono text-accent">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
          <span>STAGE 01 · MULTI-SOURCE INTAKE</span>
        </div>
        <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl text-text tracking-tight">
          Drop the case files.
        </h1>
        <p className="text-sm sm:text-base text-muted font-normal max-w-md mx-auto leading-relaxed">
          FIR reports, call records (CDR), bank statements, and IP logs.
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="w-full mb-6 p-4 rounded-xl bg-alert/10 border border-alert/30 text-alert text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-alert/70 hover:text-alert">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Glass Dropzone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => fileInputRef.current?.click()}
        className="glass w-full p-8 sm:p-12 border-dashed border-2 border-white/10 hover:border-accent/40 transition-all duration-300 cursor-pointer text-center group relative overflow-hidden"
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".csv,.xlsx,.xls,.pdf,.txt,.json,.pcap"
          onChange={(e) => {
            if (e.target.files) addFiles(e.target.files);
          }}
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-14 h-14 rounded-2xl glass-sm border border-white/10 flex items-center justify-center text-accent group-hover:scale-110 transition-transform duration-300">
            <UploadCloud className="w-7 h-7" />
          </div>

          <div className="space-y-1">
            <p className="font-serif text-2xl text-text group-hover:text-accent transition-colors">
              Click to select or drag files here
            </p>
            <p className="text-xs font-mono text-muted">
              Auto-detects CDR dumps, Axis/HDFC/SBI statements, FIR PDFs, and SDR subscriber data
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
            <span className="glass-pill px-2.5 py-1 text-[10px] font-mono text-muted">CSV / EXCEL</span>
            <span className="glass-pill px-2.5 py-1 text-[10px] font-mono text-muted">FIR PDF</span>
            <span className="glass-pill px-2.5 py-1 text-[10px] font-mono text-muted">JSON / PCAP</span>
            <span className="glass-pill px-2.5 py-1 text-[10px] font-mono text-muted">MAX 200MB</span>
          </div>
        </div>
      </div>

      {/* Staged File Chips */}
      {fileQueue.length > 0 && (
        <div className="w-full mt-6 space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-muted px-1">
            <span>Staged Evidence Files ({fileQueue.length})</span>
            <span className="text-accent">Ready for Ingestion</span>
          </div>

          <div className="flex flex-wrap gap-2.5">
            {fileQueue.map((item, idx) => (
              <div
                key={idx}
                className="glass-sm px-3.5 py-2 flex items-center gap-2.5 text-xs font-mono border border-white/10"
              >
                <span className="w-2 h-2 rounded-full bg-accent" />
                <span className="text-text font-medium truncate max-w-[220px]">
                  {item.name}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-accent font-semibold">
                  [{item.type}]
                </span>
                <span className="text-muted text-[10px]">{item.size}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(idx);
                  }}
                  className="text-muted hover:text-alert p-0.5 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Case Metadata Inputs & CTA */}
      <div className="w-full mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-[11px] font-mono text-muted uppercase tracking-wider mb-1.5">
            Case Title / Docket Name
          </label>
          <input
            type="text"
            value={caseTitle}
            onChange={(e) => setCaseTitle(e.target.value)}
            placeholder="e.g. Hawala Syndicate: North Corridor Ingestion"
            className="w-full px-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/10 text-text font-mono text-xs focus:outline-none focus:border-accent"
          />
        </div>

        <div>
          <label className="block text-[11px] font-mono text-muted uppercase tracking-wider mb-1.5">
            Case Reference Number (Optional)
          </label>
          <input
            type="text"
            value={caseRefNumber}
            onChange={(e) => setCaseRefNumber(e.target.value)}
            placeholder="e.g. CR-2026-DEL-0412"
            className="w-full px-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/10 text-text font-mono text-xs focus:outline-none focus:border-accent"
          />
        </div>
      </div>

      {/* Primary Action Button */}
      <div className="w-full mt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Sample Case Quick Link */}
        <button
          type="button"
          onClick={loadSampleHawalaCase}
          className="text-xs font-mono text-muted hover:text-accent flex items-center gap-2 group transition-colors"
        >
          <Sparkles className="w-3.5 h-3.5 text-accent" />
          <span>Try sample case: <strong className="text-text group-hover:text-accent underline">Hawala syndicate dump (₹1.84 Cr)</strong></span>
        </button>

        {/* Start Analysis Button */}
        <button
          type="button"
          onClick={startDynamicAnalysis}
          disabled={fileQueue.length === 0}
          className={`px-8 py-3 rounded-xl font-mono text-xs font-medium uppercase tracking-wider flex items-center gap-2.5 transition-all duration-200 ${
            fileQueue.length > 0
              ? 'bg-accent text-ink hover:bg-accent/90 shadow-glow-accent cursor-pointer'
              : 'bg-white/5 text-muted/50 border border-white/5 cursor-not-allowed'
          }`}
        >
          <span>Analyse Case</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Recent Cases Strip */}
      {recentCases.length > 0 && (
        <div className="w-full mt-12 pt-6 border-t border-white/[0.06]">
          <div className="flex items-center gap-2 text-xs font-mono text-muted mb-3">
            <Clock className="w-3.5 h-3.5 text-accent" />
            <span>Recent Forensic Dockets:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {recentCases.map((c) => (
              <button
                key={c.id}
                onClick={() => loadCaseById(c.id)}
                className="glass-pill px-3 py-1.5 flex items-center gap-2 text-xs font-mono text-muted hover:text-text hover:border-accent/40 transition-all text-left"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-data" />
                <span className="truncate max-w-[200px]">{c.title || `Case ${c.id.slice(0, 8)}`}</span>
                <span className="text-[10px] text-accent/80 font-bold">Open →</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default UploadScreen;
