import React, { useState, useEffect, useCallback } from 'react';
import { reportsApi } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function ReportGenerator({ caseId, isViewer }) {
  const { user } = useAuth();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [copiedHash, setCopiedHash] = useState(null);

  // Form State
  const [reportTitle, setReportTitle] = useState('Investigation Court Dossier');
  const [format, setFormat] = useState('pdf');
  const [officerName, setOfficerName] = useState(user?.username || '');
  const [officerRank, setOfficerRank] = useState('Inspector of Police');
  const [officerStation, setOfficerStation] = useState('Cyber Crime Police Station');
  const [officerUnit, setOfficerUnit] = useState('Special Investigation Division');
  const [officerRemarks, setOfficerRemarks] = useState('');

  // Section Checkbox Grid
  const [sections, setSections] = useState({
    overview: true,
    entities: true,
    cdr: true,
    financial: true,
    documents: true,
    audit: true,
  });

  const toggleSection = (key) => {
    setSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const loadReports = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    try {
      const data = await reportsApi.list(caseId);
      setReports(data || []);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch report history');
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (isViewer) return;
    setGenerating(true);
    setError('');
    setSuccessMsg('');

    try {
      const res = await reportsApi.create(caseId, {
        report_title: reportTitle.trim() || 'Investigation Court Dossier',
        format,
        sections,
        officer_name: officerName.trim(),
        officer_rank: officerRank.trim(),
        officer_station: officerStation.trim(),
        officer_unit: officerUnit.trim(),
        officer_remarks: officerRemarks.trim(),
      });

      setSuccessMsg(`Report generated successfully with SHA-256: ${res.sha256.substring(0, 16)}...`);
      await loadReports();
    } catch (err) {
      setError(err.response?.data?.detail || 'Report generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (report) => {
    try {
      await reportsApi.download(report.id, report.filename);
    } catch (err) {
      alert('Failed to download report file');
    }
  };

  const handleQuickJsonExport = async () => {
    try {
      await reportsApi.exportJson(caseId, `case_dossier_${caseId.substring(0, 8)}.json`);
    } catch (err) {
      alert('Failed to export JSON archive');
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(id);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* 1. Statutory Compliance Banner (Section 63 BSA 2023) */}
      <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-[#030712] border border-[#0284c7] rounded-md flex items-center justify-center text-[#38bdf8] flex-shrink-0 mt-0.5">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-white tracking-tight">
                  Statutory Electronic Evidence Compliance
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded border bg-emerald-950/60 text-emerald-300 border-emerald-800">
                  SECTION 63 BSA 2023 CERTIFIED
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
                Generates a formal court certificate and forensic dossier under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (formerly Section 65B Indian Evidence Act). Includes SHA-256 evidence digests, cryptographic audit head hash, and officer affirmation.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            <button
              onClick={handleQuickJsonExport}
              className="px-3 py-1.5 bg-[#030712] hover:bg-[#1e293b] text-slate-300 hover:text-white border border-[#334155] text-xs font-mono rounded transition-colors flex items-center gap-1.5"
              title="One-click machine-readable JSON export"
            >
              <svg className="w-3.5 h-3.5 text-[#38bdf8]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>Export Full JSON</span>
            </button>
          </div>
        </div>
      </div>

      {/* Error & Success Messages */}
      {error && (
        <div className="p-3 bg-rose-950/40 border border-rose-800 text-rose-300 text-xs rounded">
          {error}
        </div>
      )}
      {successMsg && (
        <div className="p-3 bg-emerald-950/40 border border-emerald-800 text-emerald-300 text-xs font-mono rounded">
          {successMsg}
        </div>
      )}

      {/* 2. Dossier Generation Configuration Grid */}
      <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg p-6">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-4 pb-2 border-b border-[#1e293b]">
          Dossier Parameters & Certifying Officer Details
        </h3>

        <form onSubmit={handleGenerate} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Report Title
              </label>
              <input
                type="text"
                value={reportTitle}
                onChange={(e) => setReportTitle(e.target.value)}
                placeholder="e.g. Court Dossier - Case #101"
                className="w-full bg-[#030712] border border-[#334155] px-3 py-2 rounded text-xs text-white focus:outline-none focus:border-[#0284c7]"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Export Format
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setFormat('pdf')}
                  className={`px-3 py-2 text-xs font-medium rounded border text-center transition-colors ${
                    format === 'pdf'
                      ? 'bg-[#0284c7] text-white border-[#0284c7] font-semibold'
                      : 'bg-[#030712] text-slate-400 border-[#334155] hover:text-white'
                  }`}
                >
                  Court Dossier PDF (Sec 63)
                </button>
                <button
                  type="button"
                  onClick={() => setFormat('json')}
                  className={`px-3 py-2 text-xs font-medium rounded border text-center transition-colors ${
                    format === 'json'
                      ? 'bg-[#0284c7] text-white border-[#0284c7] font-semibold'
                      : 'bg-[#030712] text-slate-400 border-[#334155] hover:text-white'
                  }`}
                >
                  Machine-Readable JSON Archive
                </button>
              </div>
            </div>
          </div>

          {/* Section Checkbox Grid */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-2">
              Dossier Content Modules (Section Selection)
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
              {[
                { key: 'overview', label: '1. Case Intelligence Overview', desc: 'FIR, police station, crime category' },
                { key: 'entities', label: '2. Entities of Interest Inventory', desc: 'Persons, phones, accounts, vehicles' },
                { key: 'cdr', label: '3. Telecommunication & CDR Analysis', desc: 'Call frequency pairs and timelines' },
                { key: 'financial', label: '4. Financial Money Trail & Routing', desc: 'Multi-hop transactions and anomalies' },
                { key: 'documents', label: '5. Document Text Findings', desc: 'Approved entities from FIRs and complaints' },
                { key: 'audit', label: '6. Cryptographic Audit Log', desc: 'SHA-256 chain verification status' },
              ].map((sec) => (
                <div
                  key={sec.key}
                  onClick={() => toggleSection(sec.key)}
                  className={`p-2.5 rounded border cursor-pointer select-none transition-colors ${
                    sections[sec.key]
                      ? 'bg-[#0284c7]/10 border-[#0284c7] text-white'
                      : 'bg-[#030712] border-[#334155] text-slate-400 hover:border-slate-500'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={sections[sec.key]}
                      onChange={() => {}}
                      className="rounded bg-[#030712] border-[#334155] text-[#0284c7] focus:ring-0"
                    />
                    <span className="text-xs font-semibold">{sec.label}</span>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 pl-5">{sec.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Certifying Officer Details */}
          <div className="p-4 bg-[#030712] border border-[#1e293b] rounded-md space-y-3">
            <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wide">
              Certifying Officer Information (Affirmed in Section 63 BSA Certificate)
            </span>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Officer Name</label>
                <input
                  type="text"
                  value={officerName}
                  onChange={(e) => setOfficerName(e.target.value)}
                  className="w-full bg-[#0b1120] border border-[#334155] px-2.5 py-1.5 rounded text-xs text-white focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Designation / Rank</label>
                <input
                  type="text"
                  value={officerRank}
                  onChange={(e) => setOfficerRank(e.target.value)}
                  className="w-full bg-[#0b1120] border border-[#334155] px-2.5 py-1.5 rounded text-xs text-white focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Police Station / Cell</label>
                <input
                  type="text"
                  value={officerStation}
                  onChange={(e) => setOfficerStation(e.target.value)}
                  className="w-full bg-[#0b1120] border border-[#334155] px-2.5 py-1.5 rounded text-xs text-white focus:outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Department / Unit</label>
                <input
                  type="text"
                  value={officerUnit}
                  onChange={(e) => setOfficerUnit(e.target.value)}
                  className="w-full bg-[#0b1120] border border-[#334155] px-2.5 py-1.5 rounded text-xs text-white focus:outline-none"
                  required
                />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            {!isViewer && (
              <button
                type="submit"
                disabled={generating}
                className="px-5 py-2.5 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded shadow transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {generating ? (
                  <>
                    <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>Generating Cryptographic Dossier...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span>Generate Court Report ({format.toUpperCase()})</span>
                  </>
                )}
              </button>
            )}
          </div>
        </form>
      </div>

      {/* 3. Generated Report History Table */}
      <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg overflow-hidden">
        <div className="px-5 py-3 border-b border-[#1e293b] flex items-center justify-between">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">
            Certified Report Registry & Hash Log ({reports.length})
          </h3>
          <button
            onClick={loadReports}
            className="text-[11px] text-slate-400 hover:text-white font-mono"
          >
            [REFRESH]
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-slate-400 font-mono">
            Loading report records...
          </div>
        ) : reports.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400">
            No reports have been generated for this case yet. Configure parameters above to produce a Section 63 BSA 2023 dossier.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#030712] text-slate-400 border-b border-[#1e293b]">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Report Title</th>
                  <th className="px-4 py-2.5 font-medium">Format</th>
                  <th className="px-4 py-2.5 font-medium">Certifying Officer</th>
                  <th className="px-4 py-2.5 font-medium">Generated At</th>
                  <th className="px-4 py-2.5 font-medium">SHA-256 Digest</th>
                  <th className="px-4 py-2.5 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e293b]">
                {reports.map((r) => (
                  <tr key={r.id} className="hover:bg-[#111c35] transition-colors">
                    <td className="px-4 py-3 font-semibold text-white">
                      {r.report_title}
                    </td>

                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
                        r.format === 'pdf'
                          ? 'bg-rose-950/60 text-rose-300 border-rose-800'
                          : 'bg-blue-950/60 text-blue-300 border-blue-800'
                      }`}>
                        {r.format.toUpperCase()}
                      </span>
                    </td>

                    <td className="px-4 py-3 text-slate-300">
                      <div>{r.officer_name || r.generated_by}</div>
                      {r.officer_rank && (
                        <div className="text-[10px] text-slate-400">{r.officer_rank}</div>
                      )}
                    </td>

                    <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                      {new Date(r.created_at).toLocaleString()}
                    </td>

                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-[11px] text-slate-300 bg-[#030712] px-1.5 py-0.5 rounded border border-[#1e293b]">
                          {r.sha256.substring(0, 10)}...{r.sha256.substring(54)}
                        </span>
                        <button
                          onClick={() => copyToClipboard(r.sha256, r.id)}
                          className="text-slate-400 hover:text-white p-1"
                          title="Copy full SHA-256 hash"
                        >
                          {copiedHash === r.id ? (
                            <span className="text-emerald-400 text-[10px] font-mono">Copied</span>
                          ) : (
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                          )}
                        </button>
                      </div>
                    </td>

                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDownload(r)}
                        className="px-3 py-1 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded transition-colors inline-flex items-center gap-1"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        <span>Download</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
