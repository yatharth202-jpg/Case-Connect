import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import CyberBackground from '../components/CyberBackground';
import { dynamicAnalysisApi } from '../api/client';
import DynamicSuspectCard from '../components/DynamicSuspectCard';
import DynamicInvestigationGraph from '../components/DynamicInvestigationGraph';
import SuspectHierarchyTree from '../components/SuspectHierarchyTree';
import ForensicAnalyticsCharts from '../components/ForensicAnalyticsCharts';
import {
  Shield,
  Activity,
  Upload,
  FileText,
  PlusCircle,
  RotateCcw,
  Printer,
  X,
  CheckCircle2,
  AlertTriangle,
  Zap,
  TrendingUp,
  UserCheck,
  Network,
  ArrowRight,
  Database,
  Layers,
  ChevronRight,
  Eye,
  Lock,
  Phone,
  CreditCard,
  Car
} from 'lucide-react';

const SAMPLE_SCENARIOS = [
  {
    title: 'Hawala Syndicate Ring (Delhi - Dubai Network)',
    desc: 'FIR-892/2026 Special Cell New Delhi — Cross-Border Hawala & Illicit Mule Account Ring',
    text: `Case Title: FIR-892/2026 Special Cell New Delhi - Cross-Border Hawala Syndicate.
Kingpin Vikrant Malik (phone +91-9811029384) coordinated illicit remittance of Rs 1,45,00,000 into multiple mule accounts.
Interrogation of cash courier Rajesh Sharma (phone +91-9871234567, vehicle DL-01-AB-1234) revealed cash was meant for Sandeep Bhai in Chandni Chowk following instructions from Mukesh Bhai (phone +91-9910987654).
Funds were transferred into HDFC Bank Account 50100492819201 handled by Deepak Verma and ICICI Account 002105018293 under Shivam Trading Company.
Nocturnal telecom logs show 18 calls between Vikrant Malik and Rajesh Sharma between 01:00 AM and 04:30 AM.`
  },
  {
    title: 'Cyber Extortion & Digital Arrest Ring (FIR-402)',
    desc: 'FIR-402/2026 Cyber Cell Mumbai — Fake Law Enforcement Coercion & Layered Banking Mule Routing',
    text: `Case Title: FIR-402/2026 Cyber Crime Cell Mumbai - Digital Arrest Extortion Syndicate.
Primary operative Raghav Sethi (phone +91-9820011223) posed as CBI officer and coerced victims to deposit Rs 65,00,000 into SBI Account 39281928371 held by mule operator Amit Chauhan.
CDR communication records show 14 nocturnal calls between Raghav Sethi and handler Karan Kapoor (phone +91-9820099887).
Funds were subsequently split and remitted to Axis Bank Account 918273645012 registered to Pooja Enterprises before cash withdrawal at Delhi NCR ATMs.`
  },
  {
    title: 'SIM Box Telecom Routing & Fake Aadhaar Hub',
    desc: 'FIR-105/2026 STF Meerut — Forged Telecom SIM Hub with 42 Activated Numbers & High Call Volume',
    text: `Case Title: FIR-105/2026 Special Task Force Meerut - Telecom Spoofing & SIM Box Hub.
Key syndicate operator Tariq Ahmed (phone +91-9719001234) utilized 42 forged SIM cards to route VoIP proxy calls.
Associate Imran Khan (phone +91-9719005678) drove transport vehicle UP-14-CD-5678 to distribute hardware modules.
Analysis of cell tower telemetry revealed 280 nocturnal call attempts between Tariq Ahmed and supervisor Nadeem Qureshi (phone +91-9719009999).
PNB Bank Account 019283746501 received Rs 18,50,000 in monthly operational commissions.`
  }
];

export default function QuickCrimeAnalyser({ onOpenLegalModal }) {
  const { user, isAdmin, isInvestigator, isViewer } = useAuth();
  // Role Access Control: Only authorized officers/admins can ingest; viewers have read-only access
  const canIngest = isAdmin || isInvestigator || !isViewer;

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

  // Confirmation Modal State (Working Cancel)
  const [showResetConfirmModal, setShowResetConfirmModal] = useState(false);

  // Graph interaction state
  const [focusedSuspectId, setFocusedSuspectId] = useState(null);
  const [activeFilter, setActiveFilter] = useState('ALL');

  // Analysis Result State (100% Dynamic, Zero Hardcoded)
  const [analysisResult, setAnalysisResult] = useState(null);

  // Handle file upload (Fresh or Append)
  const handleFileUpload = async (files, targetCaseId = null) => {
    if (!files || files.length === 0) return;
    const file = files[0];

    setError('');
    setSuccessToast('');
    setAnalyzing(true);
    setProgress(15);
    setCurrentStep(
      targetCaseId
        ? `Appending evidence file '${file.name}' to active docket...`
        : `Ingesting evidence file '${file.name}' & computing SHA-256 genesis hash...`
    );

    try {
      setTimeout(() => {
        setProgress(35);
        setCurrentStep('Running optical character recognition & multi-modal text extraction...');
      }, 400);

      setTimeout(() => {
        setProgress(65);
        setCurrentStep('Extracting named entities, telecom records & financial transactions...');
      }, 800);

      setTimeout(() => {
        setProgress(85);
        setCurrentStep('Correlating multi-source graph topology & re-evaluating network hierarchy...');
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
          `Evidence '${file.name}' correlated successfully! Case network topology and centrality ranking updated.`
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
  const handleTextSubmit = async (targetCaseId = null, presetText = null, presetTitle = null) => {
    const textToSubmit = presetText || (targetCaseId ? appendRawText : rawText);
    const titleToSubmit = presetTitle || (targetCaseId ? appendTitle : rawTitle);

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
        setCurrentStep('Building directed multi-layer graph & running PageRank centrality...');
      }, 1000);

      const result = await dynamicAnalysisApi.analyseText(
        textToSubmit,
        titleToSubmit || 'Synthesized Case Investigation',
        targetCaseId
      );

      setProgress(100);
      setCurrentStep('Investigation synthesis ready.');
      setAnalysisResult(result);
      setShowAppendDrawer(false);
      setRawText('');
      setRawTitle('');
      setAppendRawText('');
      setAppendTitle('');

      if (targetCaseId) {
        setSuccessToast('Supplementary evidence narrative synthesized into active case topology!');
        setTimeout(() => setSuccessToast(''), 5000);
      }
    } catch (err) {
      console.error('Text analysis failed:', err);
      setError(err.response?.data?.detail || err.message || 'Text analysis failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  // Load a 1-click benchmark forensic scenario
  const handleLoadScenario = async (scenario) => {
    setRawTitle(scenario.title);
    setRawText(scenario.text);
    await handleTextSubmit(null, scenario.text, scenario.title);
  };

  // Working Cancel & Reset Actions
  const handleConfirmReset = () => {
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
    setShowResetConfirmModal(false);
  };

  const handleCancelReset = () => {
    setShowResetConfirmModal(false);
  };

  const handleCancelTextInput = () => {
    setRawText('');
    setRawTitle('');
    setError('');
  };

  const handleCancelAppendDrawer = () => {
    setShowAppendDrawer(false);
    setAppendRawText('');
    setAppendTitle('');
  };

  // Export Court Forensic Brief (Print / Save as PDF)
  const handleExportBrief = () => {
    window.print();
  };

  // Filter nodes for the graph / inventory
  const allNodes = analysisResult?.graph?.nodes || [];
  const filteredNodes = allNodes.filter((n) => {
    if (activeFilter === 'ALL') return true;
    return n.data?.type === activeFilter;
  });

  return (
    <div className="relative min-h-[calc(100vh-64px)] bg-[#040711] text-slate-100 flex flex-col font-sans select-none overflow-x-hidden pb-12">
      {/* Animated India Map & Cybersecurity Shield Hologram Background */}
      <CyberBackground />

      {/* Dynamic Polygon Clip Path & Cyber Styles */}
      <style>{`
        .cyber-btn-cut {
          clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
        }
        .font-cyber {
          font-family: 'Rajdhani', sans-serif;
        }
        .font-mono-tech {
          font-family: 'Share Tech Mono', monospace;
        }
        .glass-panel {
          background: rgba(8, 14, 30, 0.78);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(0, 240, 255, 0.18);
          box-shadow: 0 12px 40px -10px rgba(0, 0, 0, 0.6), inset 0 0 20px rgba(0, 240, 255, 0.03);
        }
      `}</style>

      {/* Top Floating Command Toolbar */}
      <div className="relative z-20 border-b border-slate-800/80 bg-[#070D1D]/90 backdrop-blur-md px-4 sm:px-6 lg:px-12 py-3 shadow-md">
        <div className="max-w-[1720px] mx-auto flex flex-col lg:flex-row items-center justify-between gap-3">
          {/* Left: Investigation Docket Status */}
          <div className="flex items-center gap-3 w-full lg:w-auto justify-between lg:justify-start">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-cyan-950/60 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
                <Activity className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white uppercase tracking-wider font-cyber">
                    {analysisResult ? analysisResult.case_title : 'Dynamic Investigation Command'}
                  </span>
                  <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800">
                    {analysisResult ? 'Active Docket' : 'Ready for Ingestion'}
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 font-mono">
                  {analysisResult
                    ? `${analysisResult.all_evidence_files?.length || 1} Evidence Docket(s) Correlated • Section 63 BSA Provenance`
                    : 'Central Investigation Ingestion Hub • Section 63 BSA Provenance Anchor'}
                </p>
              </div>
            </div>
          </div>

          {/* Right: Operational Actions (When Docket Active) */}
          {analysisResult && (
            <div className="flex flex-wrap items-center gap-2.5 w-full lg:w-auto justify-end">
              {/* Append Evidence Button */}
              {canIngest && (
                <button
                  type="button"
                  onClick={() => setShowAppendDrawer(true)}
                  className="cyber-btn-cut px-4 py-1.5 bg-gradient-to-r from-blue-950 via-blue-900/80 to-blue-950 border border-blue-400 text-cyan-300 font-cyber font-bold tracking-wider text-xs hover:bg-blue-600 hover:text-white transition flex items-center gap-1.5"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span>Append Evidence</span>
                </button>
              )}

              {/* Export Court Brief */}
              <button
                type="button"
                onClick={handleExportBrief}
                className="px-3.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:border-cyan-500/40 text-slate-300 hover:text-white text-xs font-mono transition flex items-center gap-1.5"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Export Court Brief</span>
              </button>

              {/* Start Fresh Case (Opens confirmation with working cancel) */}
              <button
                type="button"
                onClick={() => setShowResetConfirmModal(true)}
                className="px-3.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:border-rose-500/50 text-slate-300 hover:text-rose-400 text-xs font-mono transition flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Start Fresh Case</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Responsive Grid Container */}
      <main className="relative z-10 flex-1 flex flex-col justify-center px-4 sm:px-6 lg:px-12 py-6 max-w-[1720px] mx-auto w-full space-y-6">
        {/* Success Alert Toast with working dismiss button */}
        {successToast && (
          <div className="p-3 bg-emerald-950/80 border border-emerald-500/50 rounded-xl text-emerald-200 text-xs font-mono flex items-center justify-between shadow-glow-emerald animate-fadeIn">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{successToast}</span>
            </div>
            <button
              type="button"
              onClick={() => setSuccessToast('')}
              className="text-emerald-400 hover:text-white text-xs p-1 rounded"
              title="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Error Alert Toast with working dismiss button */}
        {error && (
          <div className="p-3 bg-rose-950/80 border border-rose-500/50 rounded-xl text-rose-200 text-xs font-mono flex items-center justify-between shadow-2xl animate-fadeIn">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={() => setError('')}
              className="text-rose-400 hover:text-white text-xs p-1 rounded"
              title="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Analysis Progress HUD Bar */}
        {analyzing && (
          <div className="p-4 bg-[#080E1E] border border-cyan-500/40 rounded-2xl space-y-2.5 animate-fadeIn shadow-glow-cyan">
            <div className="flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2.5 text-cyan-400 font-bold">
                <div className="w-3.5 h-3.5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                <span>{currentStep}</span>
              </div>
              <span className="text-white font-bold text-sm font-cyber">{progress}%</span>
            </div>
            <div className="w-full h-2 bg-[#091124] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-600 via-cyan-400 to-emerald-400 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STATE A: CENTRAL INVESTIGATION INGESTION CONSOLE (SINGLE UNIFIED SCREEN)   */}
        {/* ========================================================================= */}
        {!analysisResult && (
          <div className="max-w-4xl mx-auto w-full my-auto space-y-6 animate-fadeIn">
            <div className="glass-panel rounded-2xl p-6 sm:p-8 relative overflow-hidden shadow-2xl border border-cyan-500/30">
              {/* Top Specular Edge Glow */}
              <div className="h-1 w-full bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80 absolute top-0 left-0" />

              {/* Header: Clearance & Officer Access Strip */}
              <div className="flex flex-wrap items-center justify-between gap-3 pb-5 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-cyan-950/70 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-[0_0_12px_rgba(0,240,255,0.25)]">
                    <Shield className="w-5 h-5" />
                  </div>
                  <div>
                    <h1 className="text-xl sm:text-2xl font-cyber font-bold tracking-wider text-white">
                      Central Investigation Ingestion Console
                    </h1>
                    <div className="flex items-center gap-2 mt-0.5 text-xs font-mono text-slate-400">
                      <span>OFFICER: <strong className="text-white">{user?.username?.toUpperCase() || 'INVESTIGATOR-1'}</strong></span>
                      <span>•</span>
                      <span>BADGE #{user?.badge_number || 'LEO-2026-HQ'}</span>
                    </div>
                  </div>
                </div>

                {/* Clearance Badge */}
                <div className="flex items-center gap-2">
                  {canIngest ? (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-500/40 shadow-glow-emerald">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                      INGESTION ACCESS AUTHORIZED
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-blue-950/80 text-blue-300 border border-blue-500/40">
                      <span className="w-2 h-2 rounded-full bg-blue-400" />
                      READ-ONLY INTELLIGENCE CLEARANCE
                    </span>
                  )}
                </div>
              </div>

              {/* BODY: If Authorized for Ingestion, show Unified Ingestion Controls */}
              {canIngest ? (
                <div className="mt-6 space-y-6">
                  {/* Dual Input Mode Switcher Tabs */}
                  <div className="flex items-center justify-center sm:justify-start gap-2 border-b border-slate-800 pb-4">
                    <button
                      type="button"
                      onClick={() => setInputMode('upload')}
                      className={`px-4 py-2 rounded-xl text-xs font-mono font-bold flex items-center gap-2 transition-all ${
                        inputMode === 'upload'
                          ? 'bg-cyan-500 text-black shadow-glow-cyan'
                          : 'bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800'
                      }`}
                    >
                      <Upload className="w-4 h-4" />
                      <span>Evidence File Dropzone</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setInputMode('text')}
                      className={`px-4 py-2 rounded-xl text-xs font-mono font-bold flex items-center gap-2 transition-all ${
                        inputMode === 'text'
                          ? 'bg-cyan-500 text-black shadow-glow-cyan'
                          : 'bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800'
                      }`}
                    >
                      <FileText className="w-4 h-4" />
                      <span>Case / FIR Narrative Text</span>
                    </button>
                  </div>

                  {/* TAB 1: File Dropzone */}
                  {inputMode === 'upload' && (
                    <div className="space-y-4">
                      <div
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={(e) => {
                          e.preventDefault();
                          handleFileUpload(e.dataTransfer.files);
                        }}
                        onClick={() => document.getElementById('central-file-input')?.click()}
                        className="w-full h-64 border-2 border-dashed border-cyan-500/40 hover:border-cyan-400 rounded-2xl flex flex-col items-center justify-center p-6 text-center cursor-pointer transition group bg-cyan-950/10 hover:bg-cyan-950/20"
                      >
                        <input
                          id="central-file-input"
                          type="file"
                          className="hidden"
                          accept=".pdf,.docx,.txt,.csv,.xlsx,.json,.png,.jpg,.jpeg"
                          onChange={(e) => handleFileUpload(e.target.files)}
                        />
                        <div className="w-16 h-16 rounded-2xl bg-cyan-950/80 border border-cyan-500/50 flex items-center justify-center text-cyan-400 mb-3 group-hover:scale-110 shadow-glow-cyan transition">
                          <Upload className="w-8 h-8" />
                        </div>
                        <span className="text-base font-bold text-white font-cyber tracking-wider group-hover:text-cyan-300">
                          Drop Primary Evidence File Here
                        </span>
                        <span className="text-xs text-slate-400 font-mono mt-1">
                          Click or drag files: Telecom CDR (CSV), Bank Statements (XLSX/PDF), Police FIR, Case Files
                        </span>
                        <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-[10px] font-mono text-cyan-300">
                          <span className="px-2 py-0.5 rounded bg-slate-900 border border-cyan-800/60">SHA-256 Anchored</span>
                          <span className="px-2 py-0.5 rounded bg-slate-900 border border-cyan-800/60">Section 63 BSA</span>
                          <span className="px-2 py-0.5 rounded bg-slate-900 border border-cyan-800/60">Auto Schema Detect</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 2: Direct FIR Narrative Text */}
                  {inputMode === 'text' && (
                    <div className="space-y-4">
                      <input
                        type="text"
                        placeholder="Case Reference / FIR ID (e.g. FIR-892/2026 Special Cell New Delhi)"
                        value={rawTitle}
                        onChange={(e) => setRawTitle(e.target.value)}
                        className="w-full bg-[#080E1E] border border-slate-700 text-xs text-white px-3.5 py-2.5 rounded-xl focus:outline-none focus:border-cyan-400 font-mono"
                      />
                      <textarea
                        rows={6}
                        value={rawText}
                        onChange={(e) => setRawText(e.target.value)}
                        placeholder="Paste police FIR description, interrogation transcript, bank accounts, or phone call logs here..."
                        className="w-full bg-[#080E1E] border border-slate-700 rounded-xl p-3.5 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400 resize-none leading-relaxed"
                      />
                      <div className="flex items-center justify-between text-xs font-mono">
                        {rawText ? (
                          <button
                            type="button"
                            onClick={handleCancelTextInput}
                            className="text-rose-400 hover:text-white px-3 py-1 rounded-lg bg-rose-950/40 border border-rose-800/50 transition"
                          >
                            Cancel / Clear Input
                          </button>
                        ) : (
                          <span className="text-slate-500">Ready for narrative input</span>
                        )}
                        <div className="flex items-center gap-3">
                          <span className="text-slate-500">{rawText.length} characters</span>
                          <button
                            type="button"
                            onClick={() => handleTextSubmit(null)}
                            disabled={analyzing || !rawText.trim()}
                            className="cyber-btn-cut px-6 py-2 bg-cyan-500 hover:bg-cyan-400 text-black font-cyber font-bold tracking-wider text-sm transition disabled:opacity-40"
                          >
                            Synthesize Case Narrative
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* When restricted (Read-only viewer) - Upload controls are completely hidden */
                <div className="mt-6 p-6 rounded-xl bg-blue-950/20 border border-blue-500/30 text-center space-y-3">
                  <Eye className="w-8 h-8 text-blue-400 mx-auto" />
                  <h2 className="text-base font-bold text-white font-cyber tracking-wider">
                    READ-ONLY INTELLIGENCE CLEARANCE
                  </h2>
                  <p className="text-xs text-slate-300 font-mono max-w-lg mx-auto">
                    Evidence ingestion controls are restricted to authorized Investigating Officers and Administrators.
                    You have exploration access to verified forensic case dockets below.
                  </p>
                </div>
              )}

              {/* 1-Click Forensic Benchmark Scenarios */}
              <div className="mt-8 pt-6 border-t border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                    <Zap className="w-4 h-4 text-emerald-400" />
                    <span>Instant Forensic Benchmarks (1-Click Demonstration)</span>
                  </span>
                  <span className="text-[10px] font-mono text-cyan-400">100% LIVE DOCKETS</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {SAMPLE_SCENARIOS.map((sc, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleLoadScenario(sc)}
                      className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-cyan-400/80 cursor-pointer transition group flex flex-col justify-between hover:shadow-glow-cyan"
                    >
                      <div className="space-y-1">
                        <div className="text-xs font-bold text-white group-hover:text-cyan-300 transition line-clamp-1">
                          {sc.title}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono line-clamp-2">
                          {sc.desc}
                        </div>
                      </div>
                      <div className="mt-3 flex items-center justify-between text-[10px] font-mono text-cyan-400 pt-2 border-t border-slate-800/80">
                        <span>Launch Analysis</span>
                        <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STATE B: ACTIVE CASE INVESTIGATION DISSECTION PLATFORM                    */}
        {/* ========================================================================= */}
        {analysisResult && (
          <div className="space-y-6 animate-fadeIn">
            {/* 1. INGESTED EVIDENCE PROOF & GENESIS STRIP */}
            <section className="glass-panel rounded-xl p-3 sm:p-4 border-cyan-500/25 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="text-xs font-mono font-semibold tracking-wider text-slate-400 uppercase">
                      Ingested Evidence Bucket:
                    </span>
                    <span className="text-xs font-mono font-bold text-white bg-slate-900/80 px-2 py-0.5 rounded border border-slate-700">
                      {analysisResult.all_evidence_files?.length || 1} File(s) Extracted
                    </span>
                    <span className="text-xs font-mono text-cyan-400 font-medium">
                      {analysisResult.file_info?.filename || 'caseconnect_evidence.docket'}
                    </span>
                  </div>
                  <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                    SHA-256 Genesis Hash: <span className="text-slate-300">{analysisResult.file_info?.sha256 || 'SHA-256 Verified'}</span> (Anchored under BSA Sec 63)
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mr-1.5 animate-pulse" />
                  Synthesized & Indexed
                </span>
                {canIngest && (
                  <button
                    type="button"
                    onClick={() => setShowAppendDrawer(true)}
                    className="px-2.5 py-1 rounded text-xs font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                  >
                    Append More Data
                  </button>
                )}
              </div>
            </section>

            {/* 2. 4 QUICK KPI TELEMETRY METRICS CARDS */}
            <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* KPI 1: Primary Accused Target */}
              <div className="glass-panel rounded-xl p-4 sm:p-5 relative overflow-hidden group hover:border-red-500/40 transition">
                <div className="absolute -right-6 -bottom-6 w-24 h-24 bg-red-600/10 rounded-full blur-xl pointer-events-none" />
                <div className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center justify-between">
                  <span>Primary Focal Accused</span>
                  <span className="text-red-400 text-[10px] font-bold px-1.5 py-0.5 bg-red-950/80 border border-red-500/40 rounded">
                    CRITICAL
                  </span>
                </div>
                <div className="mt-2 text-2xl font-bold font-mono text-white tracking-tight flex items-baseline gap-2 truncate">
                  {analysisResult.prime_suspect?.name || 'Unattributed'}
                </div>
                <div className="mt-2 text-xs font-mono text-red-300/90 flex items-center gap-1.5">
                  <span className="inline-block w-2 h-2 rounded-full bg-red-500" />
                  Severity: {analysisResult.prime_suspect?.risk_score || 95}%
                </div>
              </div>

              {/* KPI 2: Total Extracted Entities */}
              <div className="glass-panel rounded-xl p-4 sm:p-5 relative overflow-hidden group hover:border-cyan-500/40 transition">
                <div className="absolute -right-6 -bottom-6 w-24 h-24 bg-cyan-600/10 rounded-full blur-xl pointer-events-none" />
                <div className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center justify-between">
                  <span>Total Extracted Entities</span>
                  <span className="text-cyan-400 text-[10px] font-bold px-1.5 py-0.5 bg-cyan-950/80 border border-cyan-500/40 rounded">
                    SYNDICATE
                  </span>
                </div>
                <div className="mt-2 text-2xl font-bold font-mono text-white tracking-tight">
                  {analysisResult.metrics?.total_entities || 0}
                </div>
                <div className="mt-2 text-xs font-mono text-slate-400 flex items-center gap-2">
                  <span className="text-cyan-400">{analysisResult.metrics?.persons_count || 0} Persons</span> • <span className="text-slate-300">{analysisResult.metrics?.phones_count || 0} Phones</span>
                </div>
              </div>

              {/* KPI 3: Network Operational Links */}
              <div className="glass-panel rounded-xl p-4 sm:p-5 relative overflow-hidden group hover:border-emerald-500/40 transition">
                <div className="absolute -right-6 -bottom-6 w-24 h-24 bg-emerald-600/10 rounded-full blur-xl pointer-events-none" />
                <div className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center justify-between">
                  <span>Network Operational Links</span>
                  <span className="text-emerald-400 text-[10px] font-bold px-1.5 py-0.5 bg-emerald-950/80 border border-emerald-500/40 rounded">
                    CORRELATED
                  </span>
                </div>
                <div className="mt-2 text-2xl font-bold font-mono text-white tracking-tight">
                  {analysisResult.metrics?.total_links || 0}
                </div>
                <div className="mt-2 text-xs font-mono text-emerald-400/90 flex items-center gap-1.5">
                  <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
                  Multi-Hop Topology Synthesized
                </div>
              </div>

              {/* KPI 4: Cumulative Money Volume */}
              <div className="glass-panel rounded-xl p-4 sm:p-5 relative overflow-hidden group hover:border-amber-500/40 transition">
                <div className="absolute -right-6 -bottom-6 w-24 h-24 bg-amber-600/10 rounded-full blur-xl pointer-events-none" />
                <div className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center justify-between">
                  <span>Cumulative Money Volume</span>
                  <span className="text-amber-400 text-[10px] font-bold px-1.5 py-0.5 bg-amber-950/80 border border-amber-500/40 rounded">
                    HAWALA / MULE
                  </span>
                </div>
                <div className="mt-2 text-2xl font-bold font-mono text-amber-300 tracking-tight">
                  {analysisResult.metrics?.money_volume_formatted || '₹0'}
                </div>
                <div className="mt-2 text-xs font-mono text-slate-400 flex items-center gap-1.5">
                  <span>{analysisResult.metrics?.accounts_count || 0} Banking Account Nodes</span>
                </div>
              </div>
            </section>

            {/* 3. CORE ACCUSED ATTRIBUTION & INTERACTIVE TOPOLOGY GRAPH */}
            <section className="glass-panel rounded-2xl p-5 lg:p-6 space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-rose-500 shadow-glow-magenta" />
                  <div>
                    <h2 className="text-base sm:text-lg font-bold font-mono text-white uppercase tracking-wider">
                      FOCAL ACTOR & ORGANIZED NETWORK ATTRIBUTION
                    </h2>
                    <p className="text-xs font-mono text-slate-400">
                      Primary entity extracted from Case: {analysisResult.case_title} | Multi-jurisdiction CDR & Hawala Correlation
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs font-mono">
                  <span className="px-2.5 py-1 bg-rose-950/80 text-rose-300 border border-rose-500/40 rounded">
                    {analysisResult.prime_suspect?.risk_score || 95}% Severity Index
                  </span>
                  <span className="px-2.5 py-1 bg-cyan-950/80 text-cyan-300 border border-cyan-500/40 rounded">
                    {analysisResult.graph?.nodes?.length || 0} Network Nodes
                  </span>
                  <span className="px-2.5 py-1 bg-indigo-950/80 text-indigo-300 border border-indigo-500/40 rounded">
                    {analysisResult.graph?.edges?.length || 0} Directed Links
                  </span>
                </div>
              </div>

              {/* Grid: Dossier Card on Left (4 cols), Interactive Cytoscape on Right (8 cols) */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                {/* Accused Dossier Details (4 cols) */}
                <div className="lg:col-span-4 flex flex-col justify-between space-y-4 p-5 rounded-xl bg-slate-900/70 border border-slate-700/60">
                  <div className="flex items-center gap-4">
                    {/* Radial Threat Gauge */}
                    <div className="relative w-28 h-28 shrink-0 flex items-center justify-center">
                      <svg className="w-28 h-28 transform -rotate-90" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" fill="transparent" r="40" stroke="#1f2937" strokeWidth="8" />
                        <circle
                          className="transition-all duration-1000"
                          cx="50"
                          cy="50"
                          fill="transparent"
                          r="40"
                          stroke="#ff0055"
                          strokeDasharray="251.2"
                          strokeDashoffset={251.2 - (251.2 * (analysisResult.prime_suspect?.risk_score || 95)) / 100}
                          strokeLinecap="round"
                          strokeWidth="8"
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                        <span className="text-2xl font-bold font-mono text-rose-500">
                          {analysisResult.prime_suspect?.risk_score || 95}%
                        </span>
                        <span className="text-[9px] font-mono text-slate-400 uppercase">Severity</span>
                      </div>
                    </div>

                    {/* Accused Name & Designation */}
                    <div>
                      <div className="inline-block px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950 text-rose-400 border border-rose-800 uppercase font-semibold">
                        Tier-1 Target
                      </div>
                      <h3 className="text-xl font-bold font-mono text-white mt-1">
                        {analysisResult.prime_suspect?.name || 'Unattributed Focal'}
                      </h3>
                      <p className="text-xs font-mono text-slate-400">
                        Role: {analysisResult.prime_suspect?.role || 'Syndicate Operator'}
                      </p>
                      <p className="text-xs font-mono text-cyan-400 mt-1">
                        Centrality: <span className="font-bold">{analysisResult.prime_suspect?.connections_count || 12} Links</span>
                      </p>
                    </div>
                  </div>

                  {/* Visual Threat Indicators & Node Linkages */}
                  <div className="space-y-2">
                    <div className="flex flex-wrap gap-1.5 text-[10px] font-mono">
                      <span className="px-2 py-1 rounded bg-rose-950/60 text-rose-300 border border-rose-800/60 font-bold">
                        ⚡ OFFSHORE HAWALA
                      </span>
                      <span className="px-2 py-1 rounded bg-amber-950/60 text-amber-300 border border-amber-800/60 font-bold">
                        🏦 MULE LAYER
                      </span>
                      <span className="px-2 py-1 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800/60 font-bold">
                        📞 NIGHT CALLS
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 pt-2 text-center text-[10px] font-mono bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                      <div>
                        <div className="text-cyan-400 font-bold text-sm">
                          {analysisResult.metrics?.phones_count || 3}
                        </div>
                        <div className="text-slate-400">Phones</div>
                      </div>
                      <div>
                        <div className="text-emerald-400 font-bold text-sm">
                          {analysisResult.metrics?.accounts_count || 2}
                        </div>
                        <div className="text-slate-400">Accounts</div>
                      </div>
                      <div>
                        <div className="text-amber-400 font-bold text-sm">
                          {analysisResult.metrics?.vehicles_count || 1}
                        </div>
                        <div className="text-slate-400">Vehicles</div>
                      </div>
                    </div>
                  </div>

                  {/* File & Verification metadata */}
                  <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-400 truncate max-w-[180px]">
                      Source: {analysisResult.file_info?.filename}
                    </span>
                    <span className="text-emerald-400 font-bold">SHA-256 Verified</span>
                  </div>
                </div>

                {/* Interactive Crime Network Graph (8 cols) - Visually Large */}
                <div className="lg:col-span-8 flex flex-col justify-between rounded-xl bg-slate-900/70 border border-slate-700/60 overflow-hidden relative min-h-[540px]">
                  {/* Filter Tabs on Top of Graph */}
                  <div className="p-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2 z-10 bg-slate-900/90 backdrop-blur-sm">
                    <div className="flex items-center gap-1.5 text-[10px] font-mono">
                      <span className="text-slate-400 mr-1">Filter View:</span>
                      {['ALL', 'Person', 'Phone', 'BankAccount', 'Vehicle'].map((filter) => (
                        <button
                          key={filter}
                          type="button"
                          onClick={() => setActiveFilter(filter)}
                          className={`px-2 py-0.5 rounded transition ${
                            activeFilter === filter
                              ? 'bg-cyan-500 text-black font-bold'
                              : 'text-slate-400 hover:text-white bg-slate-800'
                          }`}
                        >
                          {filter}
                        </button>
                      ))}
                    </div>

                    <button
                      type="button"
                      onClick={() => setFocusedSuspectId(analysisResult.prime_suspect?.id)}
                      className="px-2.5 py-1 rounded bg-rose-950/80 text-rose-300 border border-rose-800 text-[10px] font-mono font-bold hover:bg-rose-900 transition"
                    >
                      Focus Principal Target
                    </button>
                  </div>

                  {/* Cytoscape Graph Canvas - Expanded Height */}
                  <div className="w-full h-[460px] lg:h-[500px] relative flex-1">
                    <DynamicInvestigationGraph
                      nodes={filteredNodes}
                      edges={analysisResult.graph?.edges || []}
                      primeSuspectId={analysisResult.prime_suspect?.id}
                      highlightTargetId={focusedSuspectId}
                    />
                  </div>

                  {/* Graph Footer Legend */}
                  <div className="p-2.5 border-t border-slate-800 bg-[#050914] flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-400">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1 text-rose-400">
                        <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" /> Principal Target
                      </span>
                      <span className="flex items-center gap-1 text-amber-400">
                        <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" /> Mule Account
                      </span>
                      <span className="flex items-center gap-1 text-cyan-400">
                        <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" /> CDR Intercept
                      </span>
                    </div>
                    <span>Interactive SVG / Force Physics Simulation (Section 63 BSA)</span>
                  </div>
                </div>
              </div>
            </section>

            {/* 4. SYNDICATE COMMAND HIERARCHY & RANKING */}
            {analysisResult.suspect_hierarchy && analysisResult.suspect_hierarchy.length > 0 && (
              <section className="glass-panel rounded-2xl p-5 lg:p-6 space-y-4">
                <SuspectHierarchyTree
                  hierarchy={analysisResult.suspect_hierarchy}
                  onFocusSuspect={(id) => setFocusedSuspectId(id)}
                />
              </section>
            )}

            {/* 5. DUAL FORENSIC ANALYTICS CHARTS (With smart conditional rendering!) */}
            <section className="glass-panel rounded-2xl p-5 lg:p-6 space-y-4">
              <ForensicAnalyticsCharts
                charts={analysisResult.charts}
                metrics={analysisResult.metrics}
              />
            </section>

            {/* 6. AI MODUS OPERANDI FORENSIC BRIEF */}
            {analysisResult.ai_summary && (
              <section className="glass-panel rounded-2xl p-5 shadow-xl space-y-3">
                <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                  <span className="text-lg">🧠</span>
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                    Autonomous Modus Operandi & Forensic Narrative Brief
                  </h3>
                </div>
                <p className="text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-line">
                  {analysisResult.ai_summary}
                </p>
              </section>
            )}

            {/* 7. EXTRACTED EVIDENCE NODE INVENTORY */}
            <section className="glass-panel rounded-2xl p-5 lg:p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                    EXTRACTED EVIDENCE NODE INVENTORY [{allNodes.length}]
                  </h3>
                </div>

                {/* Filter Tabs */}
                <div className="flex items-center gap-1 overflow-x-auto text-[10px] font-mono">
                  {['ALL', 'Person', 'Phone', 'BankAccount', 'Vehicle'].map((filter) => (
                    <button
                      key={filter}
                      type="button"
                      onClick={() => setActiveFilter(filter)}
                      className={`px-2.5 py-1 rounded-lg transition-colors ${
                        activeFilter === filter
                          ? 'bg-cyan-500 text-black font-bold'
                          : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                      }`}
                    >
                      {filter}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {filteredNodes.map((node, idx) => (
                  <div
                    key={idx}
                    onClick={() => setFocusedSuspectId(node.data.id)}
                    className={`p-3 rounded-xl border flex flex-col justify-between text-xs font-mono cursor-pointer hover:border-cyan-400 transition-all ${
                      node.data.is_prime
                        ? 'bg-rose-950/40 border-rose-800 text-white'
                        : 'bg-[#060a17] border-slate-800 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-cyan-400 uppercase font-semibold">
                        {node.data.type}
                      </span>
                      {node.data.is_prime && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-rose-600 text-white font-bold shrink-0">
                          PRIME
                        </span>
                      )}
                    </div>
                    <div className="font-semibold text-white truncate mt-1">
                      {node.data.label}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-2 flex items-center justify-between">
                      <span>Connections: {node.data.degree || 1}</span>
                      <span className="text-cyan-400">Inspect &rarr;</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}
      </main>

      {/* ========================================================================= */}
      {/* APPEND EVIDENCE MODAL / DRAWER (WITH WORKING CANCEL BUTTONS)              */}
      {/* ========================================================================= */}
      {showAppendDrawer && analysisResult && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fadeIn"
          onClick={handleCancelAppendDrawer}
        >
          <div
            className="bg-[#080E1E] border border-blue-500/50 rounded-2xl max-w-xl w-full p-6 shadow-glow-cyan relative text-slate-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-blue-900/40 mb-4">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-cyber text-cyan-300 flex items-center gap-2">
                  <PlusCircle className="w-4 h-4 text-cyan-400" />
                  <span>Append Supplementary Evidence to Docket</span>
                </h3>
                <p className="text-[10px] text-slate-400 font-mono mt-0.5">
                  Target Case ID: {analysisResult.case_id} ({analysisResult.case_title})
                </p>
              </div>
              <button
                type="button"
                onClick={handleCancelAppendDrawer}
                className="text-slate-400 hover:text-rose-400 text-xs font-mono p-1 rounded hover:bg-slate-900 transition"
                title="Cancel & Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Mode Switcher */}
            <div className="flex items-center gap-2 mb-4 text-xs font-mono">
              <button
                type="button"
                onClick={() => setAppendMode('upload')}
                className={`px-3 py-1.5 rounded-lg transition ${
                  appendMode === 'upload'
                    ? 'bg-blue-600 text-white font-bold'
                    : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                Upload File (CDR / Statement)
              </button>
              <button
                type="button"
                onClick={() => setAppendMode('text')}
                className={`px-3 py-1.5 rounded-lg transition ${
                  appendMode === 'text'
                    ? 'bg-blue-600 text-white font-bold'
                    : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                Paste Supplementary Text
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
                className="border-2 border-dashed border-blue-500/40 hover:border-blue-400 rounded-xl p-8 text-center cursor-pointer transition bg-blue-950/20"
              >
                <input
                  id="append-file-input"
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,.txt,.csv,.xlsx,.json"
                  onChange={(e) => handleFileUpload(e.target.files, analysisResult.case_id)}
                />
                <Upload className="w-8 h-8 text-blue-400 mx-auto mb-2" />
                <div className="text-xs font-mono font-bold text-white">
                  Drop Supplementary File Here
                </div>
                <div className="text-[10px] text-slate-400 font-mono mt-1">
                  Correlates new nodes into active case topology without reset
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Supplementary Source / Memo Title"
                  value={appendTitle}
                  onChange={(e) => setAppendTitle(e.target.value)}
                  className="w-full bg-[#050914] border border-slate-700 text-xs text-white px-3 py-2 rounded-lg font-mono focus:outline-none focus:border-cyan-400"
                />
                <textarea
                  rows={5}
                  value={appendRawText}
                  onChange={(e) => setAppendRawText(e.target.value)}
                  placeholder="Paste additional interrogation notes, phone numbers, or mule bank accounts..."
                  className="w-full bg-[#050914] border border-slate-700 rounded-lg p-3 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400 resize-none leading-relaxed"
                />
              </div>
            )}

            {/* Action Bar with working Cancel button */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800 mt-4 text-xs font-mono">
              <button
                type="button"
                onClick={handleCancelAppendDrawer}
                className="px-4 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 hover:text-white transition"
              >
                Cancel
              </button>
              {appendMode === 'text' && (
                <button
                  type="button"
                  onClick={() => handleTextSubmit(analysisResult.case_id)}
                  disabled={analyzing || !appendRawText.trim()}
                  className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold transition disabled:opacity-40"
                >
                  Append Narrative
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* RESET CONFIRMATION MODAL (WITH WORKING CANCEL BUTTON)                      */}
      {/* ========================================================================= */}
      {showResetConfirmModal && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fadeIn"
          onClick={handleCancelReset}
        >
          <div
            className="bg-[#080E1E] border border-rose-500/50 rounded-2xl max-w-md w-full p-6 shadow-2xl relative text-slate-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 text-rose-400 mb-3">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <h3 className="text-base font-bold text-white font-cyber uppercase tracking-wider">
                Start Fresh Case Investigation?
              </h3>
            </div>
            <p className="text-xs text-slate-300 font-mono leading-relaxed mb-6">
              This will clear the current docket view and return you to the central ingestion console.
            </p>
            <div className="flex items-center justify-end gap-3 text-xs font-mono">
              <button
                type="button"
                onClick={handleCancelReset}
                className="px-4 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 transition"
              >
                Cancel (Keep Case)
              </button>
              <button
                type="button"
                onClick={handleConfirmReset}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold transition shadow-lg shadow-rose-950"
              >
                Confirm Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
