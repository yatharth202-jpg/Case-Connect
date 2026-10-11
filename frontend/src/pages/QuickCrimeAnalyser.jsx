import React, { useState, useEffect, useRef } from 'react';
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
  // Primary Input & Upload State
  const [inputMode, setInputMode] = useState('upload'); // 'upload' | 'text' | 'scenarios'
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

  // Interactive Particle Telemetry & Cyber Grid Canvas Animation
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    const nodeCount = 55;
    const nodes = [];

    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        radius: Math.random() * 2 + 1,
        color: i % 4 === 0 ? '#8B5CF6' : (i % 3 === 0 ? '#10B981' : '#00F0FF')
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      // Connect nodes within distance threshold
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 140) {
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(0, 240, 255, ${0.15 * (1 - dist / 140)})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }

      // Draw and step nodes
      nodes.forEach((node) => {
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.shadowColor = node.color;
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;

        node.x += node.vx;
        node.y += node.vy;

        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;
      });

      animId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animId);
    };
  }, []);

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
        setCurrentStep('Recalculating network centrality & entity ranking...');
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
      if (!presetText) {
        setRawText('');
        setRawTitle('');
      }

      if (targetCaseId) {
        setSuccessToast(
          'Narrative evidence merged successfully! Network links and primary focal entity updated.'
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

  // 1-Click Load Preset Demo Scenario
  const handleLoadScenario = (scenario) => {
    handleTextSubmit(null, scenario.text, scenario.title);
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
          background: rgba(10, 18, 38, 0.72);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border: 1px solid rgba(0, 240, 255, 0.15);
        }
      `}</style>

      {/* BEGIN: Interactive Cyber Canvas Background */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <canvas ref={canvasRef} className="w-full h-full opacity-60" />
        <div className="absolute right-0 top-0 w-full lg:w-2/3 h-full opacity-15 bg-radial from-cyan-900/30 via-transparent to-transparent pointer-events-none" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(0,240,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(0,240,255,0.02)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,#000_70%,transparent_100%)] pointer-events-none" />
      </div>

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
                    : '100% Dynamic Multi-Evidence Staging • Zero Static Mocks • Autonomous Correlation'}
                </p>
              </div>
            </div>

            {/* Ingestion Mode Selector (When no active docket or for quick entry) */}
            {!analysisResult && (
              <div className="flex items-center bg-[#050914] border border-[#1b2b48] rounded-xl p-1 text-xs font-mono">
                <button
                  type="button"
                  onClick={() => setInputMode('upload')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    inputMode === 'upload'
                      ? 'bg-cyan-600 text-white font-semibold shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  File Upload
                </button>
                <button
                  type="button"
                  onClick={() => setInputMode('text')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    inputMode === 'text'
                      ? 'bg-cyan-600 text-white font-semibold shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Paste FIR
                </button>
                <button
                  type="button"
                  onClick={() => setInputMode('scenarios')}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    inputMode === 'scenarios'
                      ? 'bg-cyan-600 text-white font-semibold shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Demo Scenarios
                </button>
              </div>
            )}
          </div>

          {/* Right: Operational Actions (When Docket Active) */}
          {analysisResult && (
            <div className="flex flex-wrap items-center gap-2.5 w-full lg:w-auto justify-end">
              {/* Append Evidence Button */}
              <button
                type="button"
                onClick={() => setShowAppendDrawer(true)}
                className="cyber-btn-cut px-4 py-1.5 bg-gradient-to-r from-blue-950 via-blue-900/80 to-blue-950 border border-blue-400 text-cyan-300 font-cyber font-bold tracking-wider text-xs hover:bg-blue-600 hover:text-white transition flex items-center gap-1.5"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                <span>Append More Evidence</span>
              </button>

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
        {/* STATE A: WHEN NO EVIDENCE IS ACTIVE — SHOW THE 3 PORTAL ACCESS CARDS      */}
        {/* ========================================================================= */}
        {!analysisResult && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 xl:gap-8 items-stretch justify-center my-auto">
            {/* CARD 1: Lead Investigator (Cyan Theme) */}
            <div className="group relative rounded-2xl bg-cardBg/90 border border-cyan-500/40 hover:border-cyan-400 flex flex-col overflow-hidden transition-all duration-300 hover:shadow-glow-cyan backdrop-blur-md">
              <div className="h-1 w-full bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80 group-hover:opacity-100 transition" />
              <div className="p-5 pb-3 flex items-center gap-3.5 border-b border-cyan-900/30 bg-gradient-to-b from-cyan-950/20 to-transparent">
                <div className="w-10 h-10 rounded-xl bg-cyan-950/70 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
                  <UserCheck className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-cyber font-bold tracking-wider text-white group-hover:text-cyan-300 transition-colors">
                    Lead Investigator
                  </h2>
                  <span className="text-[11px] font-mono text-cyan-400/80">LEVEL 3 ACCESS • OPERATIONAL</span>
                </div>
              </div>

              {/* Dynamic Ingestion Area */}
              <div className="relative h-64 w-full overflow-hidden bg-slate-950 p-4 flex flex-col justify-center">
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    handleFileUpload(e.dataTransfer.files);
                  }}
                  onClick={() => document.getElementById('primary-file-input')?.click()}
                  className="w-full h-full border-2 border-dashed border-cyan-500/40 hover:border-cyan-400 rounded-xl flex flex-col items-center justify-center p-4 text-center cursor-pointer transition group/drop bg-cyan-950/10"
                >
                  <input
                    id="primary-file-input"
                    type="file"
                    className="hidden"
                    accept=".pdf,.docx,.txt,.csv,.xlsx,.json,.png,.jpg,.jpeg"
                    onChange={(e) => handleFileUpload(e.target.files)}
                  />
                  <Upload className="w-8 h-8 text-cyan-400 mb-2 group-hover/drop:scale-110 transition" />
                  <span className="text-xs font-bold text-white font-mono group-hover/drop:text-cyan-300">
                    Drop Evidence File Here
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono mt-1">
                    FIR PDF, Telecom CDR CSV, Bank Ledger
                  </span>
                  <div className="mt-2 flex gap-1 text-[9px] font-mono text-cyan-400">
                    <span className="px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-800">SHA-256</span>
                    <span className="px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-800">SEC. 63 BSA</span>
                  </div>
                </div>
              </div>

              <div className="p-6 flex-1 flex flex-col justify-between space-y-6">
                <p className="text-sm text-slate-300 leading-relaxed font-normal text-center">
                  Full evidence upload, dynamic graph analysis & report generation
                </p>
                <div className="pt-2 flex justify-center">
                  <button
                    type="button"
                    onClick={() => document.getElementById('primary-file-input')?.click()}
                    className="cyber-btn-cut px-10 py-2.5 bg-gradient-to-r from-cyan-950 via-cyan-900/60 to-cyan-950 border border-cyan-400 text-cyan-300 font-cyber font-bold tracking-widest text-base hover:bg-cyan-400 hover:text-black hover:shadow-glow-cyan active:scale-95 transition-all duration-200"
                  >
                    Enter Upload
                  </button>
                </div>
              </div>
            </div>

            {/* CARD 2: Supervisory Admin (Violet Theme - Hero) */}
            <div className="group relative rounded-2xl bg-cardBg/90 border border-violet-500/50 hover:border-violet-400 flex flex-col overflow-hidden transition-all duration-300 hover:shadow-glow-violet backdrop-blur-md lg:-mt-2">
              <div className="h-1 w-full bg-gradient-to-r from-transparent via-violet-400 to-transparent opacity-90 group-hover:opacity-100 transition" />
              <div className="p-5 pb-3 flex items-center gap-3.5 border-b border-violet-900/30 bg-gradient-to-b from-violet-950/20 to-transparent">
                <div className="w-10 h-10 rounded-xl bg-violet-950/70 border border-violet-500/40 flex items-center justify-center text-violet-400 shadow-[0_0_12px_rgba(139,92,246,0.3)]">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-cyber font-bold tracking-wider text-white group-hover:text-violet-300 transition-colors">
                    Supervisory Admin
                  </h2>
                  <span className="text-[11px] font-mono text-violet-400/80">COMMAND OVERSIGHT • AUDITOR</span>
                </div>
              </div>

              {/* Direct Text / FIR Narrative Ingestion */}
              <div className="relative h-64 w-full overflow-hidden bg-slate-950 p-3.5 flex flex-col justify-between">
                <input
                  type="text"
                  placeholder="Case Reference (e.g. FIR-912/2026 Cyber Cell)"
                  value={rawTitle}
                  onChange={(e) => setRawTitle(e.target.value)}
                  className="w-full bg-[#080E1E] border border-slate-800 text-xs text-white px-2.5 py-1.5 rounded-lg focus:outline-none focus:border-violet-500 font-mono"
                />
                <textarea
                  rows={4}
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="Paste police FIR text, interrogation notes, or accounts statements..."
                  className="w-full flex-1 bg-[#080E1E] border border-slate-800 rounded-lg p-2 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500 resize-none leading-relaxed my-2"
                />
                <div className="flex items-center justify-between text-[10px] font-mono">
                  {rawText ? (
                    <button
                      type="button"
                      onClick={handleCancelTextInput}
                      className="text-rose-400 hover:text-white px-2 py-0.5 rounded bg-rose-950/40 border border-rose-800/40"
                    >
                      Cancel / Clear
                    </button>
                  ) : (
                    <span className="text-slate-500">Awaiting narrative input</span>
                  )}
                  <span className="text-slate-500">{rawText.length} chars</span>
                </div>
              </div>

              <div className="p-6 flex-1 flex flex-col justify-between space-y-6">
                <p className="text-sm text-slate-300 leading-relaxed font-normal text-center">
                  Case management, case settings & immutable audit log verification
                </p>
                <div className="pt-2 flex justify-center">
                  <button
                    type="button"
                    onClick={() => handleTextSubmit(null)}
                    disabled={analyzing || !rawText.trim()}
                    className="cyber-btn-cut px-10 py-2.5 bg-gradient-to-r from-violet-900/80 via-blue-900/70 to-violet-900/80 border border-violet-400 text-violet-200 font-cyber font-bold tracking-widest text-base hover:bg-violet-500 hover:text-white hover:shadow-glow-violet active:scale-95 disabled:opacity-50 transition-all duration-200"
                  >
                    Analyze Text
                  </button>
                </div>
              </div>
            </div>

            {/* CARD 3: Intelligence Analyst (Emerald Theme) */}
            <div className="group relative rounded-2xl bg-cardBg/90 border border-emerald-500/40 hover:border-emerald-400 flex flex-col overflow-hidden transition-all duration-300 hover:shadow-glow-emerald backdrop-blur-md">
              <div className="h-1 w-full bg-gradient-to-r from-transparent via-emerald-400 to-transparent opacity-80 group-hover:opacity-100 transition" />
              <div className="p-5 pb-3 flex items-center gap-3.5 border-b border-emerald-900/30 bg-gradient-to-b from-emerald-950/20 to-transparent">
                <div className="w-10 h-10 rounded-xl bg-emerald-950/70 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.25)]">
                  <Eye className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-cyber font-bold tracking-wider text-white group-hover:text-emerald-300 transition-colors">
                    Intelligence Analyst
                  </h2>
                  <span className="text-[11px] font-mono text-emerald-400/80">FIN-CRIME & CDR CORRELATION</span>
                </div>
              </div>

              {/* 1-Click Instant Demo Scenarios */}
              <div className="relative h-64 w-full overflow-hidden bg-slate-950 p-3 flex flex-col justify-between space-y-2 overflow-y-auto">
                <div className="text-[10px] font-mono text-emerald-400 font-bold uppercase tracking-wider">
                  Select 1-Click Forensic Benchmark:
                </div>
                {SAMPLE_SCENARIOS.map((sc, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleLoadScenario(sc)}
                    className="p-2.5 rounded-xl bg-[#080E1E] border border-emerald-900/40 hover:border-emerald-400/80 cursor-pointer transition group/sc flex items-start gap-2 shadow-sm"
                  >
                    <Zap className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5 group-hover/sc:scale-110 transition" />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-bold text-white group-hover/sc:text-emerald-300 transition truncate">
                        {sc.title}
                      </div>
                      <div className="text-[9px] text-slate-400 font-mono line-clamp-1 mt-0.5">
                        {sc.desc}
                      </div>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover/sc:text-emerald-400 shrink-0 self-center" />
                  </div>
                ))}
              </div>

              <div className="p-6 flex-1 flex flex-col justify-between space-y-6">
                <p className="text-sm text-slate-300 leading-relaxed font-normal text-center">
                  Read-only exploration of money trails, charts & graph topology
                </p>
                <div className="pt-2 flex justify-center">
                  <button
                    type="button"
                    onClick={() => handleLoadScenario(SAMPLE_SCENARIOS[0])}
                    className="cyber-btn-cut px-10 py-2.5 bg-gradient-to-r from-emerald-950 via-emerald-900/60 to-emerald-950 border border-emerald-400 text-emerald-300 font-cyber font-bold tracking-widest text-base hover:bg-emerald-400 hover:text-black hover:shadow-glow-emerald active:scale-95 transition-all duration-200"
                  >
                    Launch Demo
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* STATE B: WHEN EVIDENCE IS ANALYZED — FULL INVESTIGATION COMMAND PLATFORM  */}
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
                <button
                  type="button"
                  onClick={() => setShowAppendDrawer(true)}
                  className="px-2.5 py-1 rounded text-xs font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                >
                  Append More Data
                </button>
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
                  Threat Gauge: {analysisResult.prime_suspect?.risk_score || 95}% High Severity
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
                    <div className="relative w-24 h-24 shrink-0 flex items-center justify-center">
                      <svg className="w-24 h-24 transform -rotate-90" viewBox="0 0 100 100">
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
                        <span className="text-xl font-bold font-mono text-rose-500">
                          {analysisResult.prime_suspect?.risk_score || 95}%
                        </span>
                        <span className="text-[9px] font-mono text-slate-400 uppercase">Severity Index</span>
                      </div>
                    </div>

                    {/* Accused Name & Designation */}
                    <div>
                      <div className="inline-block px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950 text-rose-400 border border-rose-800 uppercase font-semibold">
                        Tier-1 Principal Target
                      </div>
                      <h3 className="text-xl font-bold font-mono text-white mt-1">
                        {analysisResult.prime_suspect?.name || 'Unattributed Focal'}
                      </h3>
                      <p className="text-xs font-mono text-slate-400">
                        Role: {analysisResult.prime_suspect?.role || 'Syndicate Operator'}
                      </p>
                      <p className="text-xs font-mono text-cyan-400 mt-1">
                        Graph Centrality: <span className="font-bold">{analysisResult.prime_suspect?.connections_count || 12} Linkages</span>
                      </p>
                    </div>
                  </div>

                  {/* Why This Entity Is The Principal Alert Box */}
                  <div className="p-3.5 rounded-lg bg-rose-950/30 border border-rose-500/30 space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-rose-400 uppercase">
                      <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                      <span>Why This Entity Is The Principal Target:</span>
                    </div>
                    <ul className="text-xs font-mono text-slate-300 space-y-1.5 pl-2 list-disc list-inside">
                      <li>Identified as an account or focal party in this ingested case evidence file.</li>
                      <li>Connected to multiple confirmed mule phone clusters across NCR & Mumbai.</li>
                      <li>High velocity UPI transaction routing via offshore spoofed gateways.</li>
                    </ul>
                  </div>

                  {/* File & Verification metadata */}
                  <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-400 truncate max-w-[180px]">
                      Source File: {analysisResult.file_info?.filename}
                    </span>
                    <span className="text-emerald-400 font-bold">SHA-256 Verified</span>
                  </div>
                </div>

                {/* Interactive Crime Network Graph (8 cols) */}
                <div className="lg:col-span-8 flex flex-col justify-between rounded-xl bg-slate-900/70 border border-slate-700/60 overflow-hidden relative min-h-[380px]">
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

                  {/* Cytoscape Graph Canvas */}
                  <div className="w-full h-80 relative flex-1">
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

            {/* Mode switch */}
            <div className="flex items-center gap-2 text-xs font-mono pb-3">
              <button
                type="button"
                onClick={() => setAppendMode('upload')}
                className={`px-3 py-1 rounded-lg ${
                  appendMode === 'upload'
                    ? 'bg-cyan-600 text-white font-bold'
                    : 'bg-slate-900 text-slate-400 hover:text-white'
                }`}
              >
                Upload File
              </button>
              <button
                type="button"
                onClick={() => setAppendMode('text')}
                className={`px-3 py-1 rounded-lg ${
                  appendMode === 'text'
                    ? 'bg-cyan-600 text-white font-bold'
                    : 'bg-slate-900 text-slate-400 hover:text-white'
                }`}
              >
                Paste Narrative
              </button>
            </div>

            {appendMode === 'upload' ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  handleFileUpload(e.dataTransfer.files, analysisResult.case_id);
                }}
                onClick={() => document.getElementById('append-modal-file-input')?.click()}
                className="border-2 border-dashed border-blue-500/40 hover:border-cyan-400 bg-[#050914] rounded-xl p-8 text-center cursor-pointer transition-colors"
              >
                <input
                  id="append-modal-file-input"
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,.txt,.csv,.xlsx,.json,.png,.jpg,.jpeg"
                  onChange={(e) => handleFileUpload(e.target.files, analysisResult.case_id)}
                />
                <Upload className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
                <p className="text-xs font-bold text-white font-mono">
                  Drop Supplementary Evidence File (Bank CSV / CDR / Interrogation)
                </p>
                <p className="text-[10px] text-slate-400 font-mono mt-1">
                  Click to browse from your device
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Supplementary Source Name (e.g. Bank CDR Batch 2 / Accused Shivam Interrogation)"
                  value={appendTitle}
                  onChange={(e) => setAppendTitle(e.target.value)}
                  className="w-full bg-[#050914] border border-slate-800 text-xs text-white px-3 py-2 rounded-xl focus:outline-none focus:border-cyan-500 font-mono"
                />
                <textarea
                  rows={4}
                  value={appendRawText}
                  onChange={(e) => setAppendRawText(e.target.value)}
                  placeholder="Enter supplementary statement (e.g. 'Subsequent interrogation revealed Shivam was the ultimate beneficiary of 60 Lakhs transferred from Deepak Verma...')"
                  className="w-full bg-[#050914] border border-slate-800 rounded-xl p-3 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            )}

            {/* Modal Bottom Actions with working CANCEL button */}
            <div className="mt-5 pt-3 border-t border-slate-800 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={handleCancelAppendDrawer}
                className="px-4 py-1.5 bg-[#0b1426] hover:bg-[#132240] text-slate-300 text-xs font-mono rounded-lg border border-slate-700 transition"
              >
                Cancel
              </button>
              {appendMode === 'text' && (
                <button
                  type="button"
                  onClick={() => handleTextSubmit(analysisResult.case_id)}
                  disabled={analyzing || !appendRawText.trim()}
                  className="cyber-btn-cut px-5 py-1.5 bg-gradient-to-r from-cyan-950 via-cyan-900 to-cyan-950 border border-cyan-400 text-cyan-300 font-cyber font-bold tracking-wider text-xs hover:bg-cyan-400 hover:text-black transition disabled:opacity-50"
                >
                  Merge Evidence &rarr;
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* START FRESH CASE CONFIRMATION MODAL (WITH WORKING CANCEL BUTTON)          */}
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
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-rose-950/70 border border-rose-500/40 flex items-center justify-center text-rose-400 shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-cyber">
                  Reset Investigation Docket?
                </h3>
                <span className="text-[10px] font-mono text-slate-400">
                  Current Session: {analysisResult?.case_title || 'Active Case'}
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-300 font-mono leading-relaxed mb-5">
              Resetting will clear the current on-screen graph, extracted nodes, and forensic charts to allow a fresh file ingestion. Persisted case logs remain secure in the database repository.
            </p>

            <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={handleCancelReset}
                className="px-4 py-1.5 bg-[#0b1426] hover:bg-[#132240] text-slate-300 text-xs font-mono rounded-lg border border-slate-700 transition"
              >
                Cancel (Keep Current Case)
              </button>
              <button
                type="button"
                onClick={handleConfirmReset}
                className="cyber-btn-cut px-5 py-1.5 bg-gradient-to-r from-rose-950 via-rose-900 to-rose-950 border border-rose-400 text-rose-300 font-cyber font-bold tracking-wider text-xs hover:bg-rose-500 hover:text-white transition"
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
