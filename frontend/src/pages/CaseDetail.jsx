import React, { useState, useEffect } from 'react';
import { casesApi, evidenceApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import GraphCanvas from '../components/GraphCanvas';
import MoneyTrailCanvas from '../components/MoneyTrailCanvas';
import EntityReview from '../components/EntityReview';
import ReportGenerator from '../components/ReportGenerator';
import LeadAdvisor from '../components/LeadAdvisor';
import MasterProfiles from '../components/MasterProfiles';
import DashboardOverview from '../components/DashboardOverview';
import TimelineView from '../components/TimelineView';
import CaseSettings from '../components/CaseSettings';
import HawalaSyndicateExplorer from '../components/HawalaSyndicateExplorer';


export default function CaseDetail({ caseId }) {
  const { isViewer } = useAuth();
  const [caseData, setCaseData] = useState(null);
  const [evidenceList, setEvidenceList] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState('');

  // Verification results map: { [evidenceId]: { valid: bool, stored: str, computed: str } }
  const [verificationMap, setVerificationMap] = useState({});
  const [verifyingId, setVerifyingId] = useState(null);

  // Copy notification
  const [copiedHash, setCopiedHash] = useState(null);

  // Phase 3 Mapping & Ingestion State
  const [mappingModalOpen, setMappingModalOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [activePreview, setActivePreview] = useState(null);
  const [activeMapping, setActiveMapping] = useState({});
  const [selectedFileType, setSelectedFileType] = useState('cdr');
  const [targetEvidenceId, setTargetEvidenceId] = useState(null);

  // Ingestion Job state
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [jobProgress, setJobProgress] = useState(0);
  const [jobSteps, setJobSteps] = useState([]);

  // Data Quality Modal
  const [qualityModalOpen, setQualityModalOpen] = useState(false);
  const [qualityData, setQualityData] = useState(null);

  const fetchCaseDetails = async () => {
    setLoading(true);
    try {
      const [c, ev] = await Promise.all([
        casesApi.get(caseId),
        evidenceApi.list(caseId),
      ]);
      setCaseData(c);
      setEvidenceList(ev);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load case data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchCaseDetails();
    }
  }, [caseId]);

  // Poll Job status
  useEffect(() => {
    let interval = null;
    if (jobId && jobStatus !== 'done' && jobStatus !== 'failed') {
      interval = setInterval(async () => {
        try {
          const res = await evidenceApi.getJob(jobId);
          setJobStatus(res.status);
          setJobProgress(res.progress);
          setJobSteps(res.steps || []);
          if (res.status === 'done') {
            clearInterval(interval);
            // Refresh evidence list
            const refreshed = await evidenceApi.list(caseId);
            setEvidenceList(refreshed);
          }
        } catch (e) {
          clearInterval(interval);
        }
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [jobId, jobStatus]);

  const handleFileUpload = async (e) => {
    const files = e.target.files || e.dataTransfer?.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadProgress(0);
    setUploadError('');

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      await evidenceApi.upload(caseId, formData, (progressEvent) => {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(percent);
      });
      const refreshed = await evidenceApi.list(caseId);
      setEvidenceList(refreshed);
    } catch (err) {
      setUploadError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleVerify = async (evId) => {
    setVerifyingId(evId);
    try {
      const result = await evidenceApi.verify(evId);
      setVerificationMap((prev) => ({
        ...prev,
        [evId]: result,
      }));
    } catch (err) {
      setVerificationMap((prev) => ({
        ...prev,
        [evId]: { valid: false, error: 'Verification failed' },
      }));
    } finally {
      setVerifyingId(null);
    }
  };

  const handleOpenMapping = async (evId) => {
    setTargetEvidenceId(evId);
    setPreviewLoading(true);
    setMappingModalOpen(true);
    setJobId(null);
    setJobStatus(null);

    try {
      const preview = await evidenceApi.preview(evId);
      setActivePreview(preview);
      setSelectedFileType(preview.detected_type !== 'unknown' ? preview.detected_type : 'cdr');
      const initialMap = {};
      Object.entries(preview.suggested_mapping).forEach(([h, val]) => {
        initialMap[h] = val.canonical;
      });
      setActiveMapping(initialMap);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to analyze file preview');
      setMappingModalOpen(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleConfirmMappingAndIngest = async () => {
    try {
      // 1. Confirm Mapping
      await evidenceApi.confirmMapping(targetEvidenceId, {
        file_type: selectedFileType,
        mapping: activeMapping,
      });

      // 2. Start Ingestion Job
      const jobRes = await evidenceApi.startIngest(targetEvidenceId);
      setJobId(jobRes.job_id);
      setJobStatus('queued');
      setJobProgress(10);
      setJobSteps(['Queued for ingestion worker']);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to start ingestion job');
    }
  };

  const handleViewQuality = async (evId) => {
    try {
      const q = await evidenceApi.getQuality(evId);
      setQualityData(q);
      setQualityModalOpen(true);
    } catch (err) {
      alert('Failed to retrieve data quality summary');
    }
  };

  const handleDelete = async (evId, fileName) => {
    if (!window.confirm(`Are you sure you want to remove evidence file "${fileName}"? This action is logged permanently.`)) {
      return;
    }
    try {
      await evidenceApi.delete(evId);
      setEvidenceList((prev) => prev.filter((item) => item.id !== evId));
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete evidence file');
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(id);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="inline-block animate-spin w-6 h-6 border-2 border-slate-600 border-t-[#38bdf8] rounded-full mb-2"></div>
        <p className="text-xs text-slate-400">Loading case workspace...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center">
        <div className="p-6 bg-[#0b1120] border border-rose-900 rounded-lg">
          <div className="text-rose-400 font-bold text-sm mb-2">Access Notification</div>
          <p className="text-xs text-slate-300 mb-4">{error}</p>
          <a
            href="/cases"
            className="inline-block px-4 py-2 bg-[#1e293b] hover:bg-[#334155] text-white text-xs font-medium rounded transition-colors"
          >
            Return to Cases Repository
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      {/* Case Header */}
      <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg p-6 mb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-mono text-[#38bdf8] bg-[#030712] px-2 py-0.5 rounded border border-[#1e293b]">
                Case ID: {caseData.id}
              </span>
              <span
                className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border font-semibold ${
                  caseData.priority === 'high'
                    ? 'bg-rose-950/60 text-rose-300 border-rose-800'
                    : caseData.priority === 'medium'
                    ? 'bg-amber-950/60 text-amber-300 border-amber-800'
                    : 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                }`}
              >
                {caseData.priority} Priority
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                Opened: {new Date(caseData.created_at).toLocaleString()}
              </span>
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">{caseData.title}</h1>
            {caseData.description && (
              <p className="text-xs text-slate-400 mt-1 max-w-2xl">{caseData.description}</p>
            )}
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            <span className="text-xs text-slate-400 bg-[#030712] border border-[#1e293b] px-3 py-1.5 rounded font-mono">
              Status: <span className="text-emerald-400 font-semibold">{caseData.status.toUpperCase()}</span>
            </span>
            <button
              onClick={() => setSettingsModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-[#1e293b] hover:bg-[#334155] hover:text-white rounded border border-[#334155] transition-colors"
              title="Configure Case Thresholds & Model Weights"
            >
              <svg className="w-3.5 h-3.5 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Case Settings
            </button>
          </div>
        </div>

        {/* Tab Subnav */}
        <div className="flex items-center gap-1 border-t border-[#1e293b] mt-6 pt-3 overflow-x-auto">
          {[
            { id: 'hawala', label: 'Target Dossier & Attribution' },
            { id: 'overview', label: 'Executive Dashboard' },
            { id: 'timeline', label: 'Chronological Timeline' },
            { id: 'evidence', label: `Evidence Repository (${evidenceList.length})` },
            { id: 'graph', label: 'Investigation Graph' },
            { id: 'money', label: 'Money Trail' },
            { id: 'review', label: 'Entity Review' },
            { id: 'profiles', label: 'Master Profiles' },
            { id: 'leads', label: 'Lead Advisor' },
            { id: 'reports', label: 'Report Generator' },
          ].map((tab) => (

            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-[#0284c7] text-white font-semibold'
                  : 'text-slate-400 hover:text-white hover:bg-[#1e293b]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab: Hawala Dossier */}
      {activeTab === 'hawala' && (
        <HawalaSyndicateExplorer
          caseId={caseId}
          onOpenTab={(tabId) => setActiveTab(tabId)}
        />
      )}

      {/* Tab: Executive Dashboard (Phase 9) */}
      {activeTab === 'overview' && (
        <DashboardOverview
          caseId={caseId}
          isViewer={isViewer}
          onNavigateTab={(tab) => setActiveTab(tab)}
        />
      )}

      {/* Tab: Chronological Timeline (Phase 9) */}
      {activeTab === 'timeline' && (
        <TimelineView caseId={caseId} isViewer={isViewer} />
      )}

      {/* Tab 1: Evidence Repository */}
      {activeTab === 'evidence' && (
        <div className="space-y-6">
          {/* Upload Dropzone */}
          {!isViewer && (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                handleFileUpload(e);
              }}
              className="border-2 border-dashed border-[#334155] hover:border-[#38bdf8] bg-[#0b1120] rounded-lg p-8 text-center transition-colors"
            >
              <svg className="w-8 h-8 text-slate-500 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <h3 className="text-xs font-semibold text-white">
                Drag and drop investigation evidence files here
              </h3>
              <p className="text-[11px] text-slate-400 mt-1">
                Supported formats: CSV, XLSX, JSON, JSONL, TXT, PDF, DOCX (Max 200MB tabular, 20MB document)
              </p>

              <label className="mt-4 inline-block px-4 py-2 bg-[#1e293b] hover:bg-[#334155] text-white text-xs font-medium rounded cursor-pointer transition-colors">
                <span>Select Files from Machine</span>
                <input
                  type="file"
                  multiple
                  accept=".csv,.xlsx,.json,.jsonl,.txt,.pdf,.docx"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>

              {uploading && (
                <div className="mt-4 max-w-xs mx-auto">
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span>Hashing & Ingesting Stream...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-[#030712] h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-[#0284c7] h-full transition-all duration-200"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {uploadError && (
                <div className="mt-4 p-2 bg-rose-950/60 border border-rose-800 rounded text-rose-300 text-xs max-w-md mx-auto">
                  {uploadError}
                </div>
              )}
            </div>
          )}

          {/* Evidence Files List */}
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg overflow-hidden">
            <div className="p-4 border-b border-[#1e293b] flex items-center justify-between">
              <h2 className="text-xs font-bold text-white uppercase tracking-wider">
                Chain of Custody Repository ({evidenceList.length} Files)
              </h2>
              <span className="text-[11px] text-slate-400 font-mono">
                Section 63 BSA 2023 Digital Integrity
              </span>
            </div>

            {evidenceList.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No evidence files uploaded to this case yet. Drop telecom CDR, bank statements, or FIRs above.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#030712] text-slate-400 font-mono text-[11px] uppercase border-b border-[#1e293b]">
                    <tr>
                      <th className="px-4 py-3">File Name</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">File Size</th>
                      <th className="px-4 py-3">SHA-256 Fingerprint</th>
                      <th className="px-4 py-3">Integrity</th>
                      <th className="px-4 py-3">Ingestion Pipeline</th>
                      {!isViewer && <th className="px-4 py-3 text-right">Actions</th>}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1e293b]">
                    {evidenceList.map((file) => {
                      const ver = verificationMap[file.id];
                      return (
                        <tr key={file.id} className="hover:bg-[#030712]/40 transition-colors">
                          <td className="px-4 py-3 font-medium text-white flex items-center gap-2">
                            <svg className="w-4 h-4 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            <span className="truncate max-w-xs" title={file.original_name}>
                              {file.original_name}
                            </span>
                          </td>

                          <td className="px-4 py-3">
                            <span
                              className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
                                file.status === 'ingested'
                                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800'
                                  : file.status === 'mapped'
                                  ? 'bg-blue-950/60 text-blue-400 border-blue-800'
                                  : 'bg-[#1e293b] text-slate-400 border-[#334155]'
                              }`}
                            >
                              {file.status}
                            </span>
                          </td>

                          <td className="px-4 py-3 text-slate-400 font-mono">
                            {(file.file_size / 1024).toFixed(1)} KB
                          </td>

                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono text-[11px] text-slate-300 bg-[#030712] px-1.5 py-0.5 rounded border border-[#1e293b]">
                                {file.sha256.substring(0, 10)}...{file.sha256.substring(54)}
                              </span>
                              <button
                                onClick={() => copyToClipboard(file.sha256, file.id)}
                                className="text-slate-400 hover:text-white p-1"
                                title="Copy full SHA-256 hash"
                              >
                                {copiedHash === file.id ? (
                                  <span className="text-emerald-400 text-[10px] font-mono">Copied</span>
                                ) : (
                                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                  </svg>
                                )}
                              </button>
                            </div>
                          </td>

                          <td className="px-4 py-3">
                            {ver ? (
                              ver.valid ? (
                                <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800 px-2 py-0.5 rounded">
                                  <span>[OK]</span>
                                  <span>INTACT</span>
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[11px] font-mono text-rose-400 bg-rose-950/40 border border-rose-800 px-2 py-0.5 rounded">
                                  <span>[TAMPERED]</span>
                                  <span>MISMATCH</span>
                                </span>
                              )
                            ) : (
                              <button
                                onClick={() => handleVerify(file.id)}
                                disabled={verifyingId === file.id}
                                className="text-[11px] text-[#38bdf8] hover:underline disabled:opacity-50"
                              >
                                {verifyingId === file.id ? 'Checking...' : 'Verify Hash'}
                              </button>
                            )}
                          </td>

                          <td className="px-4 py-3">
                            {file.status === 'ingested' ? (
                              <button
                                onClick={() => handleViewQuality(file.id)}
                                className="text-[11px] text-emerald-400 hover:underline font-mono"
                              >
                                Quality Metrics
                              </button>
                            ) : (
                              <button
                                onClick={() => handleOpenMapping(file.id)}
                                className="px-2.5 py-1 bg-[#0284c7] hover:bg-[#0369a1] text-white text-[11px] font-semibold rounded transition-colors"
                              >
                                Map & Ingest
                              </button>
                            )}
                          </td>

                          {!isViewer && (
                            <td className="px-4 py-3 text-right">
                              <button
                                onClick={() => handleDelete(file.id, file.original_name)}
                                className="text-slate-500 hover:text-rose-400 text-xs transition-colors"
                                title="Remove File"
                              >
                                Delete
                              </button>
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Investigation Graph (Phase 4) */}
      {activeTab === 'graph' && (
        <GraphCanvas caseId={caseId} isViewer={isViewer} />
      )}

      {/* Tab 3: Money Trail Explorer (Phase 5) */}
      {activeTab === 'money' && (
        <MoneyTrailCanvas caseId={caseId} isViewer={isViewer} />
      )}

      {/* Tab 4: Entity Review & Document NLP (Phase 6) */}
      {activeTab === 'review' && (
        <EntityReview caseId={caseId} isViewer={isViewer} />
      )}

      {/* Tab 5: Master Profiles & Entity Deduplication (Phase 7 - Hero Feature #1) */}
      {activeTab === 'profiles' && (
        <MasterProfiles caseId={caseId} isViewer={isViewer} />
      )}

      {/* Tab 6: Report Generator & Section 63 BSA 2023 Dossier */}
      {activeTab === 'reports' && (
        <ReportGenerator caseId={caseId} isViewer={isViewer} />
      )}

      {/* Tab 7: Lead Advisor (Phase 8 - Hero Feature #3) */}
      {activeTab === 'leads' && (
        <LeadAdvisor caseId={caseId} isViewer={isViewer} />
      )}

      {/* Fallback for unknown tabs */}
      {activeTab !== 'overview' && activeTab !== 'timeline' && activeTab !== 'evidence' && activeTab !== 'graph' && activeTab !== 'money' && activeTab !== 'review' && activeTab !== 'profiles' && activeTab !== 'reports' && activeTab !== 'leads' && (
        <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg p-12 text-center">
          <div className="w-12 h-12 bg-[#030712] border border-[#1e293b] rounded-md flex items-center justify-center mx-auto mb-4 text-[#38bdf8]">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 className="text-sm font-bold text-white capitalize">
            {activeTab.replace('-', ' ')} Module
          </h3>
          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            This module activates in downstream intelligence phases (Phases 7-8). Currently storing {evidenceList.length} verified evidence files in the chain of custody.
          </p>
          <div className="mt-6">
            <button
              onClick={() => setActiveTab('evidence')}
              className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-white text-xs rounded transition-colors"
            >
              Return to Evidence Repository
            </button>
          </div>
        </div>
      )}


      {/* Phase 3 Column Mapping & Ingestion Modal */}
      {mappingModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg max-w-4xl w-full p-6 shadow-2xl my-8">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] mb-4">
              <div>
                <h3 className="text-sm font-bold text-white">
                  Column Mapping & Schema Ingestion Engine
                </h3>
                <p className="text-xs text-slate-400">
                  Confirm canonical field bindings for: <code className="text-[#38bdf8]">{activePreview?.file_name}</code>
                </p>
              </div>
              <button
                onClick={() => setMappingModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs font-mono"
              >
                [CLOSE]
              </button>
            </div>

            {previewLoading ? (
              <div className="py-16 text-center text-xs text-slate-400">
                <div className="inline-block animate-spin w-6 h-6 border-2 border-slate-600 border-t-[#38bdf8] rounded-full mb-2"></div>
                <p>Sniffing header patterns & value distributions...</p>
              </div>
            ) : jobStatus ? (
              /* Live Ingestion Job Running View */
              <div className="py-8">
                <div className="max-w-md mx-auto">
                  <div className="flex items-center justify-between text-xs text-slate-300 mb-2 font-mono">
                    <span className="uppercase font-bold text-[#38bdf8]">Job Status: {jobStatus}</span>
                    <span>{jobProgress}%</span>
                  </div>
                  <div className="w-full bg-[#030712] h-2 rounded-full overflow-hidden mb-6 border border-[#1e293b]">
                    <div
                      className={`h-full transition-all duration-300 ${
                        jobStatus === 'done' ? 'bg-emerald-500' : jobStatus === 'failed' ? 'bg-rose-500' : 'bg-[#0284c7]'
                      }`}
                      style={{ width: `${jobProgress}%` }}
                    />
                  </div>

                  <div className="bg-[#030712] border border-[#1e293b] rounded p-4 space-y-2 text-xs font-mono text-slate-400">
                    {jobSteps.map((s, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-slate-300">
                        <span className="text-[#38bdf8] font-bold">[OK]</span>
                        <span>{s}</span>
                      </div>
                    ))}
                  </div>

                  {jobStatus === 'done' && (
                    <div className="mt-6 text-center">
                      <button
                        onClick={() => {
                          setMappingModalOpen(false);
                          fetchCaseDetails();
                        }}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold"
                      >
                        Ingestion Complete - View Workspace
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* Mapping Review View */
              <div className="space-y-4">
                {/* File Type Selection */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-[#030712] border border-[#1e293b] rounded">
                  <div className="text-xs">
                    <span className="text-slate-400">AI Detected Type: </span>
                    <span className="font-bold text-white uppercase">{activePreview?.detected_type}</span>
                    <span className="text-xs text-[#38bdf8] font-mono ml-2">
                      ({Math.round((activePreview?.confidence || 0) * 100)}% Confidence)
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <label className="text-xs text-slate-400" htmlFor="file-type-override">Override Type:</label>
                    <select
                      id="file-type-override"
                      value={selectedFileType}
                      onChange={(e) => setSelectedFileType(e.target.value)}
                      className="px-2.5 py-1 bg-[#0b1120] border border-[#334155] rounded text-xs text-white"
                    >
                      <option value="cdr">CDR (Call Detail Records)</option>
                      <option value="bank_transactions">Bank Transactions (Multi-Account)</option>
                      <option value="bank_statement">Bank Statement (Single-Account Passbook)</option>
                      <option value="identity_table">Identity Table (SDR / KYC / Person List)</option>
                      <option value="ip_log">IP Logs</option>
                    </select>
                  </div>
                </div>

                {/* Mapping Table */}
                <div className="border border-[#1e293b] rounded overflow-hidden max-h-72 overflow-y-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#030712] text-slate-400 font-mono text-[11px] uppercase border-b border-[#1e293b] sticky top-0">
                      <tr>
                        <th className="px-4 py-2">Source Header</th>
                        <th className="px-4 py-2">Canonical Binding</th>
                        <th className="px-4 py-2">Sample Preview Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1e293b]">
                      {activePreview?.headers.map((h) => {
                        const sampleVal = activePreview.preview_rows[0]?.[h];
                        return (
                          <tr key={h} className="hover:bg-[#030712]/40">
                            <td className="px-4 py-2 font-mono text-slate-200">{h}</td>
                            <td className="px-4 py-2">
                              <select
                                value={activeMapping[h] || 'ignore'}
                                onChange={(e) =>
                                  setActiveMapping((prev) => ({
                                    ...prev,
                                    [h]: e.target.value,
                                  }))
                                }
                                className="px-2 py-1 bg-[#030712] border border-[#334155] rounded text-xs text-[#38bdf8] font-mono"
                              >
                                <option value="ignore">ignore</option>
                                {selectedFileType === 'cdr' && (
                                  <>
                                    <option value="caller">caller</option>
                                    <option value="receiver">receiver</option>
                                    <option value="datetime">datetime</option>
                                    <option value="date">date</option>
                                    <option value="time">time</option>
                                    <option value="duration">duration</option>
                                    <option value="call_type">call_type</option>
                                    <option value="imei">imei</option>
                                  </>
                                )}
                                {selectedFileType === 'bank_transactions' && (
                                  <>
                                    <option value="from_account">from_account</option>
                                    <option value="to_account">to_account</option>
                                    <option value="amount">amount</option>
                                    <option value="datetime">datetime</option>
                                    <option value="date">date</option>
                                    <option value="reference">reference</option>
                                    <option value="from_name">from_name</option>
                                    <option value="to_name">to_name</option>
                                  </>
                                )}
                                {selectedFileType === 'bank_statement' && (
                                  <>
                                    <option value="date">date</option>
                                    <option value="narration">narration</option>
                                    <option value="debit">debit</option>
                                    <option value="credit">credit</option>
                                    <option value="amount">amount</option>
                                    <option value="balance">balance</option>
                                  </>
                                )}
                                {selectedFileType === 'identity_table' && (
                                  <>
                                    <option value="name">name</option>
                                    <option value="phone">phone</option>
                                    <option value="account">account</option>
                                    <option value="vehicle">vehicle</option>
                                    <option value="email">email</option>
                                    <option value="registered_mobile">registered_mobile</option>
                                  </>
                                )}
                                {selectedFileType === 'ip_log' && (
                                  <>
                                    <option value="identifier">identifier</option>
                                    <option value="ip">ip</option>
                                    <option value="datetime">datetime</option>
                                  </>
                                )}
                              </select>
                            </td>
                            <td className="px-4 py-2 font-mono text-slate-400 truncate max-w-xs">
                              {sampleVal !== undefined && sampleVal !== null ? String(sampleVal) : '-'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="pt-3 border-t border-[#1e293b] flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 font-mono">
                    Template will be cached by header signature for automatic future mapping.
                  </span>
                  <button
                    onClick={handleConfirmMappingAndIngest}
                    className="px-5 py-2 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded transition-colors"
                  >
                    Confirm Mapping & Execute Ingestion
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Data Quality Report Modal */}
      {qualityModalOpen && qualityData && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] mb-4">
              <h3 className="text-sm font-bold text-white">Data Quality Summary</h3>
              <button onClick={() => setQualityModalOpen(false)} className="text-slate-400 hover:text-white text-xs font-mono">
                [CLOSE]
              </button>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div className="flex justify-between py-1 border-b border-[#1e293b]">
                <span className="text-slate-400">File Name:</span>
                <span className="text-white font-bold">{qualityData.file_name}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1e293b]">
                <span className="text-slate-400">Schema Type:</span>
                <span className="text-[#38bdf8] uppercase">{qualityData.file_type}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1e293b]">
                <span className="text-slate-400">Staged Records:</span>
                <span className="text-emerald-400 font-bold">{qualityData.staged_rows}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1e293b]">
                <span className="text-slate-400">Rejected Anomaly Rows:</span>
                <span className="text-amber-400 font-bold">{qualityData.rejected_rows}</span>
              </div>
            </div>

            <div className="mt-6 text-right">
              <button
                onClick={() => setQualityModalOpen(false)}
                className="px-4 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-white text-xs rounded"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Case Settings & Dynamic Recompute Modal (Phase 9) */}
      <CaseSettings
        caseId={caseId}
        isOpen={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        onSettingsUpdated={() => {
          fetchCaseDetails();
        }}
      />
    </div>
  );
}
