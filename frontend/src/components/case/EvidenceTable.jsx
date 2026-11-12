import React, { useState } from 'react';
import { Search, FileText, CheckCircle2, Eye, Shield, X, Filter } from 'lucide-react';

export const EvidenceTable = ({ evidenceRecords = [] }) => {
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'cdr' | 'bank'
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEvidence, setSelectedEvidence] = useState(null);

  const defaultRecords = [
    {
      id: 'EV-101',
      time: '12-Oct-2026 18:30 IST',
      type: 'FIR_COMPLAINT',
      typeBadge: 'FIR',
      observation: 'Statutory cyber fraud & syndicate Hawala complaint registered under IPC 420/120B & Section 63 BSA',
      source: 'FIR-409-2026-HAWALA-SYNDICATE.txt',
      hash: 'a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0',
      entities: 'Complainant statement, IPC 420/120B, BNS Sec 318(4), ₹4.85 Cr target loss'
    },
    {
      id: 'EV-102',
      time: '14-Oct-2026 14:40 IST',
      type: 'BANK_TXN',
      typeBadge: 'BANK',
      observation: '142 layered IMPS/RTGS tranches totalling ₹1,84,00,000 routed through Lotus Overseas Impex Axis mule account',
      source: 'Hawala_AxisBank_Stat.csv',
      hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      entities: 'Axis A/C 918020049219014, HDFC A/C 50200084911928, ₹1.84 Cr'
    },
    {
      id: 'EV-103',
      time: '15-Oct-2026 11:20 IST',
      type: 'BANK_TXN',
      typeBadge: 'BANK',
      observation: 'Multi-sheet Bullion bullion acquisition ledger converting ₹1.84 Cr digital fund into physical gold bullion',
      source: 'HDFC_Bullion_Merchant_Stat.xlsx',
      hash: 'c8f7e6d5b4a39281706f5e4d3c2b1a0987654321fedcba0987654321abcdef12',
      entities: 'Bullion Merchant A/C 50200084911928, 2.85 Kg 24K Gold Bullion Bars'
    },
    {
      id: 'EV-104',
      time: '14-Oct-2026 02:18 IST',
      type: 'CDR_CALL',
      typeBadge: 'CDR',
      observation: '1,842 call events identified; 41-call coordinated midnight burst via Noida SIM-Box tower bypass to Surat courier handler',
      source: 'CDR_Dump_Delhi_Noida.xlsx',
      hash: '9f83a45c6b72d14e38910452cf8a1e2b4895018a93cb4781920194857682910a',
      entities: '+91 98112 04812 (KC Seth), +91 98711 92834 (Farhan Khan), Tower DEL-NOI-04'
    },
    {
      id: 'EV-105',
      time: '14-Oct-2026 04:52 IST',
      type: 'VEHICLE_LOG',
      typeBadge: 'VEHICLES',
      observation: '38 ANPR toll camera captures confirming Fortuner DL01CZ8821 & Creta HR26DK4902 cash transport across Delhi-Surat corridor',
      source: 'vehicles_anpr_log.csv',
      hash: '4b7a2d9c1e3f5a8b6c0d2e4f7a9b1c3d5e8f0a2b4c6d8e1f3a5b7c9d2e4f6a8b',
      entities: 'DL01CZ8821 (Armoured Fortuner), HR26DK4902 (Creta Escort), Baroda Toll 04:52'
    },
    {
      id: 'EV-106',
      time: '14-Oct-2026 02:22 IST',
      type: 'AUDIO_WIRETAP',
      typeBadge: 'AUDIO',
      observation: 'Forensic wiretap audio intercepts confirming physical token (₹10 note Parchi #7729) delivery instruction',
      source: 'phone_transcripts.json',
      hash: 'f6e5d4c3b2a10987654321fedcba0987654321abcdef0123456789abcdef0123',
      entities: 'Speaker KC Seth: "Courier Farhan se ₹42.5 Lakh lo token note 7729 verify karke"'
    },
    {
      id: 'EV-107',
      time: '14-Oct-2026 03:05 IST',
      type: 'IP_SESSION',
      typeBadge: 'IP',
      observation: 'Static proxy IP session initiated from gateway 103.24.18.9 accessing mule netbanking portals',
      source: 'Firewall_Access_Log.txt',
      hash: '7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d',
      entities: 'IP: 103.24.18.9, Port 8443, IMEI 864201041920391, Protocol TLS 1.3'
    }
  ];

  const records = evidenceRecords.length > 0 ? evidenceRecords : defaultRecords;

  const filtered = records.filter(r => {
    const matchType = activeTab === 'all' || r.typeBadge.toLowerCase() === activeTab;
    const matchQuery = !searchQuery ||
      r.observation.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.hash.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.source.toLowerCase().includes(searchQuery.toLowerCase());
    return matchType && matchQuery;
  });

  const [tamperedId, setTamperedId] = useState(null);

  const toggleTamperSimulation = () => {
    if (tamperedId) {
      setTamperedId(null);
    } else {
      setTamperedId('EV-102');
    }
  };

  return (
    <section id="evidence" className="w-full py-16 px-4 sm:px-6 max-w-6xl mx-auto relative z-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass-sm text-[11px] font-mono text-accent mb-2">
            <Shield className="w-3.5 h-3.5 text-accent" />
            <span>SECTION 05 · CHAIN OF CUSTODY INTEGRITY LEDGER</span>
          </div>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-text tracking-tight">
            Verified forensic evidence ledger.
          </h2>
          <p className="text-xs sm:text-sm text-muted font-normal mt-1.5 max-w-xl">
            Cryptographically anchored artifacts under Section 63 BSA 2023 with SHA-256 chain of custody.
          </p>
        </div>

        {/* Tab Controls & Tamper Simulation Button */}
        <div className="flex flex-wrap items-center gap-2 self-start md:self-auto">
          <button
            type="button"
            onClick={toggleTamperSimulation}
            className={`glass-pill px-3 py-1.5 text-xs font-mono transition-all border ${
              tamperedId
                ? 'bg-alert/20 border-alert text-alert font-bold shadow-glow-alert'
                : 'text-muted hover:text-text hover:border-white/20'
            }`}
            title="Demonstrate Section 63 BSA 2023 Tamper Detection"
          >
            {tamperedId ? '↺ Restore Cryptographic Hash' : '⚡ Simulate Tamper Demo'}
          </button>

          <div className="glass-pill p-1 flex flex-wrap items-center gap-1 text-xs font-mono">
            {[
              { id: 'all', label: `All (${records.length})` },
              { id: 'bank', label: 'Bank' },
              { id: 'cdr', label: 'CDR' },
              { id: 'fir', label: 'FIR' },
              { id: 'vehicles', label: 'Vehicles' },
              { id: 'audio', label: 'Audio' },
              { id: 'ip', label: 'IP Logs' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded-full transition-all ${
                  activeTab === tab.id
                    ? 'bg-accent/20 text-accent font-semibold border border-accent/40 shadow-sm'
                    : 'text-muted hover:text-text hover:bg-white/[0.04]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tamper Alert Demonstration Banner */}
      {tamperedId && (
        <div className="mb-4 p-4 rounded-xl glass border border-alert/50 bg-alert/10 text-xs font-mono text-alert flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fadeIn shadow-glow-alert">
          <div className="space-y-1">
            <span className="font-bold flex items-center gap-1.5">
              <span>⚠ CRYPTOGRAPHIC TAMPER DETECTED ON RECORD #{tamperedId}</span>
            </span>
            <p className="text-[11px] text-muted font-sans">
              1-byte payload alteration detected. Genesis hash does not match current recalculated SHA-256 hash. Inadmissible under Section 63 BSA 2023.
            </p>
          </div>
          <button
            onClick={toggleTamperSimulation}
            className="px-3 py-1.5 rounded-lg bg-alert text-ink font-mono font-bold hover:bg-alert/90 shrink-0 self-start sm:self-auto"
          >
            Restore Genesis Ledger
          </button>
        </div>
      )}

      {/* Search Bar */}
      <div className="mb-4 relative max-w-sm">
        <Search className="w-4 h-4 text-muted absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search hash, keyword, or filename..."
          className="w-full pl-9 pr-4 py-2 rounded-xl bg-white/[0.04] border border-white/10 text-xs font-mono text-text focus:outline-none focus:border-accent"
        />
      </div>

      {/* Main Glass Table Container */}
      <div className="glass rounded-2xl border border-white/10 overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-muted text-[10px] uppercase tracking-wider bg-white/[0.02]">
                <th className="py-3.5 px-4 font-semibold">Timestamp (IST)</th>
                <th className="py-3.5 px-4 font-semibold">Artifact Type</th>
                <th className="py-3.5 px-4 font-semibold">Observation & Finding</th>
                <th className="py-3.5 px-4 font-semibold">Source File</th>
                <th className="py-3.5 px-4 font-semibold">SHA-256 Ledger Hash</th>
                <th className="py-3.5 px-4 font-semibold text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.05]">
              {filtered.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => setSelectedEvidence(row)}
                  className="hover:bg-white/[0.03] transition-colors cursor-pointer group"
                >
                  <td className="py-3 px-4 text-muted whitespace-nowrap text-[11px]">
                    {row.time}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      row.typeBadge === 'BANK' ? 'bg-accent/15 text-accent border border-accent/30' :
                      row.typeBadge === 'CDR' ? 'bg-data/15 text-data border border-data/30' :
                      'bg-alert/15 text-alert border border-alert/30'
                    }`}>
                      {row.type}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-text font-sans text-xs max-w-sm truncate group-hover:text-accent transition-colors">
                    {row.observation}
                  </td>
                  <td className="py-3 px-4 text-muted text-[11px] whitespace-nowrap">
                    {row.source}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <span className="flex items-center gap-1.5 text-data text-[11px]">
                      <CheckCircle2 className="w-3.5 h-3.5 text-data" />
                      <span>{row.hash.slice(0, 14)}...</span>
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedEvidence(row);
                      }}
                      className="glass-pill px-2.5 py-1 text-[10px] text-muted hover:text-text hover:border-accent/40 transition-colors inline-flex items-center gap-1"
                    >
                      <Eye className="w-3 h-3 text-accent" />
                      <span>Preview</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Forensic Record Detail Preview Modal */}
      {selectedEvidence && (
        <div
          className="fixed inset-0 z-50 bg-ink/85 backdrop-blur-md flex items-center justify-center p-4 animate-fadeIn"
          onClick={() => setSelectedEvidence(null)}
        >
          <div
            className="glass max-w-lg w-full p-6 border border-white/15 relative shadow-2xl space-y-4 font-mono text-xs"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <div>
                <span className="text-[10px] text-accent uppercase tracking-wider">
                  [{selectedEvidence.type}]
                </span>
                <h4 className="font-serif text-xl text-text font-normal mt-0.5">
                  Record ID: {selectedEvidence.id}
                </h4>
              </div>
              <button
                onClick={() => setSelectedEvidence(null)}
                className="text-muted hover:text-text p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Cryptographic SHA-256 Block */}
            <div className="p-3 bg-white/[0.03] rounded-xl border border-white/10 space-y-1">
              <span className="text-[10px] text-muted uppercase">SHA-256 Genesis-Anchored Hash</span>
              <p className="text-accent break-all text-[11px] select-all">
                {selectedEvidence.hash}
              </p>
            </div>

            <div className="space-y-2 text-muted leading-relaxed">
              <p>
                <strong className="text-text">Observation:</strong> {selectedEvidence.observation}
              </p>
              <p>
                <strong className="text-text">Source Evidence File:</strong> {selectedEvidence.source}
              </p>
              <p>
                <strong className="text-text">Correlated Entities:</strong> {selectedEvidence.entities}
              </p>
              <p>
                <strong className="text-text">Chain of Custody Custodian:</strong> Cyber Cell Autonomous Ingestion Pipeline
              </p>
            </div>

            <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-[10px] text-data">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Section 63 BSA 2023 Statutory Certificate Verified</span>
              </span>
              <span className="text-muted">Air-Gapped Vault</span>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default EvidenceTable;
