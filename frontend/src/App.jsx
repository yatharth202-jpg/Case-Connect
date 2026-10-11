import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import QuickCrimeAnalyser from './pages/QuickCrimeAnalyser';
import Cases from './pages/Cases';
import CaseDetail from './pages/CaseDetail';
import AuditLog from './pages/AuditLog';
import { Shield, Lock, UserCheck, Network, Database, X } from 'lucide-react';

function MainRouter() {
  const { isAuthenticated, loading } = useAuth();
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  const [activeLegalModal, setActiveLegalModal] = useState(null);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Keyboard Escape listener to dismiss any active modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setActiveLegalModal(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#040711] flex items-center justify-center text-white text-xs font-mono">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-slate-700 border-t-[#00F0FF] rounded-full animate-spin" />
          <span className="text-cyan-400 font-semibold tracking-wider">Validating Officer Credentials...</span>
        </div>
      </div>
    );
  }

  // Route matching
  if (!isAuthenticated && currentPath !== '/login') {
    window.history.replaceState(null, '', '/login');
    return <Login />;
  }

  if (currentPath === '/login') {
    if (isAuthenticated) {
      window.history.replaceState(null, '', '/');
      return (
        <div className="min-h-screen bg-[#040711] text-slate-100 flex flex-col font-sans">
          <Navbar onOpenLegalModal={setActiveLegalModal} />
          <QuickCrimeAnalyser />
        </div>
      );
    }
    return <Login />;
  }

  // Handle /cases/:id
  const caseMatch = currentPath.match(/^\/cases\/([a-zA-Z0-9_-]+)/);

  return (
    <div className="min-h-screen bg-[#040711] text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      <Navbar onOpenLegalModal={setActiveLegalModal} />

      <main className="flex-1 flex flex-col">
        {caseMatch ? (
          <CaseDetail caseId={caseMatch[1]} />
        ) : currentPath === '/audit' ? (
          <AuditLog />
        ) : currentPath === '/cases' ? (
          <Cases />
        ) : (
          <QuickCrimeAnalyser onOpenLegalModal={setActiveLegalModal} />
        )}
      </main>

      {/* BEGIN: MainFooter (Stitch Anti-Gravity Refined Footer) */}
      <footer className="relative z-20 border-t border-slate-800/80 bg-[#060B19]/95 backdrop-blur-lg pt-7 pb-5 px-6 lg:px-12 mt-auto" data-purpose="refined-footer">
        <div className="max-w-[1720px] mx-auto flex flex-col items-center text-center space-y-4">
          {/* Brand Soft Emblem & Identity */}
          <div className="flex items-center justify-center gap-2.5">
            <div className="flex items-center gap-2 tracking-widest font-cyber text-2xl font-bold text-slate-200">
              <span>UNIT<span className="text-cyan-400 font-black">X</span></span>
            </div>
            <div className="w-6 h-6 rounded-full border border-cyan-500/40 bg-cyan-950/40 flex items-center justify-center text-cyan-400 text-xs">
              <Shield className="w-3.5 h-3.5" />
            </div>
          </div>

          {/* Functional Capability Subtitle */}
          <p className="max-w-4xl text-xs sm:text-sm text-slate-400 font-normal leading-relaxed">
            Automated telecommunication CDR, banking transaction, and multi-jurisdiction FIR correlation engine engineered for Indian law enforcement agencies.
          </p>

          {/* Statutory & Algorithmic Compliance Tags */}
          <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[11px] text-slate-400 font-mono tracking-tight bg-slate-900/80 py-1.5 px-4 rounded-full border border-slate-800">
            <span className="text-slate-300">Section 63 Bharatiya Sakshya Adhiniyam (BSA) 2023 compliant audit ledger</span>
            <span className="text-cyan-500">•</span>
            <span className="text-slate-300">Deterministic SHA-256 genesis-anchored chain of custody</span>
            <span className="text-cyan-500">•</span>
            <span className="text-slate-300">100% Dynamic multi-evidence learning without hardcoded mocks</span>
          </div>

          {/* Divider line */}
          <div className="w-full h-px bg-gradient-to-r from-transparent via-slate-800 to-transparent my-1" />

          {/* Bottom Status & Navigation Strip */}
          <div className="w-full flex flex-col lg:flex-row items-center justify-between gap-4 pt-1 text-xs">
            {/* Left: Sovereign Trust Tag */}
            <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-3 text-left">
              <div className="flex items-center gap-1.5 text-cyan-400 font-medium">
                <Shield className="w-3.5 h-3.5 text-[11px]" />
                <span>Secure | Trusted | For a Safer India</span>
              </div>
              <span className="hidden sm:inline text-slate-700">|</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-800/60">
                DPDP Act 2023 Compliant
              </span>
            </div>

            {/* Center: Security Node Icons */}
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-full bg-slate-900 border border-slate-700/80 flex items-center justify-center text-slate-400 hover:text-cyan-400 hover:border-cyan-500/50 transition cursor-pointer" title="End-to-End Encrypted Ledger">
                <Lock className="w-3.5 h-3.5" />
              </div>
              <div className="w-7 h-7 rounded-full bg-slate-900 border border-slate-700/80 flex items-center justify-center text-slate-400 hover:text-cyan-400 hover:border-cyan-500/50 transition cursor-pointer" title="Biometric / Cert Authenticated">
                <UserCheck className="w-3.5 h-3.5" />
              </div>
              <div className="w-7 h-7 rounded-full bg-slate-900 border border-slate-700/80 flex items-center justify-center text-slate-400 hover:text-cyan-400 hover:border-cyan-500/50 transition cursor-pointer" title="Decentralized Inter-Agency Node">
                <Network className="w-3.5 h-3.5" />
              </div>
              <div className="w-7 h-7 rounded-full bg-slate-900 border border-slate-700/80 flex items-center justify-center text-slate-400 hover:text-cyan-400 hover:border-cyan-500/50 transition cursor-pointer" title="Immutable Data Vault">
                <Database className="w-3.5 h-3.5" />
              </div>
            </div>

            {/* Right: Legal & Portal Links with Working Modals */}
            <div className="flex flex-wrap items-center gap-4 text-slate-400 text-[11px] font-mono">
              <button onClick={() => setActiveLegalModal('privacy')} className="hover:text-cyan-400 transition">Privacy Policy</button>
              <span className="text-slate-700">•</span>
              <button onClick={() => setActiveLegalModal('terms')} className="hover:text-cyan-400 transition">Terms of Service</button>
              <span className="text-slate-700">•</span>
              <button onClick={() => setActiveLegalModal('docs')} className="hover:text-cyan-400 transition">Documentation</button>
              <span className="text-slate-700">•</span>
              <button onClick={() => setActiveLegalModal('contact')} className="hover:text-cyan-400 transition">Contact Us</button>
            </div>
          </div>
        </div>
      </footer>

      {/* Legal & Compliance Modals with Working Cancel/Close Buttons */}
      {activeLegalModal && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fadeIn"
          onClick={() => setActiveLegalModal(null)}
        >
          <div
            className="bg-[#080E1E] border border-cyan-500/40 rounded-2xl max-w-lg w-full p-6 shadow-glow-cyan relative text-slate-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-cyan-900/40 mb-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider font-cyber text-cyan-300">
                {activeLegalModal === 'bsa' && 'Section 63 BSA 2023 Statutory Certification'}
                {activeLegalModal === 'dpdp' && 'DPDP Act 2023 Compliance & Security Scope'}
                {activeLegalModal === 'privacy' && 'Case Connect AI Privacy & Data Governance'}
                {activeLegalModal === 'terms' && 'Law Enforcement Operational Terms of Service'}
                {activeLegalModal === 'docs' && 'Investigation System Architecture & Manual'}
                {activeLegalModal === 'contact' && 'Law Enforcement Technical Support & Escalation'}
                {activeLegalModal === 'help' && 'System Manual & Officer Operational Guide'}
              </h3>
              <button
                onClick={() => setActiveLegalModal(null)}
                className="text-slate-400 hover:text-rose-400 text-xs font-mono p-1 rounded hover:bg-slate-900 transition"
                title="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs text-slate-300 space-y-3 leading-relaxed max-h-80 overflow-y-auto font-mono pr-1">
              {activeLegalModal === 'bsa' && (
                <>
                  <p>
                    <strong className="text-white">Statutory Foundation:</strong> Under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (replacing Section 65B of IEA), electronic records are admissible as primary electronic evidence subject to verifiable chain of custody, system integrity attestation, and cryptographic provenance.
                  </p>
                  <p>
                    <strong className="text-white">Immutable Audit Ledger:</strong> Every action performed within this terminal—including file ingestion, SHA-256 fingerprinting, entity merges, and report outputs—is permanently recorded in an append-only SHA-256 chained ledger with Genesis anchoring.
                  </p>
                  <p>
                    <strong className="text-white">Judicial Non-Repudiation:</strong> Hashes can be verified independently on demand by judicial officers and supervisory magistrates without exposing raw investigative notes.
                  </p>
                </>
              )}

              {activeLegalModal === 'dpdp' && (
                <>
                  <p>
                    <strong className="text-white">Digital Personal Data Protection (DPDP) Act 2023:</strong> The processing of personal data within Case Connect AI is conducted strictly under lawful law enforcement exemptions for crime prevention, detection, and investigation.
                  </p>
                  <p>
                    <strong className="text-white">Zero External Telemetry:</strong> All database operations, graph indices, and AI scoring algorithms operate in an offline, air-gapped environment. No data is transmitted to third-party servers, public LLMs, or cloud CDNs.
                  </p>
                </>
              )}

              {activeLegalModal === 'privacy' && (
                <>
                  <p>
                    <strong className="text-white">Law Enforcement Confidentiality:</strong> All ingested dockets, extracted entities, call detail records, and bank statements remain restricted to authorized case investigators and supervisory commanders.
                  </p>
                  <p>
                    <strong className="text-white">Role-Based Cryptographic Isolation:</strong> Read-only users cannot alter evidence chains; supervisory approvals are cryptographically signed.
                  </p>
                </>
              )}

              {activeLegalModal === 'terms' && (
                <>
                  <p>
                    <strong className="text-white">Authorized Agency Usage:</strong> Access is limited to authenticated police personnel, cyber cells, and authorized legal prosecutors with valid investigative warrant numbers.
                  </p>
                  <p>
                    <strong className="text-white">Audit Obligation:</strong> All queries, graph inspections, and report downloads are logged with timestamp and user ID.
                  </p>
                </>
              )}

              {activeLegalModal === 'docs' && (
                <>
                  <p>
                    <strong className="text-white">Pipeline Architecture:</strong> Ingestion (SHA-256 + MIME magic) &rarr; Extraction (Fast NER + Rule-based RegEx + OCR) &rarr; Entity Resolution &rarr; Graph Topology (Neo4j / Cytoscape) &rarr; Centrality & Hawala Ranking.
                  </p>
                  <p>
                    <strong className="text-white">AI Scoring Invariant:</strong> Risk scoring combines betweenness centrality, degree centrality, nocturnal call ratios, and monetary transaction velocities.
                  </p>
                </>
              )}

              {activeLegalModal === 'contact' && (
                <>
                  <p>
                    <strong className="text-white">Agency Technical Desk:</strong> Team UNITx (Smart India Hackathon SIH26189).
                  </p>
                  <p>
                    <strong className="text-white">Emergency Support:</strong> support@caseconnect.gov.in / Cyber Crime Coordination Center (I4C).
                  </p>
                </>
              )}

              {activeLegalModal === 'help' && (
                <>
                  <p>
                    <strong className="text-white">1. Evidence Ingestion:</strong> Drag and drop any FIR PDF, telecom CDR CSV, or banking statement. The system hashes the file with SHA-256 and extracts entities in real-time.
                  </p>
                  <p>
                    <strong className="text-white">2. Multi-Evidence Staging:</strong> Click &quot;Append More Evidence&quot; to cross-correlate secondary files (e.g. Bank CSV with Call logs).
                  </p>
                  <p>
                    <strong className="text-white">3. Network Topology:</strong> Click on any node in the graph to highlight direct connections and review phone numbers, accounts, and accomplice links.
                  </p>
                </>
              )}
            </div>

            <div className="mt-5 pt-3 border-t border-cyan-900/40 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setActiveLegalModal(null)}
                className="px-4 py-1.5 bg-[#0b1426] hover:bg-[#132240] text-slate-300 text-xs font-mono rounded-lg border border-slate-700 transition"
              >
                Cancel / Close
              </button>
              <button
                type="button"
                onClick={() => setActiveLegalModal(null)}
                className="cyber-btn-cut px-5 py-1.5 bg-gradient-to-r from-cyan-950 via-cyan-900 to-cyan-950 border border-cyan-400 text-cyan-300 font-cyber font-bold tracking-wider text-xs hover:bg-cyan-400 hover:text-black transition"
              >
                Acknowledge
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainRouter />
    </AuthProvider>
  );
}
