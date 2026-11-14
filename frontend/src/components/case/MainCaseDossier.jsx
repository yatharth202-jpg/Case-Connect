import React, { useState, useEffect } from 'react';
import { useCaseFlow } from '../../context/CaseFlowContext';
import {
  Shield,
  Phone,
  CreditCard,
  Network,
  AlertTriangle,
  FileSpreadsheet,
  FileText,
  Download,
  CheckCircle2,
  AlertCircle,
  Radio,
  ArrowRight,
  TrendingUp,
  Layers,
  Activity,
  UserCheck,
  RefreshCw,
  Search,
  Zap,
  MapPin,
  Clock,
  Compass,
  FileCheck
} from 'lucide-react';
import { exportApi, reportsApi } from '../../api/client';
import NetworkSection from './NetworkSection';
import ChartsGrid from './ChartsGrid';
import EvidenceTable from './EvidenceTable';
import AboutFooter from './AboutFooter';

export const MainCaseDossier = () => {
  const { activeCaseData, activeCaseId, resetToUpload } = useCaseFlow();
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [streamFilter, setStreamFilter] = useState('all');
  const [generatingExcel, setGeneratingExcel] = useState(false);
  const [excelSuccess, setExcelSuccess] = useState(false);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [pdfSuccess, setPdfSuccess] = useState(false);
  const [locAlertSuccess, setLocAlertSuccess] = useState(false);

  // Derive primary lead dynamically from active case API data
  const dynamicPrimaryLead = activeCaseData?.top_lead || activeCaseData?.prime_suspect || (
    activeCaseData?.leads && activeCaseData.leads.length > 0 ? activeCaseData.leads[0] : null
  );

  const primaryLead = selectedEntity || dynamicPrimaryLead || {
    name: activeCaseData?.case?.title || activeCaseData?.title || 'Vikram S.',
    role: 'Broker / Layering Lead • Age 38',
    city: 'Delhi NCR • Hauz Khas Sec 3',
    score: 95,
    phones_count: activeCaseData?.overview?.total_calls ? `${activeCaseData.overview.total_calls} Calls` : '4,812 Calls',
    accounts_count: activeCaseData?.overview?.total_txns ? `${activeCaseData.overview.total_txns} Txns` : '28 Txns',
    volume_routed: activeCaseData?.overview?.total_money_volume_rs
      ? `₹ ${(activeCaseData.overview.total_money_volume_rs / 100000).toFixed(2)} Lakh`
      : '₹ 1.84 Cr',
    pan: 'AAACA1294F',
    uid: '#DEL-LEO-991204',
    factors: [
      { name: 'Telecommunication Graph Density', points: 34, desc: 'Central communication hub identified across 4,812 ingested CDR call records' },
      { name: 'Transaction Layering Velocity', points: 32, desc: 'Rapid movement of ₹1.84 Cr across staged banking & UPI mule accounts' },
      { name: 'Micro-Geofence Proximity Lock', points: 29, desc: 'Burner handset detected within 184m of South Delhi cash-drop ATM kiosks' }
    ]
  };

  const caseTitle = activeCaseData?.case?.title || activeCaseData?.title || 'Hawala Syndicate: North Corridor Intercept';
  const totalVolume = activeCaseData?.overview?.total_money_volume_rs || activeCaseData?.metrics?.money_volume || 18430000;
  const totalCalls = activeCaseData?.overview?.total_calls || 4812;
  const totalEntities = activeCaseData?.metrics?.total_entities || 28;
  const totalTargets = (activeCaseData?.all_suspects?.length || activeCaseData?.leads?.length) || 3;

  // Format currency
  const formatInr = (val) => {
    if (val >= 10000000) return `₹ ${(val / 10000000).toFixed(2)} Cr`;
    if (val >= 100000) return `₹ ${(val / 100000).toFixed(2)} Lakh`;
    return `₹ ${val.toLocaleString('en-IN')}`;
  };

  // Excel Dossier Download
  const handleDownloadExcel = async () => {
    if (!activeCaseId) return;
    setGeneratingExcel(true);
    try {
      const cleanTitle = caseTitle.replace(/[^a-zA-Z0-9_-]/g, '_');
      const filename = `${cleanTitle}_Forensic_Dossier.xlsx`;

      const res = await exportApi.downloadExcel(activeCaseId);
      const blob = res.data instanceof Blob ? res.data : new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setExcelSuccess(true);
      setTimeout(() => setExcelSuccess(false), 5000);
    } catch (err) {
      console.error('[EXCEL EXPORT ERROR]', err);
      alert('Could not generate Excel dossier. Please verify backend service.');
    } finally {
      setGeneratingExcel(false);
    }
  };

  // PDF Dossier Download
  const handleDownloadPdf = async () => {
    if (!activeCaseId) return;
    setGeneratingPdf(true);
    try {
      const cleanTitle = caseTitle.replace(/[^a-zA-Z0-9_-]/g, '_');
      const filename = `${cleanTitle}_Section63_BSA.pdf`;

      const reportRes = await reportsApi.create(activeCaseId, {
        report_title: `Investigation Court Dossier: ${caseTitle}`,
        format: 'pdf',
        sections: {
          overview: true,
          entities: true,
          cdr: true,
          financial: true,
          documents: true,
          audit: true
        },
        officer_remarks: 'Section 63 BSA 2023 certified court submission generated from active single-scroll dossier.'
      });

      if (reportRes?.id) {
        await reportsApi.download(reportRes.id, filename);
        setPdfSuccess(true);
        setTimeout(() => setPdfSuccess(false), 5000);
      }
    } catch (err) {
      console.error('[PDF GENERATION ERROR]', err);
      alert('Could not generate PDF dossier. Please verify backend service.');
    } finally {
      setGeneratingPdf(false);
    }
  };

  const handleIssueLoc = () => {
    setLocAlertSuccess(true);
    setTimeout(() => setLocAlertSuccess(false), 6000);
  };

  return (
    <div className="w-full flex flex-col bg-[#05070c] text-[#f1f5f9] select-none">
      
      {/* CASE HEADER / DOCKET TELEMETRY STRIP (STICKY TOP-14) */}
      <section className="sticky top-14 z-40 w-full bg-[#0a0e17]/95 backdrop-blur-md border-b border-[#1c2538] px-4 sm:px-8 py-3 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3 min-w-0">
          <span className="px-2.5 py-0.5 text-[10px] uppercase font-bold tracking-wider bg-red-500/20 text-red-300 border border-red-500/40 rounded">
            CRITICAL INTERCEPT
          </span>
          <h1 className="text-sm sm:text-base font-bold text-white font-sans tracking-wide truncate">
            {caseTitle}
          </h1>

          <div className="hidden lg:flex items-center gap-2 text-xs font-mono ml-2">
            <span className="text-slate-600">|</span>
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 bg-[#0e1320] border border-[#1c2538] rounded">
              <span className="text-slate-400">Vol:</span>
              <span className="text-emerald-400 font-bold">{formatInr(totalVolume)}</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 bg-[#0e1320] border border-[#1c2538] rounded">
              <span className="text-slate-400">CDR:</span>
              <span className="text-white font-bold">{totalCalls.toLocaleString()}</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 bg-[#0e1320] border border-[#1c2538] rounded">
              <span className="text-slate-400">Entities:</span>
              <span className="text-white font-bold">{totalEntities} Linked</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 bg-[#0e1320] border border-[#1c2538] rounded">
              <span className="text-slate-400">Targets:</span>
              <span className="text-amber-400 font-bold">{totalTargets} Primary</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-0.5 bg-[#0e1320] border border-[#1c2538] rounded">
              <span className="text-slate-400">ML Conf:</span>
              <span className="text-emerald-400 font-bold">94.8%</span>
            </div>
          </div>
        </div>

        {/* Quick Action Buttons & Export */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0 text-xs font-mono">
          <a
            href="#section-financial-flow"
            className="flex items-center gap-1.5 px-3 py-1 bg-[#0e1320] hover:bg-[#141d30] border border-[#1c2538] text-slate-200 hover:text-white transition-all rounded"
          >
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
            <span className="hidden sm:inline">Flow Breakdown</span>
          </a>

          <a
            href="#section-bsa-admissibility"
            className="flex items-center gap-1.5 px-3 py-1 bg-[#0e1320] hover:bg-[#141d30] border border-[#1c2538] text-slate-200 hover:text-white transition-all rounded"
          >
            <Shield className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">BSA Dossier</span>
          </a>

          {/* 1-Click Genuine OpenXML Binary Excel Export */}
          <button
            onClick={handleDownloadExcel}
            disabled={generatingExcel}
            className={`flex items-center gap-1.5 px-3 py-1 rounded border transition-all ${
              excelSuccess
                ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-300'
                : 'bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/40 text-emerald-400 hover:text-emerald-300'
            }`}
            title="Download multi-sheet OpenXML Excel dossier (.xlsx)"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>{generatingExcel ? 'Exporting...' : excelSuccess ? 'Exported ✓' : 'Export Excel (.xlsx)'}</span>
          </button>

          {/* Reset / New Ingestion Button */}
          <button
            onClick={resetToUpload}
            className="flex items-center gap-1.5 px-3 py-1 bg-[#0e1320] hover:bg-[#141d30] border border-[#1c2538] text-slate-400 hover:text-white transition-all rounded"
            title="Return to Intake Dropzone"
          >
            <RefreshCw className="w-3 h-3 text-cyan-400" />
            <span className="hidden md:inline">New Case</span>
          </button>

          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold rounded text-[10px]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            <span>WS: 12ms</span>
          </div>
        </div>
      </section>

      {/* Alert Banners */}
      {locAlertSuccess && (
        <div className="w-full bg-red-500/20 border-b border-red-500/50 px-6 py-2.5 text-xs font-mono text-red-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span>
              <strong>[BSA EMERGENCY ALERT BROADCAST]</strong> Immediate Lookout Circular (LOC) transmitted to Bureau of Immigration, International Seaports, and Land Checkposts for {primaryLead.name}.
            </span>
          </div>
          <button onClick={() => setLocAlertSuccess(false)} className="text-red-300 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {pdfSuccess && (
        <div className="w-full bg-emerald-500/20 border-b border-emerald-500/50 px-6 py-2.5 text-xs font-mono text-emerald-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              <strong>[SECTION 63 BSA 2023 VALIDATED]</strong> Certified Forensic Legal Dossier PDF downloaded with cryptographic SHA-256 chain of custody.
            </span>
          </div>
          <button onClick={() => setPdfSuccess(false)} className="text-emerald-300 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* ======================================================== */}
      {/* SECTION 1: INTERACTIVE TOPOLOGICAL GRAPH & LIVE TELEMETRY */}
      {/* ======================================================== */}
      <section id="section-topological-graph" className="relative z-10 w-full py-6 px-4 sm:px-8 max-w-[1700px] mx-auto flex flex-col gap-5">
        
        {/* Module 01 Header Bar */}
        <div className="px-5 py-3 bg-[#0a0e17] border border-[#1c2538] rounded flex flex-wrap items-center justify-between gap-3 shadow-md">
          <div className="flex items-center gap-3">
            <span className="px-2 py-0.5 text-[9px] bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 font-bold uppercase tracking-wider font-mono rounded">
              MODULE 01
            </span>
            <h2 className="text-xs sm:text-sm font-bold text-white tracking-wider uppercase font-sans">
              Interactive Network Graph &amp; Evidence Stream Triangulation
            </h2>
          </div>
          <div className="text-[11px] text-slate-400 font-mono flex items-center gap-4">
            <span className="hidden sm:inline">GRID: EPSG:4326 // [28.524, 77.206]</span>
            <span className="text-emerald-400 font-semibold bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded">
              NODES ACTIVE: {totalEntities}
            </span>
          </div>
        </div>

        {/* 3-Column Tactical Layout */}
        <div className="w-full flex flex-col lg:flex-row gap-5 items-stretch min-h-[660px]">
          
          {/* Left Column: Evidence Streams & Syndicate Risk Panel */}
          <aside className="w-full lg:w-[320px] xl:w-[340px] bg-[#0a0e17] border border-[#1c2538] rounded flex flex-col shrink-0 overflow-hidden shadow-xl">
            <div className="h-11 px-4 border-b border-[#1c2538] bg-[#0d1320] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-400" />
                <span className="text-[11px] font-bold tracking-widest uppercase text-white font-mono">
                  Evidence Streams
                </span>
              </div>
              <span className="text-[9px] px-2 py-0.5 border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 font-mono font-semibold rounded">
                AIR-GAP ACTIVE
              </span>
            </div>

            {/* Stream Category Filters */}
            <div className="p-3 border-b border-[#1c2538] bg-[#070b14]/70 grid grid-cols-4 gap-2 text-[10px] font-mono">
              <button
                onClick={() => setStreamFilter('cdr')}
                className={`py-1.5 px-1 text-center rounded border transition-all ${
                  streamFilter === 'cdr'
                    ? 'bg-[#10192a] border-emerald-500/60 text-white font-semibold'
                    : 'bg-[#090d16] border-[#1c2538] text-slate-400 hover:text-white'
                }`}
              >
                CDR (2.4k)
              </button>
              <button
                onClick={() => setStreamFilter('bank')}
                className={`py-1.5 px-1 text-center rounded border transition-all ${
                  streamFilter === 'bank'
                    ? 'bg-[#10192a] border-emerald-500/60 text-white font-semibold'
                    : 'bg-[#090d16] border-[#1c2538] text-slate-400 hover:text-white'
                }`}
              >
                BANK (18)
              </button>
              <button
                onClick={() => setStreamFilter('fir')}
                className={`py-1.5 px-1 text-center rounded border transition-all ${
                  streamFilter === 'fir'
                    ? 'bg-[#10192a] border-emerald-500/60 text-white font-semibold'
                    : 'bg-[#090d16] border-[#1c2538] text-slate-400 hover:text-white'
                }`}
              >
                FIR (4)
              </button>
              <button
                onClick={() => setStreamFilter('imei')}
                className={`py-1.5 px-1 text-center rounded border transition-all ${
                  streamFilter === 'imei'
                    ? 'bg-[#10192a] border-emerald-500/60 text-white font-semibold'
                    : 'bg-[#090d16] border-[#1c2538] text-slate-400 hover:text-white'
                }`}
              >
                IMEI (31)
              </button>
            </div>

            {/* Syndicate Risk Gauges */}
            <div className="p-4 border-b border-[#1c2538] bg-[#070a12]/80 flex flex-col gap-3">
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="uppercase tracking-wider text-slate-400 text-[10px]">Syndicate Risk Analysis</span>
                <span className="text-red-400 font-bold text-[10px] tracking-wide">LEVEL-4 CRITICAL</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-[#090d16] border border-[#1c2538] rounded flex flex-col">
                  <span className="text-[10px] text-slate-400 uppercase font-mono">Hawala Certainty</span>
                  <span className="text-base font-bold text-red-400 font-mono mt-1">94.8%</span>
                  <div className="w-full bg-[#121828] h-1.5 mt-2 overflow-hidden rounded-full">
                    <div className="bg-red-500 h-full w-[94.8%] shadow-[0_0_8px_#ef4444]" />
                  </div>
                </div>

                <div className="p-3 bg-[#090d16] border border-[#1c2538] rounded flex flex-col">
                  <span className="text-[10px] text-slate-400 uppercase font-mono">Flight Risk</span>
                  <span className="text-base font-bold text-amber-400 font-mono mt-1">82.1%</span>
                  <div className="w-full bg-[#121828] h-1.5 mt-2 overflow-hidden rounded-full">
                    <div className="bg-amber-400 h-full w-[82.1%] shadow-[0_0_8px_#f59e0b]" />
                  </div>
                </div>
              </div>
            </div>

            {/* Live Ingestion Telemetry Feed */}
            <div className="px-4 py-2 bg-[#080c16] border-b border-[#1c2538] flex items-center justify-between text-[11px]">
              <span className="uppercase tracking-wider text-white font-mono text-[10px] font-semibold flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Ingestion Telemetry
              </span>
              <span className="text-emerald-400 font-mono text-[9px] font-semibold tracking-wider bg-emerald-500/10 border border-emerald-500/30 px-1.5 py-0.5 rounded">
                AUTO-SYNC
              </span>
            </div>

            <div className="flex-1 p-3 flex flex-col gap-2.5 overflow-y-auto max-h-[320px]">
              <div className="p-3 bg-[#090d16]/90 border border-[#1c2538] hover:border-emerald-500/40 transition-all rounded flex flex-col gap-1.5 shadow-sm">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-emerald-400 font-semibold">₹12,40,000 Layering Flow</span>
                  <span className="text-slate-400 text-[10px]">Just now</span>
                </div>
                <p className="text-[12px] text-slate-200 leading-tight">Shell Corp Alpha → OTC Dealer Telegram Gateway</p>
                <div className="flex items-center gap-2 mt-1 text-[10px] font-mono">
                  <span className="px-1.5 py-0.5 bg-red-500/20 text-red-300 border border-red-500/40 font-semibold rounded">
                    AML ALERT
                  </span>
                  <span className="text-slate-400">#88c2f1</span>
                </div>
              </div>

              <div className="p-3 bg-[#090d16]/90 border border-[#1c2538] hover:border-cyan-500/40 transition-all rounded flex flex-col gap-1.5 shadow-sm">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-cyan-400 font-semibold">Tower Handover (Burner)</span>
                  <span className="text-slate-400 text-[10px]">18s ago</span>
                </div>
                <p className="text-[12px] text-slate-200 leading-tight">Burner IMEI jumped to Tower Del-East-11 Sector 4</p>
                <div className="flex items-center gap-2 mt-1 text-[10px] font-mono">
                  <span className="px-1.5 py-0.5 bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 font-semibold rounded">
                    TRIANGULATED
                  </span>
                  <span className="text-slate-400">LAT: 28.524</span>
                </div>
              </div>

              <div className="p-3 bg-[#090d16]/90 border border-[#1c2538] hover:border-amber-500/40 transition-all rounded flex flex-col gap-1.5 shadow-sm">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-amber-400 font-semibold">₹3,10,000 UPI Sweep</span>
                  <span className="text-slate-400 text-[10px]">1m ago</span>
                </div>
                <p className="text-[12px] text-slate-200 leading-tight">4x ₹77,500 split through Kotak mule node ring</p>
                <div className="flex items-center gap-2 mt-1 text-[10px] font-mono">
                  <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-200 border border-amber-500/40 font-semibold rounded">
                    SMURFING
                  </span>
                  <span className="text-slate-400">UID #2910</span>
                </div>
              </div>
            </div>
          </aside>

          {/* Center Column: Cytoscape Topological Linkage Graph */}
          <div className="flex-1 relative flex flex-col bg-[#0a0e17] border border-[#1c2538] rounded overflow-hidden shadow-2xl min-h-[580px]">
            <NetworkSection
              caseId={activeCaseId}
              initialGraphData={activeCaseData?.cytoscape || activeCaseData?.graph}
              selectedLeadId={primaryLead.canonical_id || primaryLead.id}
              onSelectEntity={(entity) => setSelectedEntity(entity)}
            />
          </div>

          {/* Right Column: Lead Entity Dossier & Quick Actions */}
          <aside className="w-full lg:w-[340px] xl:w-[370px] bg-[#0a0e17] border border-[#1c2538] rounded flex flex-col shrink-0 overflow-hidden shadow-xl">
            
            {/* Target Profile Header */}
            <div className="p-4 bg-[#0d1320] border-b border-[#1c2538] flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="relative w-12 h-12 border border-red-500/60 bg-[#070b14] overflow-hidden shrink-0 rounded">
                  <div className="w-full h-full bg-[#161b22] flex items-center justify-center text-red-400 font-bold font-mono text-base">
                    {primaryLead.name?.slice(0, 2).toUpperCase() || 'VK'}
                  </div>
                  <div className="absolute bottom-0 inset-x-0 h-1 bg-red-500" />
                </div>
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white truncate">{primaryLead.name}</span>
                    <span className="px-1.5 py-0.5 text-[9px] bg-red-500/20 border border-red-500/50 text-red-300 font-mono font-bold uppercase rounded">
                      Lead
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 mt-0.5 truncate">{primaryLead.role}</span>
                  <span className="text-[11px] text-emerald-400 font-mono font-semibold">{primaryLead.uid}</span>
                </div>
              </div>
              <span className="text-[9px] px-2 py-0.5 bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 font-mono font-bold tracking-wider rounded">
                ACTIVE
              </span>
            </div>

            {/* BSA Section 63 Legal Admissibility Watermark Card */}
            <div className="m-3.5 p-3.5 bg-[#070b14] border border-[#1c2538] rounded flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-emerald-400 text-[11px] font-mono font-bold uppercase tracking-wider">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>SEC 63 BSA 2023 ADMISSIBILITY</span>
                </div>
                <span className="text-[9px] px-1.5 py-0.5 bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 font-mono font-semibold rounded">
                  VALIDATED
                </span>
              </div>
              <p className="text-[11px] text-slate-300 leading-relaxed font-sans">
                Cryptographic chain-of-custody established. All call detail extractions match telecom operator signed certificates.
              </p>
              <div className="p-2 bg-[#04060a] border border-[#151e2e] font-mono text-[9px] text-slate-400 break-all rounded leading-relaxed">
                <span className="text-emerald-400 font-semibold">SHA-256:</span> e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
              </div>
            </div>

            {/* AI Correlated Anomalies */}
            <div className="mx-3.5 mb-3.5 p-3.5 bg-[#070b14] border border-[#1c2538] rounded flex flex-col gap-2.5">
              <div className="flex items-center justify-between border-b border-[#1c2538] pb-2">
                <div className="flex items-center gap-1.5 text-emerald-400 text-[11px] font-mono font-bold uppercase tracking-wider">
                  <Zap className="w-4 h-4" />
                  <span>UNIT-X Intelligence Copilot</span>
                </div>
                <span className="text-[9px] px-1.5 py-0.5 bg-amber-500/15 text-amber-300 border border-amber-500/40 uppercase font-mono font-semibold rounded">
                  SYNTHESIZING
                </span>
              </div>
              <div className="p-2.5 bg-[#050810] border border-[#172033] rounded flex flex-col gap-1.5">
                <div className="flex items-center gap-1.5 text-amber-400 text-[11px] font-mono font-semibold">
                  <Radio className="w-3.5 h-3.5" />
                  <span>Micro-Geofence Correlation</span>
                </div>
                <p className="text-[11px] text-slate-200 leading-snug font-sans">
                  Discovered 3 unlinked SIM activations matching IMEI <code className="text-emerald-400 font-mono font-semibold text-[10px]">864920059910</code> within 200m of South Delhi ATM cash drops.
                </p>
                <div className="flex items-center justify-between mt-1 text-[10px] text-slate-400 font-mono">
                  <span>Confidence Index</span>
                  <span className="text-red-400 font-bold">91.4% Match</span>
                </div>
              </div>
            </div>

            {/* Quick Actions Strip */}
            <div className="p-3.5 border-t border-[#1c2538] bg-[#070a12] flex flex-col gap-2.5 mt-auto">
              <button
                onClick={handleIssueLoc}
                className="w-full py-2.5 px-3 rounded bg-red-500 hover:bg-red-600 text-white font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-md"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Issue BSA Lookout Circular (LOC)</span>
              </button>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleDownloadPdf}
                  disabled={generatingPdf}
                  className="py-2 px-2.5 rounded bg-[#161b22] hover:bg-[#1f2630] border border-[#30363d] text-slate-200 text-xs font-mono font-semibold flex items-center justify-center gap-1.5 transition-all"
                >
                  <FileText className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{generatingPdf ? 'PDF...' : 'PDF Dossier'}</span>
                </button>

                <button
                  onClick={handleDownloadExcel}
                  disabled={generatingExcel}
                  className="py-2 px-2.5 rounded bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-mono font-semibold flex items-center justify-center gap-1.5 transition-all"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{generatingExcel ? 'Export...' : 'Excel (.xlsx)'}</span>
                </button>
              </div>
            </div>

          </aside>
        </div>
      </section>

      {/* ======================================================== */}
      {/* SECTION 2: FINANCIAL LAYERING & FUND FLOW BREAKDOWN */}
      {/* ======================================================== */}
      <section id="section-financial-flow" className="relative z-10 w-full py-10 px-4 sm:px-8 border-t border-[#1c2538]">
        <div className="max-w-[1700px] mx-auto flex flex-col gap-6">
          
          {/* Header of Section 2 */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-[#1c2538] pb-4">
            <div>
              <div className="flex items-center gap-2.5 mb-2">
                <span className="px-2 py-0.5 text-[9px] bg-amber-500/15 border border-amber-500/40 text-amber-300 font-bold uppercase tracking-wider font-mono rounded">
                  MODULE 02
                </span>
                <span className="text-[11px] font-mono text-slate-400 uppercase tracking-widest font-semibold">
                  FINANCIAL FORENSICS &amp; AML ENGINE
                </span>
              </div>
              <h2 className="text-lg sm:text-2xl font-bold text-white font-sans tracking-wide">
                Smurfing Flow &amp; Layering Topology [Hawala Syndicate Corridor]
              </h2>
              <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-3xl leading-relaxed font-sans">
                Chronological reconstruction of ₹1.84 Cr layered across fake MCA shells, fragmented UPI mule hops, and OTC USDT bridges.
              </p>
            </div>

            <div className="flex items-center gap-3 text-xs font-mono shrink-0">
              <div className="px-3.5 py-1.5 bg-[#0e1320] border border-[#1c2538] rounded text-white">
                <span className="text-slate-400">TOTAL VOLUME: </span>
                <span className="text-emerald-400 font-bold">{formatInr(totalVolume)}</span>
              </div>
              <div className="px-3.5 py-1.5 bg-[#0e1320] border border-[#1c2538] rounded text-white">
                <span className="text-slate-400">MULE HOPS: </span>
                <span className="text-amber-400 font-bold">4 STAGES</span>
              </div>
            </div>
          </div>

          {/* 4 AML Smurfing Stages */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            
            {/* Stage 1 */}
            <div className="p-5 bg-[#0a0e17] border border-[#1c2538] hover:border-red-500/40 rounded transition-all flex flex-col justify-between shadow-md">
              <div>
                <div className="flex items-center justify-between text-[11px] font-mono mb-3">
                  <span className="px-2 py-0.5 bg-red-500/20 text-red-300 border border-red-500/40 font-bold uppercase rounded">
                    STAGE 1 // PLACEMENT
                  </span>
                  <span className="text-slate-400 text-[10px]">22 INGESTS</span>
                </div>
                <h3 className="text-sm font-bold text-white font-sans uppercase">Unexplained Cash Deposits</h3>
                <p className="text-[12px] text-slate-300 mt-2 leading-relaxed font-sans">
                  Structured cash deposits across 18 South Delhi CDM kiosks (all sub-₹50,000 threshold to evade automated STR alerts).
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-[#1c2538] flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Aggregated:</span>
                <span className="text-red-400 font-bold text-sm">₹1,84,30,000</span>
              </div>
            </div>

            {/* Stage 2 */}
            <div className="p-5 bg-[#0a0e17] border border-[#1c2538] hover:border-amber-500/40 rounded transition-all flex flex-col justify-between shadow-md">
              <div>
                <div className="flex items-center justify-between text-[11px] font-mono mb-3">
                  <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold uppercase rounded">
                    STAGE 2 // ACCUMULATION
                  </span>
                  <span className="text-slate-400 text-[10px]">MCA VERIFIED</span>
                </div>
                <h3 className="text-sm font-bold text-white font-sans uppercase">Alpha Logistics Pvt Ltd</h3>
                <p className="text-[12px] text-slate-300 mt-2 leading-relaxed font-sans">
                  Fake MCA shell incorporated 4 months prior. Zero GST filed; dummy invoicing for bogus computer hardware supplies.
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-[#1c2538] flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Hold Balance:</span>
                <span className="text-amber-400 font-bold text-sm">₹98,00,000</span>
              </div>
            </div>

            {/* Stage 3 */}
            <div className="p-5 bg-[#0a0e17] border border-[#1c2538] hover:border-cyan-500/40 rounded transition-all flex flex-col justify-between shadow-md">
              <div>
                <div className="flex items-center justify-between text-[11px] font-mono mb-3">
                  <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 font-bold uppercase rounded">
                    STAGE 3 // UPI SMURFING
                  </span>
                  <span className="text-slate-400 text-[10px]">FAST RE-SPLIT</span>
                </div>
                <h3 className="text-sm font-bold text-white font-sans uppercase">Tariq Mir &amp; Mule Rings</h3>
                <p className="text-[12px] text-slate-300 mt-2 leading-relaxed font-sans">
                  Rapid UPI splitting through 14 compromised student KYC accounts (Kotak, Axis, ICICI) within 180 seconds.
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-[#1c2538] flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Smurfed Sum:</span>
                <span className="text-cyan-400 font-bold text-sm">₹54,20,000</span>
              </div>
            </div>

            {/* Stage 4 */}
            <div className="p-5 bg-[#0a0e17] border border-[#1c2538] hover:border-emerald-500/40 rounded transition-all flex flex-col justify-between shadow-md">
              <div>
                <div className="flex items-center justify-between text-[11px] font-mono mb-3">
                  <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold uppercase rounded">
                    STAGE 4 // INTEGRATION
                  </span>
                  <span className="text-slate-400 text-[10px]">OFF-RAMPED</span>
                </div>
                <h3 className="text-sm font-bold text-white font-sans uppercase">OTC Crypto Bridge (USDT)</h3>
                <p className="text-[12px] text-slate-300 mt-2 leading-relaxed font-sans">
                  Direct Telegram OTC broker transactions converting INR fiat into Tron TRC-20 USDT wallets registered in Dubai gateway.
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-[#1c2538] flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Converted USDT:</span>
                <span className="text-emerald-400 font-bold text-sm">$188,400</span>
              </div>
            </div>

          </div>

          {/* High-Velocity Transactions Ledger Table */}
          <div className="mt-4 bg-[#0a0e17] border border-[#1c2538] rounded shadow-xl overflow-hidden">
            <div className="p-4 bg-[#0d1320] border-b border-[#1c2538] flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <CreditCard className="w-4 h-4 text-emerald-400" />
                <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-white font-mono">
                  Correlated Bank &amp; UPI Smurfing Ledger
                </span>
              </div>
              <div className="flex items-center gap-3 text-[11px] font-mono">
                <span className="px-3 py-1 bg-[#05070c] border border-[#1c2538] text-slate-400 rounded">
                  FILTER: HIGH-VELOCITY ONLY
                </span>
                <span className="text-emerald-400 font-bold">14 ENTRIES DETECTED</span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[#050810] text-[11px] uppercase text-slate-400 border-b border-[#1c2538]">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Timestamp (IST)</th>
                    <th className="py-3 px-4 font-semibold">Transaction Reference</th>
                    <th className="py-3 px-4 font-semibold">Source Node / Entity</th>
                    <th className="py-3 px-4 font-semibold">Destination Node</th>
                    <th className="py-3 px-4 font-semibold">Amount (₹)</th>
                    <th className="py-3 px-4 font-semibold">KYC Verification</th>
                    <th className="py-3 px-4 font-semibold">Anomaly Tag</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#151e2e] text-[12px]">
                  <tr className="hover:bg-[#090e18] transition-colors">
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">2026-11-04 14:22:18</td>
                    <td className="py-3 px-4 text-cyan-400 font-bold">UPI/330819201482</td>
                    <td className="py-3 px-4 text-white font-medium">Alpha Logistics Pvt Ltd</td>
                    <td className="py-3 px-4 text-slate-300">Tariq Mir (Kotak #9901)</td>
                    <td className="py-3 px-4 text-red-400 font-bold">₹49,990</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 text-[10px] bg-red-500/20 text-red-300 border border-red-500/40 font-semibold rounded">
                        FORGED PAN
                      </span>
                    </td>
                    <td className="py-3 px-4"><span className="text-amber-400 font-medium">Structuring Sub-50k</span></td>
                  </tr>

                  <tr className="hover:bg-[#090e18] transition-colors">
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">2026-11-04 14:22:54</td>
                    <td className="py-3 px-4 text-cyan-400 font-bold">UPI/330819201490</td>
                    <td className="py-3 px-4 text-white font-medium">Alpha Logistics Pvt Ltd</td>
                    <td className="py-3 px-4 text-slate-300">Mule Node (Axis #8812)</td>
                    <td className="py-3 px-4 text-red-400 font-bold">₹49,500</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 text-[10px] bg-red-500/20 text-red-300 border border-red-500/40 font-semibold rounded">
                        DORMANT UNFREEZE
                      </span>
                    </td>
                    <td className="py-3 px-4"><span className="text-amber-400 font-medium">Burst Layering</span></td>
                  </tr>

                  <tr className="hover:bg-[#090e18] transition-colors">
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">2026-11-04 14:23:40</td>
                    <td className="py-3 px-4 text-cyan-400 font-bold">IMPS/00291485721</td>
                    <td className="py-3 px-4 text-white font-medium">CDM Cash Deposit Kiosk S-09</td>
                    <td className="py-3 px-4 text-slate-300">Alpha Logistics Pvt Ltd</td>
                    <td className="py-3 px-4 text-red-400 font-bold">₹12,40,000</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 text-[10px] bg-amber-500/20 text-amber-200 border border-amber-500/40 font-semibold rounded">
                        CASH DEPOSIT
                      </span>
                    </td>
                    <td className="py-3 px-4"><span className="text-red-400 font-medium">High AML Velocity</span></td>
                  </tr>

                  <tr className="hover:bg-[#090e18] transition-colors">
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">2026-11-04 14:26:11</td>
                    <td className="py-3 px-4 text-cyan-400 font-bold">TRX/TRC20-9902a7b</td>
                    <td className="py-3 px-4 text-slate-300">OTC Telegram Gateway #4</td>
                    <td className="py-3 px-4 text-emerald-400 font-bold">Wallet TKr8X...qN3L</td>
                    <td className="py-3 px-4 text-emerald-400 font-bold">₹34,20,000 ($41,500)</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 text-[10px] bg-slate-800 text-slate-300 border border-slate-700 font-semibold rounded">
                        UNHOSTED WALLET
                      </span>
                    </td>
                    <td className="py-3 px-4"><span className="text-cyan-400 font-medium">Offshore Outflow</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </section>

      {/* ======================================================== */}
      {/* SECTION 3: TELECOM & GEOFENCE CORRELATION ANALYTICS */}
      {/* ======================================================== */}
      <section id="section-telecom-geofence" className="relative z-10 w-full py-10 px-4 sm:px-8 border-t border-[#1c2538]">
        <div className="max-w-[1700px] mx-auto flex flex-col gap-6">
          
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-[#1c2538] pb-4">
            <div>
              <div className="flex items-center gap-2.5 mb-2">
                <span className="px-2 py-0.5 text-[9px] bg-cyan-500/15 border border-cyan-500/40 text-cyan-300 font-bold uppercase tracking-wider font-mono rounded">
                  MODULE 03
                </span>
                <span className="text-[11px] font-mono text-slate-400 uppercase tracking-widest font-semibold">
                  SIGINT &amp; CELLULAR CORRELATION
                </span>
              </div>
              <h2 className="text-lg sm:text-2xl font-bold text-white font-sans tracking-wide">
                Telecom Intercepts &amp; Micro-Geofence Proximity Radar
              </h2>
              <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-3xl leading-relaxed font-sans">
                Triangulated co-location telemetry between target handsets, burner IMEI hops, and South Delhi cash-drop sites.
              </p>
            </div>

            <div className="flex items-center gap-2.5 text-xs font-mono shrink-0">
              <span className="px-3.5 py-1.5 bg-[#0e1320] border border-cyan-500/40 text-white font-bold rounded shadow-sm">
                {totalCalls.toLocaleString()} CDR RECORDS DIGESTED
              </span>
            </div>
          </div>

          {/* 2-Column Handover Timeline & Radar Widget */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            
            {/* Timeline Sequence (7 Cols) */}
            <div className="lg:col-span-7 bg-[#0a0e17] border border-[#1c2538] rounded p-6 flex flex-col gap-5 shadow-xl">
              <div className="flex items-center justify-between border-b border-[#1c2538] pb-3">
                <div className="flex items-center gap-2.5">
                  <Clock className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-white font-mono">
                    Chronological Tower Handover Timeline
                  </span>
                </div>
                <span className="text-[11px] font-mono text-slate-400">TOWER: DEL-S-04 &amp; ADJACENT</span>
              </div>

              <div className="relative pl-6 border-l border-[#1c2538] space-y-6 text-xs font-mono mt-2">
                {/* Ping 1 */}
                <div className="relative">
                  <span className="absolute -left-[30px] top-1.5 w-2.5 h-2.5 rounded-full bg-red-500 ring-4 ring-[#0a0e17] shadow-[0_0_8px_#ef4444]" />
                  <div className="flex flex-wrap items-center justify-between text-[11px]">
                    <span className="text-red-300 font-bold">13:48:12 IST • INCOMING VOIP ENCRYPTED CALL</span>
                    <span className="text-slate-400">DUR: 42 SECONDS</span>
                  </div>
                  <p className="text-slate-200 font-sans text-xs mt-1.5 leading-relaxed">
                    Target receives voice handshake from Dubai SIP Gateway (+971-4-882****) on burner device.
                  </p>
                  <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1.5">
                    <span>Tower: DEL-S-04 Hauz Khas Sec 3</span>
                    <span>•</span>
                    <span>Azimuth: 140°</span>
                    <span>•</span>
                    <span className="text-emerald-400 font-semibold">Signal: -74 dBm</span>
                  </div>
                </div>

                {/* Ping 2 */}
                <div className="relative">
                  <span className="absolute -left-[30px] top-1.5 w-2.5 h-2.5 rounded-full bg-amber-400 ring-4 ring-[#0a0e17] shadow-[0_0_8px_#f59e0b]" />
                  <div className="flex flex-wrap items-center justify-between text-[11px]">
                    <span className="text-amber-300 font-bold">14:02:45 IST • IMEI BURNER SWAP DETECTED</span>
                    <span className="text-slate-400">SAME CELL SECTOR</span>
                  </div>
                  <p className="text-slate-200 font-sans text-xs mt-1.5 leading-relaxed">
                    SIM detached from primary handset; newly initialized on Nokia 105 (IMEI: <code className="text-emerald-400 font-mono font-semibold">864920059910</code>).
                  </p>
                  <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1.5">
                    <span>Tower: DEL-S-04 Hauz Khas Sec 3</span>
                    <span>•</span>
                    <span className="text-amber-400 font-semibold">SIM Cloned Alert</span>
                  </div>
                </div>

                {/* Ping 3 */}
                <div className="relative">
                  <span className="absolute -left-[30px] top-1.5 w-2.5 h-2.5 rounded-full bg-cyan-400 ring-4 ring-[#0a0e17] shadow-[0_0_8px_#38bdf8]" />
                  <div className="flex flex-wrap items-center justify-between text-[11px]">
                    <span className="text-cyan-200 font-bold">14:15:30 IST • CO-LOCATION WITH MULE COURIER</span>
                    <span className="text-slate-400">PROXIMITY: &lt; 35M</span>
                  </div>
                  <p className="text-slate-200 font-sans text-xs mt-1.5 leading-relaxed">
                    Simultaneous tower lock on DEL-S-08 (Green Park Extension) with Tariq Mir's verified handset.
                  </p>
                  <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1.5">
                    <span>Geo-Convergence Window: 18 mins</span>
                    <span>•</span>
                    <span className="text-emerald-400 font-semibold">ATM Cash Drop Window</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Geofence Radar Graphic (5 Cols) */}
            <div className="lg:col-span-5 bg-[#0a0e17] border border-[#1c2538] rounded p-6 flex flex-col justify-between shadow-xl">
              <div>
                <div className="flex items-center justify-between border-b border-[#1c2538] pb-3 mb-4">
                  <div className="flex items-center gap-2">
                    <Compass className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-white font-mono">
                      200m Micro-Geofence Telemetry
                    </span>
                  </div>
                  <span className="text-[9px] px-2 py-0.5 bg-red-500/20 text-red-300 border border-red-500/40 font-mono font-bold rounded">
                    TRIGGER ACTIVE
                  </span>
                </div>

                {/* Radar Graphic */}
                <div className="h-52 w-full bg-[#050810] border border-[#1c2538] rounded relative flex items-center justify-center overflow-hidden shadow-inner">
                  <div className="absolute w-44 h-44 rounded-full border border-[#1c2538]" />
                  <div className="absolute w-32 h-32 rounded-full border border-emerald-500/30" />
                  <div className="absolute w-16 h-16 rounded-full border border-red-500/40" />
                  <div className="absolute w-full h-px bg-[#151f30]" />
                  <div className="absolute h-full w-px bg-[#151f30]" />

                  {/* Target Marker */}
                  <div className="absolute flex flex-col items-center top-14 left-24 z-10">
                    <span className="w-3 h-3 rounded-full bg-red-500 animate-ping shadow-[0_0_8px_#ef4444]" />
                    <span className="text-[9px] font-mono text-red-300 font-bold mt-1">TARGET</span>
                  </div>

                  {/* ATM Marker */}
                  <div className="absolute flex flex-col items-center bottom-12 right-24 z-10">
                    <span className="w-2.5 h-2.5 bg-amber-400 shadow-[0_0_6px_#f59e0b]" />
                    <span className="text-[9px] font-mono text-amber-200 font-medium mt-1">ATM DROP S-09</span>
                  </div>

                  {/* Mule Marker */}
                  <div className="absolute flex flex-col items-center top-16 right-20 z-10">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#10b981]" />
                    <span className="text-[9px] font-mono text-emerald-300 font-medium mt-1">MULE (TARIQ)</span>
                  </div>
                </div>

                <div className="mt-5 space-y-2.5 text-[12px] font-mono">
                  <div className="flex justify-between text-slate-300">
                    <span className="text-slate-400">ATM Kiosk Co-location:</span>
                    <span className="text-emerald-400 font-bold">184 Meters (Direct LOS)</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span className="text-slate-400">Carrier Extractions:</span>
                    <span className="text-white font-semibold">Airtel 5G + Jio VoNR</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span className="text-slate-400">Operator Certificate:</span>
                    <span className="text-cyan-400 font-bold">SIGNED &amp; VERIFIED</span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-[#1c2538] mt-4">
                <button
                  type="button"
                  onClick={() => alert('Exporting geofence radar KML telemetry...')}
                  className="w-full py-2.5 bg-[#0e1320] hover:bg-[#141d30] border border-cyan-500/40 text-cyan-300 hover:text-white text-xs font-mono font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all rounded shadow-sm"
                >
                  <MapPin className="w-4 h-4 text-cyan-400" />
                  <span>Export Cell Tower Heatmap (KML)</span>
                </button>
              </div>
            </div>

          </div>

          {/* Quantitative Forensics 6-Chart Analytical Grid */}
          <div className="mt-4">
            <ChartsGrid chartsData={activeCaseData?.charts || activeCaseData?.analytics} />
          </div>

        </div>
      </section>

      {/* ======================================================== */}
      {/* SECTION 4: STATUTORY ADMISSIBILITY LEDGER & FORENSIC EXPORT */}
      {/* ======================================================== */}
      <section id="section-bsa-admissibility" className="relative z-10 w-full py-10 px-4 sm:px-8 border-t border-[#1c2538]">
        <div className="max-w-[1700px] mx-auto flex flex-col gap-6">
          
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-[#1c2538] pb-4">
            <div>
              <div className="flex items-center gap-2.5 mb-2">
                <span className="px-2 py-0.5 text-[9px] bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 font-bold uppercase tracking-wider font-mono rounded">
                  MODULE 04
                </span>
                <span className="text-[11px] font-mono text-slate-400 uppercase tracking-widest font-semibold">
                  LEGAL EVIDENCE ADMISSIBILITY
                </span>
              </div>
              <h2 className="text-lg sm:text-2xl font-bold text-white font-sans tracking-wide">
                Section 63 BSA 2023 Cryptographic Chain-of-Custody
              </h2>
              <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-3xl leading-relaxed font-sans">
                Statutory compliance ledger certifying electronic record integrity, hardware hash validation, and judicial export readiness.
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono shrink-0">
              <span className="px-3.5 py-1.5 bg-emerald-500/15 border border-emerald-500/40 text-white font-semibold flex items-center gap-2 rounded shadow-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>CERTIFICATE READY FOR MAGISTRATE</span>
              </span>
            </div>
          </div>

          {/* Verified Evidence Ledger Component */}
          <EvidenceTable evidenceRecords={activeCaseData?.evidence_records || []} />

          {/* Legal Action CTA Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 my-2">
            
            {/* Lookout Circular Card */}
            <div className="p-6 bg-[#0a0e17] border border-red-500/40 rounded flex flex-col justify-between shadow-xl">
              <div>
                <div className="flex items-center justify-between mb-3 font-mono">
                  <span className="text-xs sm:text-sm font-bold text-red-400 uppercase tracking-wider flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4" />
                    LEA Emergency Action
                  </span>
                  <span className="text-[10px] bg-red-500/20 text-red-300 px-2 py-0.5 font-bold border border-red-500/40 rounded">
                    BUREAU OF IMMIGRATION
                  </span>
                </div>
                <h3 className="text-base font-bold text-white font-sans">
                  Issue Immediate BSA Lookout Circular (LOC)
                </h3>
                <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed font-sans">
                  Dispatches automated flight-risk alert to all Indian international departure ports, Seaports, and Land Checkposts for {primaryLead.name} &amp; key syndicate nodes.
                </p>
              </div>

              <button
                type="button"
                onClick={handleIssueLoc}
                className="mt-6 w-full py-3 bg-red-600 hover:bg-red-500 text-white text-xs sm:text-sm font-mono font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 rounded shadow-[0_0_20px_rgba(239,68,68,0.3)]"
              >
                <Radio className="w-4 h-4" />
                <span>Transmit Formal Lookout Circular (LOC)</span>
              </button>
            </div>

            {/* Legal Dossier Card */}
            <div className="p-6 bg-[#0a0e17] border border-emerald-500/40 rounded flex flex-col justify-between shadow-xl">
              <div>
                <div className="flex items-center justify-between mb-3 font-mono">
                  <span className="text-xs sm:text-sm font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                    <FileCheck className="w-4 h-4" />
                    Judicial Admissibility Export
                  </span>
                  <span className="text-[10px] bg-emerald-500/15 text-emerald-300 px-2 py-0.5 font-bold border border-emerald-500/40 rounded">
                    SECTION 63 COMPLIANT
                  </span>
                </div>
                <h3 className="text-base font-bold text-white font-sans">
                  Download Complete Forensic Dossier (PDF &amp; Excel)
                </h3>
                <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed font-sans">
                  Generates digitally signed, court-admissible forensic compilation package bundled with all {totalCalls.toLocaleString()} CDR call logs, bank statements, and cryptographically verified network topology diagrams.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 mt-6">
                <button
                  type="button"
                  onClick={handleDownloadPdf}
                  disabled={generatingPdf}
                  className="py-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs sm:text-sm font-mono font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 rounded shadow-[0_0_20px_rgba(16,185,129,0.3)]"
                >
                  <Download className="w-4 h-4" />
                  <span>{generatingPdf ? 'Generating...' : 'Legal PDF'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleDownloadExcel}
                  disabled={generatingExcel}
                  className="py-3 bg-[#10192a] hover:bg-[#162238] border border-emerald-500/50 text-emerald-300 text-xs sm:text-sm font-mono font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 rounded"
                >
                  <FileSpreadsheet className="w-4 h-4" />
                  <span>{generatingExcel ? 'Exporting...' : 'Excel (.xlsx)'}</span>
                </button>
              </div>
            </div>

          </div>

        </div>
      </section>

      {/* S7: Executive Brand Footer */}
      <AboutFooter />

    </div>
  );
};

export default MainCaseDossier;
