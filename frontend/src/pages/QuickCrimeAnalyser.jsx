import React, { useState } from 'react';
import { dynamicAnalysisApi } from '../api/client';
import DynamicSuspectCard from '../components/DynamicSuspectCard';
import DynamicInvestigationGraph from '../components/DynamicInvestigationGraph';
import SuspectHierarchyTree from '../components/SuspectHierarchyTree';
import ForensicAnalyticsCharts from '../components/ForensicAnalyticsCharts';

export default function QuickCrimeAnalyser() {
  // Primary Input & Upload State
  const [inputMode, setInputMode] = useState('upload'); // 'upload' | 'text'
  const [rawText, setRawText] = useState('');
  const [rawTitle, setRawTitle] = useState('');

  // Append Evidence State (Adding Evidence B, C to Case 1)
  const [showAppendDrawer, setShowAppendDrawer] = useState(false);
  const [appendMode, setAppendMode] = useState('upload'); // 'upload' | 'text'
  const [appendTitle, setAppendTitle] = useState('');
  const [appendRawText, setAppendRawText] = useState('');

  // Processing & Feedback State
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [error, setError] = useState('');
  const [successToast, setSuccessToast] = useState('');

  // Graph interaction state
  const [focusedSuspectId, setFocusedSuspectId] = useState(null);

  // Analysis Result State (100% Dynamic, Zero Hardcoded)
  const [analysisResult, setAnalysisResult] = useState(null);
  const [activeFilter, setActiveFilter] = useState('ALL');

  // Handle direct file upload (Fresh or Append)
  const handleFileUpload = async (files, targetCaseId = null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    setError('');
    setSuccessToast('');
    setAnalyzing(true);
    setProgress(15);
    setCurrentStep(
      targetCaseId
        ? `Appending evidence '${file.name}' to case docket...`
        : 'Computing cryptographic SHA-256 integrity hash...'
    );

    try {
      setTimeout(() => {
        setProgress(35);
        setCurrentStep('Running optical character recognition & multi-modal text extraction...');
      }, 400);

      setTimeout(() => {
        setProgress(65);
        setCurrentStep('Extracting criminal entities, telecom records & financial transactions...');
      }, 800);

      setTimeout(() => {
        setProgress(85);
        setCurrentStep('Correlating multi-source graph topology & re-evaluating suspect hierarchy...');
      }, 1200);

      const result = await dynamicAnalysisApi.analyseFile(
        file,
        (evt) => {
          if (evt.total) {
            const p = Math.round((evt.loaded * 100) / evt.total);
            setProgress(Math.min(90, Math.max(20, p)));
          }
        },
        targetCaseId
      );

      setProgress(100);
      setCurrentStep('Investigation synthesis ready.');
      setAnalysisResult(result);
      setShowAppendDrawer(false);

      if (targetCaseId) {
        setSuccessToast(
          `Evidence '${file.name}' correlated successfully! Case network topology and suspect ranking updated.`
        );
        setTimeout(() => setSuccessToast(''), 5000);
      }
    } catch (err) {
      console.error('File analysis failed:', err);
      setError(err.response?.data?.detail || err.message || 'Evidence file analysis failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  // Handle direct text/statement submit (Fresh or Append)
  const handleTextSubmit = async (targetCaseId = null) => {
    const textToSubmit = targetCaseId ? appendRawText : rawText;
    const titleToSubmit = targetCaseId ? appendTitle : rawTitle;

    if (!textToSubmit.trim()) {
      setError('Please enter or paste case narrative or evidence records.');
      return;
    }
    setError('');
    setSuccessToast('');
    setAnalyzing(true);
    setProgress(25);
    setCurrentStep(
      targetCaseId
        ? 'Appending narrative & cross-referencing existing case nodes...'
        : 'Parsing case narrative & Indian legal descriptors...'
    );

    try {
      setTimeout(() => {
        setProgress(60);
        setCurrentStep('Extracting named accused, phones, bank accounts & vehicles...');
      }, 500);

      setTimeout(() => {
        setProgress(85);
        setCurrentStep('Recalculating network centrality & criminal ranking...');
      }, 1000);

      const result = await dynamicAnalysisApi.analyseText(
        titleToSubmit.trim() || 'Direct Evidence Narrative',
        textToSubmit,
        targetCaseId
      );

      setProgress(100);
      setCurrentStep('Analysis complete.');
      setAnalysisResult(result);
      setShowAppendDrawer(false);
      setAppendRawText('');
      setAppendTitle('');

      if (targetCaseId) {
        setSuccessToast(
          'Narrative evidence merged successfully! Network links and prime suspect updated.'
        );
        setTimeout(() => setSuccessToast(''), 5000);
      }
    } catch (err) {
      console.error('Text analysis failed:', err);
      setError(err.response?.data?.detail || err.message || 'Analysis failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  // Reset to analyze another file
  const handleReset = () => {
    setAnalysisResult(null);
    setRawText('');
    setRawTitle('');
    setAppendRawText('');
    setAppendTitle('');
    setError('');
    setSuccessToast('');
    setProgress(0);
    setCurrentStep('');
    setFocusedSuspectId(null);
  };

  // Export Court Forensic Brief (Print / Save as PDF)
  const handleExportBrief = () => {
    window.print();
  };

  // Extract filtered nodes for inspection
  const allNodes = analysisResult?.graph?.nodes || [];
  const filteredNodes = allNodes.filter((n) => {
    if (activeFilter === 'ALL') return true;
    return n.data?.type === activeFilter;
  });

  return (
    <div className="min-h-[calc(100vh-64px)] bg-[#050914] text-slate-100 flex flex-col font-sans select-none pb-16">
      {/* Top Tactical Status Bar */}
      <div className="bg-[#070d1d] border-b border-[#14213d] px-6 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md sticky top-0 z-30 backdrop-blur-md bg-opacity-95">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-amber-600 to-yellow-400 p-0.5 flex items-center justify-center shadow-lg shadow-amber-500/10">
            <div className="w-full h-full bg-[#070d1d] rounded-md flex items-center justify-center text-amber-400 text-sm font-bold">
              ⚡
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-white tracking-wide uppercase font-mono">
                Case Connect AI <span className="text-blue-400">| Dynamic Crime Engine</span>
              </h1>
              <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800 font-bold">
                Live Ingestion
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Pure File-Driven Correlation • Multi-Evidence Staging • Section 63 BSA Provenance
            </p>
          </div>
        </div>

        {analysisResult && (
          <div className="flex flex-wrap items-center gap-2">
            {/* Append More Evidence Button */}
            <button
              onClick={() => setShowAppendDrawer(!showAppendDrawer)}
              className="px-3 py-1.5 rounded-lg bg-[#0c1833] hover:bg-blue-600 border border-blue-500/40 text-cyan-300 hover:text-white text-xs font-mono font-bold transition-all shadow-sm flex items-center gap-1.5"
            >
              <span>➕ Append More Evidence</span>
            </button>

            {/* Export Court Brief */}
            <button
              onClick={handleExportBrief}
              className="px-3 py-1.5 rounded-lg bg-[#0e172a] hover:bg-[#1e293b] border border-[#334155] text-slate-300 hover:text-white text-xs font-mono transition-colors shadow-sm flex items-center gap-1.5"
            >
              <span>📄 Export Court Brief</span>
            </button>

            {/* Start Fresh Button */}
            <button
              onClick={handleReset}
              className="px-3 py-1.5 rounded-lg bg-[#1e293b] hover:bg-rose-900/60 border border-[#334155] hover:border-rose-700 text-slate-300 hover:text-rose-200 text-xs font-mono transition-colors shadow-sm flex items-center gap-1.5"
            >
              <span>🔄 Start Fresh Case</span>
            </button>
          </div>
        )}
      </div>

      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 pt-6 flex-1 flex flex-col space-y-6">
        {/* Success Toast */}
        {successToast && (
          <div className="p-3 bg-emerald-950/80 border border-emerald-700 rounded-xl text-emerald-200 text-xs font-mono flex items-center justify-between animate-fadeIn shadow-lg">
            <div className="flex items-center gap-2">
              <span className="text-emerald-400 font-bold">✓ [SUCCESS]</span>
              <span>{successToast}</span>
            </div>
            <button onClick={() => setSuccessToast('')} className="text-emerald-400 hover:text-white text-xs">
              ✕
            </button>
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="p-3 bg-rose-950/80 border border-rose-800 rounded-xl text-rose-200 text-xs font-mono flex items-center justify-between animate-fadeIn">
            <div className="flex items-center gap-2">
              <span className="text-rose-400 font-bold">[ALERT]</span>
              <span>{error}</span>
            </div>
            <button onClick={() => setError('')} className="text-rose-400 hover:text-white text-xs">
              ✕
            </button>
          </div>
        )}

        {/* 1. INITIAL INGESTION ZONE (Shown when no active result or analyzing) */}
        {!analysisResult && (
          <div className="bg-gradient-to-b from-[#0a1226] to-[#070d1d] border border-[#172545] rounded-2xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

            <div className="flex items-center justify-between mb-6 pb-4 border-b border-[#152340]">
              <div>
                <h2 className="text-lg font-bold text-white tracking-tight">
                  Forensic Evidence Ingestion & Network Dissection
                </h2>
                <p className="text-xs text-slate-400 mt-0.5 font-mono">
                  Upload ANY police file: FIR PDF, chargesheet, telecom CDRs, bank statement, or scanned OCR image
                </p>
              </div>

              <div className="flex items-center bg-[#050914] border border-[#1b2b48] rounded-xl p-1 text-xs font-mono">
                <button
                  onClick={() => setInputMode('upload')}
                  className={`px-3 py-1.5 rounded-lg transition-all ${
                    inputMode === 'upload'
                      ? 'bg-blue-600 text-white font-semibold shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  File Upload
                </button>
                <button
                  onClick={() => setInputMode('text')}
                  className={`px-3 py-1.5 rounded-lg transition-all ${
                    inputMode === 'text'
                      ? 'bg-blue-600 text-white font-semibold shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Direct Text / FIR Paste
                </button>
              </div>
            </div>

            {inputMode === 'upload' ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  handleFileUpload(e.dataTransfer.files);
                }}
                onClick={() => document.getElementById('primary-file-input')?.click()}
                className="border-2 border-dashed border-[#20345b] hover:border-blue-400 bg-[#060a17]/80 rounded-2xl p-10 sm:p-14 text-center transition-all cursor-pointer group relative shadow-inner"
              >
                <input
                  id="primary-file-input"
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,.txt,.csv,.xlsx,.json,.png,.jpg,.jpeg"
                  onChange={(e) => handleFileUpload(e.target.files)}
                />

                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[#0d172e] group-hover:bg-blue-600/20 group-hover:scale-110 flex items-center justify-center transition-all border border-[#1f2f54] text-blue-400 shadow-lg">
                  <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.8}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                </div>

                <h3 className="text-base font-bold text-white group-hover:text-blue-300 transition-colors">
                  Drag & Drop Initial Evidence File Here, or Click to Browse
                </h3>
                <p className="text-xs text-slate-400 mt-2 max-w-md mx-auto font-mono">
                  Supports PDF (FIR & chargesheets), DOCX, TXT narratives, Banking Statements (CSV/XLSX), Telecom CDRs, and Scanned Image OCR.
                </p>

                <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-[10px] font-mono text-slate-400">
                  <span className="px-2 py-0.5 rounded bg-[#0b1428] border border-[#172747]">PDF / DOCX</span>
                  <span className="px-2 py-0.5 rounded bg-[#0b1428] border border-[#172747]">BANK CSV / CDR</span>
                  <span className="px-2 py-0.5 rounded bg-[#0b1428] border border-[#172747]">SCANNED OCR</span>
                  <span className="px-2 py-0.5 rounded bg-[#0b1428] border border-[#172747]">SHA-256 SEC. 63 BSA</span>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <input
                  type="text"
                  placeholder="Case Reference or Subject (e.g. FIR-912/2026 Special Cell Cyber Crime)"
                  value={rawTitle}
                  onChange={(e) => setRawTitle(e.target.value)}
                  className="w-full bg-[#060a17] border border-[#1f2f54] text-xs text-white px-4 py-2.5 rounded-xl focus:outline-none focus:border-blue-500 font-mono"
                />

                <textarea
                  rows={7}
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="Paste police FIR text, interrogation notes, or financial statements (e.g. 'Kingpin Vikrant Malik mobile 9876543210 transferred Rs 45,00,000 into mule account 919283746501 handled by Deepak Verma...')"
                  className="w-full bg-[#060a17] border border-[#1f2f54] rounded-xl p-4 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 leading-relaxed"
                />

                <div className="flex justify-end">
                  <button
                    onClick={() => handleTextSubmit(null)}
                    disabled={analyzing || !rawText.trim()}
                    className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-bold font-mono rounded-xl transition-all shadow-lg shadow-blue-600/30 flex items-center gap-2"
                  >
                    <span>Analyze Evidence Text &rarr;</span>
                  </button>
                </div>
              </div>
            )}

            {analyzing && (
              <div className="mt-6 p-4 bg-[#080d1d] border border-[#1e2f52] rounded-xl space-y-2.5 animate-fadeIn">
                <div className="flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center gap-2 text-cyan-400 font-bold">
                    <div className="w-3.5 h-3.5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                    <span>{currentStep}</span>
                  </div>
                  <span className="text-white font-bold">{progress}%</span>
                </div>
                <div className="w-full h-2 bg-[#0d162b] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-600 via-cyan-400 to-indigo-500 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* 2. APPEND MORE EVIDENCE DRAWER / MODAL (Appends B to Case 1) */}
        {showAppendDrawer && analysisResult && (
          <div className="bg-[#080d1d] border-2 border-blue-500/50 rounded-2xl p-6 shadow-2xl animate-fadeIn space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#182642]">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
                  <span>➕ Append Additional Evidence to Active Docket:</span>
                  <span className="text-cyan-400">{analysisResult.case_title}</span>
                </h3>
                <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                  Uploading supplementary evidence (e.g. Bank CSV, CDR logs, interrogation report) will incrementally merge entities, recalculate centrality, and update suspect ranking!
                </p>
              </div>
              <button
                onClick={() => setShowAppendDrawer(false)}
                className="text-slate-400 hover:text-white text-xs font-mono px-2 py-1 rounded bg-[#131f36]"
              >
                [CLOSE]
              </button>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono pb-2">
              <button
                onClick={() => setAppendMode('upload')}
                className={`px-3 py-1 rounded-lg ${
                  appendMode === 'upload'
                    ? 'bg-blue-600 text-white font-bold'
                    : 'bg-[#0f172a] text-slate-400 hover:text-white'
                }`}
              >
                Upload Supplementary File
              </button>
              <button
                onClick={() => setAppendMode('text')}
                className={`px-3 py-1 rounded-lg ${
                  appendMode === 'text'
                    ? 'bg-blue-600 text-white font-bold'
                    : 'bg-[#0f172a] text-slate-400 hover:text-white'
                }`}
              >
                Paste Additional Evidence Text
              </button>
            </div>

            {appendMode === 'upload' ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  handleFileUpload(e.dataTransfer.files, analysisResult.case_id);
                }}
                onClick={() => document.getElementById('append-file-input')?.click()}
                className="border-2 border-dashed border-[#233863] hover:border-blue-400 bg-[#060a17] rounded-xl p-8 text-center cursor-pointer transition-colors"
              >
                <input
                  id="append-file-input"
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,.txt,.csv,.xlsx,.json,.png,.jpg,.jpeg"
                  onChange={(e) => handleFileUpload(e.target.files, analysisResult.case_id)}
                />
                <span className="text-2xl block mb-2">📂</span>
                <p className="text-xs font-bold text-white font-mono">
                  Drop Supplementary Evidence File (Bank Statement / CDR / Supplementary FIR)
                </p>
                <p className="text-[10px] text-slate-400 font-mono mt-1">
                  Click to select file to correlate with Case ID: {analysisResult.case_id}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Supplementary Source Name (e.g. Bank CDR Batch 2 / Accused Shivam Interrogation)"
                  value={appendTitle}
                  onChange={(e) => setAppendTitle(e.target.value)}
                  className="w-full bg-[#060a17] border border-[#1f2f54] text-xs text-white px-3 py-2 rounded-xl focus:outline-none focus:border-blue-500 font-mono"
                />
                <textarea
                  rows={4}
                  value={appendRawText}
                  onChange={(e) => setAppendRawText(e.target.value)}
                  placeholder="Enter supplementary evidence statement (e.g. 'Subsequent interrogation revealed Shivam was the ultimate beneficiary of 60 Lakhs transferred from Deepak Verma...')"
                  className="w-full bg-[#060a17] border border-[#1f2f54] rounded-xl p-3 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
                <div className="flex justify-end">
                  <button
                    onClick={() => handleTextSubmit(analysisResult.case_id)}
                    disabled={analyzing || !appendRawText.trim()}
                    className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-bold font-mono rounded-xl transition-all shadow-md"
                  >
                    Merge with Existing Case &rarr;
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 3. DYNAMIC ANALYSIS RESULTS DASHBOARD */}
        {analysisResult && (
          <div className="space-y-6 animate-fadeIn">
            {/* Docket Evidence Inventory Strip */}
            <div className="bg-[#080d1d] border border-[#172545] rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
              <div className="flex items-center gap-2">
                <span className="text-base">📁</span>
                <span className="text-slate-400">Ingested Evidence Dockets:</span>
                <span className="text-cyan-300 font-bold">
                  {analysisResult.all_evidence_files?.length || 1} File(s) Correlated
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {(analysisResult.all_evidence_files || [analysisResult.file_info]).map((file, idx) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 rounded bg-[#0b1428] border border-[#1b2b48] text-[11px] text-slate-200 flex items-center gap-1.5"
                  >
                    <span className="text-blue-400">📄</span>
                    <span className="font-semibold">{file.filename}</span>
                    <span className="text-[9px] text-slate-500">({file.sha256?.slice(0, 8)}...)</span>
                  </span>
                ))}
              </div>
            </div>

            {/* Top 4 Statistical KPI Strips */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-[#080d1d] border border-[#192742] rounded-xl p-4 shadow-md">
                <div className="text-[11px] font-mono text-slate-400">Prime Suspect Target</div>
                <div className="text-base font-bold text-rose-400 mt-1 truncate">
                  {analysisResult.prime_suspect?.name || 'Unattributed'}
                </div>
                <div className="text-[10px] font-mono text-rose-400/80 mt-0.5">
                  Threat Rating: {analysisResult.prime_suspect?.risk_score || 0}% ({analysisResult.prime_suspect?.threat_level})
                </div>
              </div>

              <div className="bg-[#080d1d] border border-[#192742] rounded-xl p-4 shadow-md">
                <div className="text-[11px] font-mono text-slate-400">Total Extracted Entities</div>
                <div className="text-2xl font-bold font-mono text-white mt-1">
                  {analysisResult.metrics?.total_entities || 0}
                </div>
                <div className="text-[10px] font-mono text-cyan-400 mt-0.5">
                  {analysisResult.metrics?.persons_count || 0} Persons • {analysisResult.metrics?.phones_count || 0} Phones
                </div>
              </div>

              <div className="bg-[#080d1d] border border-[#192742] rounded-xl p-4 shadow-md">
                <div className="text-[11px] font-mono text-slate-400">Network Operational Links</div>
                <div className="text-2xl font-bold font-mono text-white mt-1">
                  {analysisResult.metrics?.total_links || 0}
                </div>
                <div className="text-[10px] font-mono text-emerald-400 mt-0.5">
                  Multi-Hop Topology Synchronized
                </div>
              </div>

              <div className="bg-[#080d1d] border border-[#192742] rounded-xl p-4 shadow-md">
                <div className="text-[11px] font-mono text-slate-400">Cumulative Money Volume</div>
                <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
                  {analysisResult.metrics?.money_volume_formatted || '₹0'}
                </div>
                <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                  {analysisResult.metrics?.accounts_count || 0} Banking Account Nodes
                </div>
              </div>
            </div>

            {/* Suspect Attribution Dossier Card */}
            <DynamicSuspectCard
              suspects={analysisResult.all_suspects}
              primeSuspect={analysisResult.prime_suspect}
              fileInfo={analysisResult.file_info}
            />

            {/* Main Interactive Network Topology Graph */}
            <div className="space-y-3">
              <div className="flex items-center justify-between bg-[#080d1d] border border-[#182640] rounded-xl px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                    Interactive Evidence Network Topology (Spacious Physics Graph)
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-slate-400">
                  {analysisResult.graph?.nodes?.length || 0} Nodes • {analysisResult.graph?.edges?.length || 0} Directed Edges
                </span>
              </div>

              <DynamicInvestigationGraph
                nodes={analysisResult.graph?.nodes}
                edges={analysisResult.graph?.edges}
                primeSuspectId={analysisResult.prime_suspect?.id}
                highlightTargetId={focusedSuspectId}
              />
            </div>

            {/* Suspect Command Hierarchy Tree (Top 5 Suspects with Reasons & Links) */}
            {analysisResult.suspect_hierarchy && analysisResult.suspect_hierarchy.length > 0 && (
              <SuspectHierarchyTree
                hierarchy={analysisResult.suspect_hierarchy}
                onFocusSuspect={(id) => setFocusedSuspectId(id)}
              />
            )}

            {/* Additional Analytics: 24-Hour Curve, Donut, Bar Charts */}
            {analysisResult.charts && (
              <ForensicAnalyticsCharts
                charts={analysisResult.charts}
                metrics={analysisResult.metrics}
              />
            )}

            {/* AI Modus Operandi & Executive Synthesis Brief */}
            <div className="bg-[#080d1d] border border-[#182640] rounded-2xl p-5 shadow-xl">
              <div className="flex items-center gap-2 border-b border-[#142036] pb-3 mb-3">
                <span className="text-base">🧠</span>
                <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                  Autonomous Modus Operandi & Forensic Narrative Brief
                </h3>
              </div>
              <p className="text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-line">
                {analysisResult.ai_summary}
              </p>
            </div>

            {/* Extracted Entity Filter & Inspection Strip */}
            <div className="bg-[#080d1d] border border-[#182640] rounded-2xl p-5 shadow-xl">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#142036] pb-3 mb-4">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                  Extracted Evidence Node Inventory ({filteredNodes.length})
                </h3>

                {/* Filter Tabs */}
                <div className="flex items-center gap-1 overflow-x-auto text-[10px] font-mono">
                  {['ALL', 'Person', 'Phone', 'BankAccount', 'Vehicle', 'FIR'].map((filter) => (
                    <button
                      key={filter}
                      onClick={() => setActiveFilter(filter)}
                      className={`px-2.5 py-1 rounded-lg transition-colors ${
                        activeFilter === filter
                          ? 'bg-blue-600 text-white font-bold'
                          : 'bg-[#0e172c] text-slate-400 hover:text-white border border-[#1b2b48]'
                      }`}
                    >
                      {filter}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2.5">
                {filteredNodes.map((node, idx) => (
                  <div
                    key={idx}
                    onClick={() => setFocusedSuspectId(node.data.id)}
                    className={`p-2.5 rounded-xl border flex items-center justify-between text-xs font-mono cursor-pointer hover:border-blue-400 transition-all ${
                      node.data.is_prime
                        ? 'bg-rose-950/40 border-rose-800 text-white'
                        : 'bg-[#0a1226] border-[#182640] text-slate-300'
                    }`}
                  >
                    <div className="truncate pr-2">
                      <div className="font-semibold text-white truncate">{node.data.label}</div>
                      <div className="text-[10px] text-slate-400">{node.data.type}</div>
                    </div>
                    {node.data.is_prime && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-600 text-white font-bold shrink-0">
                        PRIME
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
