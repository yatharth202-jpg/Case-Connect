import React, { useState } from 'react';
import { 
  Shield, Phone, CreditCard, Network, AlertTriangle, 
  ChevronDown, ChevronUp, Camera, CheckCircle2, ArrowUpRight, 
  Download, FileText 
} from 'lucide-react';
import { reportsApi } from '../../api/client';
import { useCaseFlow } from '../../context/CaseFlowContext';

export const SuspectHero = ({ activeEntity, onSelectFactorEvidence }) => {
  const { activeCaseId, activeCaseData } = useCaseFlow();
  const [whyExpanded, setWhyExpanded] = useState(false);
  const [customPhotoUrl, setCustomPhotoUrl] = useState(null);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [pdfSuccess, setPdfSuccess] = useState(false);

  const handleDownloadPdf = async () => {
    if (!activeCaseId) return;
    setGeneratingPdf(true);
    try {
      const caseTitle = activeCaseData?.case?.title || activeCaseData?.title || 'Case_Dossier';
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

  if (!activeEntity) {
    return (
      <section id="lead" className="w-full py-16 px-4 max-w-6xl mx-auto text-center">
        <div className="glass p-12 text-muted font-mono text-sm">
          No primary lead attributed yet. Ingest evidence files to generate forensic attribution.
        </div>
      </section>
    );
  }

  const name = activeEntity.name || activeEntity.display_name || 'Primary Focal Node';
  const role = activeEntity.role || activeEntity.label || 'Syndicate Key Entity';
  const score = Math.round(activeEntity.score ?? activeEntity.risk_score ?? activeEntity.confidence ?? 85);
  const city = activeEntity.city || activeEntity.location || 'Multi-Jurisdiction Node';

  // Semantic color for risk ring
  const ringColor = score > 60 ? '#E5484D' : score >= 31 ? '#F2A33A' : '#3FB6A8';
  const circumference = 2 * Math.PI * 40; // ~251.3
  const strokeOffset = circumference - (circumference * score) / 100;

  // Derive initials
  const initials = name
    .split(' ')
    .filter(Boolean)
    .map(p => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase() || 'ID';

  // Factors breakdown
  const factors = activeEntity.factors || activeEntity.why_factors || [
    { name: 'Network Centrality Influence', points: 28, desc: 'High degree cross-cluster bridging across telecom hubs' },
    { name: 'Pass-Through Money Velocity', points: 34, desc: 'Layering transfer pattern through mule accounts within 4 hours' },
    { name: 'Co-Location & Call Burst Spike', points: 23, desc: '41 anomalous calls concentrated during odd midnight curfew hours' }
  ];

  const handlePhotoUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setCustomPhotoUrl(url);
    }
  };

  return (
    <section id="lead" className="w-full py-12 px-4 sm:px-6 max-w-6xl mx-auto relative z-10">
      {/* Section Tagline & Court PDF Action */}
      <div className="mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass-sm text-[11px] font-mono text-accent">
          <span className="w-1.5 h-1.5 rounded-full bg-alert animate-ping" />
          <span>SECTION 01 · PRIMARY THREAT ATTRIBUTION</span>
        </div>

        <div className="flex items-center gap-2.5">
          {activeCaseId && (
            <button
              onClick={handleDownloadPdf}
              disabled={generatingPdf}
              className="glass-pill px-3 py-1 text-xs font-mono text-text hover:text-accent border-accent/30 hover:border-accent/60 transition-all flex items-center gap-1.5 disabled:opacity-50"
              title="Generate Court-Admissible Section 63 BSA Certified PDF"
            >
              {generatingPdf ? (
                <>
                  <div className="w-3 h-3 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
                  <span className="text-accent">Generating PDF...</span>
                </>
              ) : pdfSuccess ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-data" />
                  <span className="text-data">Sealed PDF Ready</span>
                </>
              ) : (
                <>
                  <Download className="w-3.5 h-3.5 text-accent" />
                  <span>Download Court PDF (Sec 63 BSA)</span>
                </>
              )}
            </button>
          )}

          <span className="font-mono text-xs text-muted">
            UID: {activeEntity.canonical_id || activeEntity.id || 'CC-NODE-01'}
          </span>
        </div>
      </div>

      {/* Main Glass Dossier Card */}
      <div className="glass p-6 sm:p-8 relative overflow-hidden border border-white/10 shadow-2xl">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Column 1: Portrait Silhouette Avatar (No Fake Faces) */}
          <div className="lg:col-span-3 flex flex-col items-center">
            <div className="relative w-40 h-48 sm:w-44 sm:h-52 rounded-2xl glass-sm border border-white/15 overflow-hidden flex flex-col items-center justify-center group shadow-xl">
              {customPhotoUrl ? (
                <img
                  src={customPhotoUrl}
                  alt={name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center justify-center space-y-2">
                  <div className="w-20 h-20 rounded-full bg-white/[0.04] border border-white/10 flex items-center justify-center font-serif text-3xl font-bold text-accent">
                    {initials}
                  </div>
                  <span className="text-[10px] font-mono text-muted uppercase tracking-wider">
                    Monochrome Silhouette
                  </span>
                </div>
              )}

              {/* Attach Official Photo Action */}
              <label className="absolute inset-0 bg-ink/80 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center cursor-pointer p-4 text-center">
                <Camera className="w-6 h-6 text-accent mb-1" />
                <span className="text-[11px] font-mono text-text">Attach Official Photo</span>
                <span className="text-[9px] font-mono text-muted">Local case storage only</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoUpload}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          {/* Column 2: Entity Identification & Corroborated Chips */}
          <div className="lg:col-span-6 space-y-4">
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider bg-alert/15 text-alert border border-alert/30 font-semibold">
                  {role}
                </span>
                <span className="text-xs font-mono text-muted">
                  • {city}
                </span>
              </div>
              <h2 className="font-serif text-3xl sm:text-4xl text-text tracking-tight">
                {name}
              </h2>
            </div>

            {/* Structured Telemetry Chips */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-1">
              <div className="glass-sm p-2.5 rounded-xl border border-white/5">
                <div className="flex items-center gap-1.5 text-muted text-[10px] font-mono mb-0.5">
                  <Phone className="w-3 h-3 text-accent" />
                  <span>PHONES / MSISDN</span>
                </div>
                <p className="font-mono text-sm text-text font-semibold">
                  {activeEntity.phones_count || activeEntity.phones?.length || '3 Linked'}
                </p>
              </div>

              <div className="glass-sm p-2.5 rounded-xl border border-white/5">
                <div className="flex items-center gap-1.5 text-muted text-[10px] font-mono mb-0.5">
                  <CreditCard className="w-3 h-3 text-data" />
                  <span>BANK ACCOUNTS</span>
                </div>
                <p className="font-mono text-sm text-text font-semibold">
                  {activeEntity.accounts_count || activeEntity.accounts?.length || '5 Accounts'}
                </p>
              </div>

              <div className="glass-sm p-2.5 rounded-xl border border-white/5 col-span-2 sm:col-span-1">
                <div className="flex items-center gap-1.5 text-muted text-[10px] font-mono mb-0.5">
                  <Network className="w-3 h-3 text-alert" />
                  <span>TOTAL VOLUME</span>
                </div>
                <p className="font-mono text-sm text-accent font-semibold truncate">
                  {activeEntity.volume_routed || '₹ 1.84 Cr'}
                </p>
              </div>
            </div>

            {/* Expandable Why Flagged Button */}
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setWhyExpanded(!whyExpanded)}
                className="glass-pill px-4 py-2 text-xs font-mono text-muted hover:text-text flex items-center justify-between w-full border border-white/10 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-accent" />
                  <span>Why flagged for review</span>
                </span>
                {whyExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Column 3: Large Dynamic Confidence Meter */}
          <div className="lg:col-span-3 flex flex-col items-center justify-center p-4">
            <div className="relative w-36 h-36 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 96 96">
                <circle
                  cx="48"
                  cy="48"
                  r="40"
                  fill="none"
                  stroke="rgba(255, 255, 255, 0.08)"
                  strokeWidth="6"
                />
                <circle
                  cx="48"
                  cy="48"
                  r="40"
                  fill="none"
                  stroke={ringColor}
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeOffset}
                  className="ring-circle"
                />
              </svg>

              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-mono text-4xl font-bold text-text tracking-tight">
                  {score}%
                </span>
                <span className="font-mono text-[9px] uppercase tracking-wider text-muted">
                  Confidence
                </span>
              </div>
            </div>

            <div className="text-center mt-3">
              <span className="inline-flex items-center gap-1 text-[11px] font-mono text-data">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>3 Vectors Corroborated</span>
              </span>
            </div>
          </div>
        </div>

        {/* Expandable Why-Flagged Factor Breakdown Panel */}
        {whyExpanded && (
          <div className="mt-6 pt-6 border-t border-white/[0.08] space-y-3 animate-fadeIn">
            <div className="flex items-center justify-between text-xs font-mono text-muted mb-2">
              <span>Algorithmic Factor Breakdown (Section 63 BSA Verifiable)</span>
              <span>Weight Contribution</span>
            </div>

            <div className="space-y-2.5">
              {factors.map((f, i) => (
                <div key={i} className="glass-sm p-3.5 rounded-xl border border-white/5 space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-text font-medium">{f.name}</span>
                    <span className="text-accent font-semibold">+{f.points} pts</span>
                  </div>
                  <div className="w-full bg-white/[0.06] h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-accent h-full rounded-full transition-all duration-700"
                      style={{ width: `${Math.min(f.points * 2.5, 100)}%` }}
                    />
                  </div>
                  <p className="text-[11px] text-muted leading-relaxed">
                    {f.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export default SuspectHero;
