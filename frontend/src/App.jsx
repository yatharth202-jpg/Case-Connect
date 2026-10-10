import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import QuickCrimeAnalyser from './pages/QuickCrimeAnalyser';
import Cases from './pages/Cases';
import CaseDetail from './pages/CaseDetail';
import AuditLog from './pages/AuditLog';

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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#030712] flex items-center justify-center text-white text-xs">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-slate-600 border-t-[#38bdf8] rounded-full animate-spin"></div>
          <span>Validating Officer Credentials...</span>
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
        <div className="min-h-screen bg-[#030712] text-slate-100 flex flex-col">
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
    <div className="min-h-screen bg-[#030712] text-slate-100 flex flex-col">
      <Navbar onOpenLegalModal={setActiveLegalModal} />

      <main className="flex-1">
        {caseMatch ? (
          <CaseDetail caseId={caseMatch[1]} />
        ) : currentPath === '/audit' ? (
          <AuditLog />
        ) : currentPath === '/cases' ? (
          <Cases />
        ) : (
          <QuickCrimeAnalyser />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-[#0b1120] border-t border-[#1e293b] px-6 py-4 text-center text-[11px] text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Case Connect AI | Smart India Hackathon PS SIH26189 | Team UNITx</span>
          <span>Section 63 BSA 2023 & DPDP Act 2023 Compliant</span>
        </div>
      </footer>

      {/* Legal Modals */}
      {activeLegalModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg max-w-lg w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] mb-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                {activeLegalModal === 'bsa'
                  ? 'Section 63 BSA 2023 Legal Certification'
                  : 'DPDP Act 2023 Compliance'}
              </h3>
              <button
                onClick={() => setActiveLegalModal(null)}
                className="text-slate-400 hover:text-white text-xs font-mono"
              >
                [CLOSE]
              </button>
            </div>

            <div className="text-xs text-slate-300 space-y-3 leading-relaxed max-h-80 overflow-y-auto">
              {activeLegalModal === 'bsa' ? (
                <>
                  <p>
                    <strong>Statutory Foundation:</strong> Under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023, electronic records are admissible as primary electronic evidence subject to verifiable chain of custody, system integrity attestation, and cryptographic provenance.
                  </p>
                  <p>
                    <strong>Immutable Audit Log:</strong> Every action performed within this terminal—including file ingestion, SHA-256 fingerprinting, entity merges, and report outputs—is permanently recorded in an append-only SHA-256 chained ledger with Genesis anchoring.
                  </p>
                  <p>
                    <strong>Non-Repudiation:</strong> Hashes can be verified independently on demand by judicial officers and supervisory magistrates.
                  </p>
                </>
              ) : (
                <>
                  <p>
                    <strong>Digital Personal Data Protection (DPDP) Act 2023:</strong> The processing of personal data within Case Connect AI is conducted strictly under lawful law enforcement exemptions for crime prevention, detection, and investigation.
                  </p>
                  <p>
                    <strong>Zero External Telemetry:</strong> All database operations, graph indices, and AI scoring algorithms operate in an offline, air-gapped environment. No data is transmitted to third-party servers, public LLMs, or cloud CDNs.
                  </p>
                </>
              )}
            </div>

            <div className="mt-6 pt-3 border-t border-[#1e293b] text-right">
              <button
                onClick={() => setActiveLegalModal(null)}
                className="px-4 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-white text-xs rounded transition-colors"
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
