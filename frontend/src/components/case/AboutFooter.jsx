import React, { useState } from 'react';
import { Shield, Lock, Award, FileCheck, CheckCircle2, X } from 'lucide-react';

export const AboutFooter = () => {
  const [activeModal, setActiveModal] = useState(null);

  return (
    <footer id="about" className="relative z-10 w-full border-t border-white/[0.08] bg-ink/95 backdrop-blur-2xl pt-16 pb-12 px-6 lg:px-12 mt-16">
      <div className="max-w-6xl mx-auto flex flex-col items-center text-center space-y-6">
        {/* Brand Soft Emblem & Identity */}
        <div className="flex items-center justify-center gap-3">
          <span className="font-serif text-4xl sm:text-5xl tracking-tight text-text">
            UNIT<span className="text-accent font-bold">x</span>
          </span>
          <div className="w-8 h-8 rounded-full border border-accent/40 bg-accent/10 flex items-center justify-center text-accent text-xs">
            <Shield className="w-4 h-4" />
          </div>
        </div>

        {/* Functional Capability Subtitle */}
        <p className="max-w-2xl text-xs sm:text-sm text-muted font-normal leading-relaxed">
          Built by team UNITx for Smart India Hackathon. Automated telecommunication CDR, banking transaction, and multi-jurisdiction FIR correlation engine engineered for Indian law enforcement agencies.
        </p>

        {/* Compliance Badges Strip */}
        <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
          <span className="glass-pill px-3 py-1.5 text-[11px] font-mono text-muted flex items-center gap-1.5 border border-white/10">
            <FileCheck className="w-3.5 h-3.5 text-data" />
            <span>Section 63 BSA 2023 Certified Ledger</span>
          </span>
          <span className="glass-pill px-3 py-1.5 text-[11px] font-mono text-muted flex items-center gap-1.5 border border-white/10">
            <Lock className="w-3.5 h-3.5 text-accent" />
            <span>DPDP Act 2023 Air-Gapped Privacy</span>
          </span>
          <span className="glass-pill px-3 py-1.5 text-[11px] font-mono text-muted flex items-center gap-1.5 border border-white/10">
            <Award className="w-3.5 h-3.5 text-alert" />
            <span>NCRP Core Interop Standard</span>
          </span>
          <span className="glass-pill px-3 py-1.5 text-[11px] font-mono text-muted flex items-center gap-1.5 border border-white/10">
            <CheckCircle2 className="w-3.5 h-3.5 text-data" />
            <span>Strict Zero-Hallucination Contract</span>
          </span>
        </div>

        {/* Legal & Compliance Action Links */}
        <div className="flex flex-wrap items-center justify-center gap-4 text-xs font-mono text-muted pt-4 border-t border-white/[0.06] w-full">
          <button
            onClick={() => setActiveModal('bsa')}
            className="hover:text-accent transition-colors"
          >
            BSA 2023 Section 63 Mandate
          </button>
          <span className="text-white/20">•</span>
          <button
            onClick={() => setActiveModal('dpdp')}
            className="hover:text-accent transition-colors"
          >
            Data Protection Governance (DPDP)
          </button>
          <span className="text-white/20">•</span>
          <button
            onClick={() => setActiveModal('custody')}
            className="hover:text-accent transition-colors"
          >
            Cryptographic Chain of Custody
          </button>
        </div>

        {/* Copyright notice */}
        <p className="text-[10px] font-mono text-muted/60 pt-2">
          CaseConnect AI · Team UNITx · All forensic evidence ledgered deterministically.
        </p>
      </div>

      {/* Compliance Information Modal */}
      {activeModal && (
        <div
          className="fixed inset-0 z-50 bg-ink/85 backdrop-blur-md flex items-center justify-center p-4 animate-fadeIn"
          onClick={() => setActiveModal(null)}
        >
          <div
            className="glass max-w-lg w-full p-6 border border-white/15 relative shadow-2xl space-y-4 font-mono text-xs text-text"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <h3 className="font-serif text-2xl text-accent font-normal">
                {activeModal === 'bsa' && 'Section 63 BSA 2023 Statutory Certification'}
                {activeModal === 'dpdp' && 'DPDP Act 2023 Law Enforcement Scope'}
                {activeModal === 'custody' && 'Deterministic SHA-256 Ledger Lock'}
              </h3>
              <button
                onClick={() => setActiveModal(null)}
                className="text-muted hover:text-text p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-muted text-xs font-sans leading-relaxed">
              {activeModal === 'bsa' && (
                <p>
                  Electronic records admitted into court proceedings require verification of system integrity and absence of tampering under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023). Every evidence record uploaded to CaseConnect produces an immutable cryptographic ledger entry linked by SHA-256 hash chaining.
                </p>
              )}
              {activeModal === 'dpdp' && (
                <p>
                  In compliance with the Digital Personal Data Protection Act, 2023 (DPDP), all subscriber identity records (SDR) and telecommunication metadata are processed within strict law enforcement access control envelopes and stored with role-based segregation.
                </p>
              )}
              {activeModal === 'custody' && (
                <p>
                  Every file ingested (CSV, XLSX, PDF, TXT) is hashed via SHA-256 at the ingestion boundary. When court reports or analytical dossiers are generated, each page contains the cryptographic stamp and verification hash of the genesis artifact.
                </p>
              )}
            </div>

            <div className="pt-3 border-t border-white/[0.06] flex justify-end">
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-text font-mono text-xs transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </footer>
  );
};

export default AboutFooter;
