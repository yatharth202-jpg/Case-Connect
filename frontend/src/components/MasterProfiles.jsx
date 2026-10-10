import React, { useState, useEffect } from 'react';
import { matchesApi } from '../api/client';

export default function MasterProfiles({ caseId, isViewer }) {
  const [activeSubTab, setActiveSubTab] = useState('queue'); // 'queue' | 'dossier' | 'shared' | 'possible'
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');
  const [successToast, setSuccessToast] = useState('');

  // Data states
  const [matches, setMatches] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [crossCaseAlerts, setCrossCaseAlerts] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState(null);
  const [profileDetail, setProfileDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Confirmation modal
  const [confirmModal, setConfirmModal] = useState(null); // { action: 'approve'|'undo'|'reject', matchId, title, message }

  const fetchData = async () => {
    setLoading(true);
    try {
      const [matchesRes, profilesRes, alertsRes] = await Promise.all([
        matchesApi.listMatches(caseId, { limit: 100 }),
        matchesApi.listProfiles(caseId),
        matchesApi.getCrossCaseAlerts(caseId).catch(() => []),
      ]);
      setMatches(matchesRes.items || []);
      setProfiles(profilesRes || []);
      setCrossCaseAlerts(alertsRes || []);
      setError('');

      if (profilesRes && profilesRes.length > 0 && !selectedProfileId) {
        setSelectedProfileId(profilesRes[0].profile_id);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load entity matching data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchData();
    }
  }, [caseId]);

  useEffect(() => {
    if (selectedProfileId) {
      loadProfileDetail(selectedProfileId);
    }
  }, [selectedProfileId]);

  const loadProfileDetail = async (profId) => {
    setDetailLoading(true);
    try {
      const detail = await matchesApi.getProfileDetail(caseId, profId);
      setProfileDetail(detail);
    } catch (err) {
      console.error(err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleScanMatches = async () => {
    setScanning(true);
    setError('');
    try {
      const res = await matchesApi.generateMatches(caseId);
      setSuccessToast(`Matching scan complete: ${res.new_suggestions} new suggestions evaluated.`);
      setTimeout(() => setSuccessToast(''), 3500);
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Scan failed');
    } finally {
      setScanning(false);
    }
  };

  const handleApprove = async (matchId) => {
    try {
      await matchesApi.approveMatch(matchId);
      setConfirmModal(null);
      setSuccessToast('Match approved. Consolidated Master Profile created.');
      setTimeout(() => setSuccessToast(''), 3000);
      await fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Approval failed');
    }
  };

  const handleReject = async (matchId) => {
    try {
      await matchesApi.rejectMatch(matchId);
      setConfirmModal(null);
      setSuccessToast('Match rejected.');
      setTimeout(() => setSuccessToast(''), 3000);
      await fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Rejection failed');
    }
  };

  const handleUndo = async (matchId) => {
    try {
      await matchesApi.undoMatch(matchId);
      setConfirmModal(null);
      setSuccessToast('Merge undone. Original entity structure restored.');
      setTimeout(() => setSuccessToast(''), 3000);
      await fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Undo failed');
    }
  };

  // Filter queues
  const highMediumMatches = matches.filter(
    (m) => (m.level === 'HIGH' || m.level === 'MEDIUM') && (m.status === 'pending' || m.status === 'approved')
  );
  const sharedDeviceFlags = matches.filter((m) => m.level === 'SHARED_DEVICE');
  const possibleLowMatches = matches.filter((m) => m.level === 'LOW');

  const formatPaise = (paise) => {
    if (!paise) return '₹0.00';
    const rupees = paise / 100.0;
    if (rupees >= 10000000) return `₹${(rupees / 10000000).toFixed(2)} Cr`;
    if (rupees >= 100000) return `₹${(rupees / 100000).toFixed(2)} L`;
    return `₹${rupees.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  if (loading) {
    return (
      <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg p-16 text-center">
        <div className="inline-block animate-spin w-6 h-6 border-2 border-slate-600 border-t-[#38bdf8] rounded-full mb-3"></div>
        <p className="text-xs text-slate-400 font-mono">Running entity identity resolution engine...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Toast Alert */}
      {successToast && (
        <div className="p-3 bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs rounded-md flex items-center justify-between font-mono animate-fadeIn">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            {successToast}
          </span>
          <button onClick={() => setSuccessToast('')} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Cross-Case Alert Banner */}
      {crossCaseAlerts.length > 0 && (
        <div className="bg-amber-950/40 border border-amber-800 rounded-lg p-4">
          <div className="flex items-center gap-2 text-amber-300 text-xs font-bold uppercase tracking-wider mb-2 font-mono">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping"></span>
            <span>Cross-Case Intelligence Link ({crossCaseAlerts.length} matches across cases)</span>
          </div>
          <div className="space-y-1.5">
            {crossCaseAlerts.map((a, idx) => (
              <div key={idx} className="text-xs text-slate-300 font-mono flex items-center gap-2">
                <span className="px-1.5 py-0.5 rounded bg-amber-950 border border-amber-800 text-amber-400 text-[10px]">
                  {a.type}
                </span>
                <span>{a.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Container Card */}
      <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg p-6">
        {/* Top Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-[#1e293b]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-mono text-[#38bdf8] bg-[#030712] px-2 py-0.5 rounded border border-[#1e293b]">
                PHASE 7 | HERO FEATURE #1
              </span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800">
                Non-Destructive Resolution
              </span>
            </div>
            <h2 className="text-base font-bold text-white tracking-tight">
              Entity Deduplication & Cross-FIR Master Profiles
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Identifies name variants and shared identifiers across FIRs and registries. AI suggests; the investigating officer decides.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {!isViewer && (
              <button
                onClick={handleScanMatches}
                disabled={scanning}
                className="px-3.5 py-2 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {scanning && <div className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin"></div>}
                <span>{scanning ? 'Scanning...' : 'Re-Scan Case Matches'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Sub-Tabs Navigation */}
        <div className="flex items-center gap-2 border-b border-[#1e293b] py-3 overflow-x-auto text-xs font-medium">
          <button
            onClick={() => setActiveSubTab('queue')}
            className={`px-3 py-1.5 rounded transition-colors flex items-center gap-2 ${
              activeSubTab === 'queue'
                ? 'bg-[#1e293b] text-white font-semibold border border-slate-700'
                : 'text-slate-400 hover:text-white hover:bg-[#131d33]'
            }`}
          >
            <span>Matches Review Queue</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-[#030712] text-[#38bdf8] border border-[#1e293b]">
              {highMediumMatches.length}
            </span>
          </button>

          <button
            onClick={() => setActiveSubTab('dossier')}
            className={`px-3 py-1.5 rounded transition-colors flex items-center gap-2 ${
              activeSubTab === 'dossier'
                ? 'bg-[#1e293b] text-white font-semibold border border-slate-700'
                : 'text-slate-400 hover:text-white hover:bg-[#131d33]'
            }`}
          >
            <span>Master Profiles Dossier</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-[#030712] text-emerald-400 border border-[#1e293b]">
              {profiles.length}
            </span>
          </button>

          <button
            onClick={() => setActiveSubTab('shared')}
            className={`px-3 py-1.5 rounded transition-colors flex items-center gap-2 ${
              activeSubTab === 'shared'
                ? 'bg-[#1e293b] text-amber-300 font-semibold border border-amber-900/60'
                : 'text-slate-400 hover:text-white hover:bg-[#131d33]'
            }`}
          >
            <span>Shared Device Warnings</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-950 text-amber-400 border border-amber-800">
              {sharedDeviceFlags.length}
            </span>
          </button>

          <button
            onClick={() => setActiveSubTab('possible')}
            className={`px-3 py-1.5 rounded transition-colors flex items-center gap-2 ${
              activeSubTab === 'possible'
                ? 'bg-[#1e293b] text-white font-semibold border border-slate-700'
                : 'text-slate-400 hover:text-white hover:bg-[#131d33]'
            }`}
          >
            <span>Possible Matches (Low)</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-[#030712] text-slate-400 border border-[#1e293b]">
              {possibleLowMatches.length}
            </span>
          </button>
        </div>

        {/* Tab 1: Matches Review Queue */}
        {activeSubTab === 'queue' && (
          <div className="pt-6 space-y-4">
            {highMediumMatches.length === 0 ? (
              <div className="p-12 text-center text-slate-400 font-mono text-xs border border-dashed border-[#1e293b] rounded-lg">
                <p>No pending High or Medium match suggestions in this case.</p>
                <p className="mt-1 text-slate-500">
                  Click 'Re-Scan Case Matches' to detect name variants across newly uploaded files.
                </p>
              </div>
            ) : (
              highMediumMatches.map((item) => (
                <div
                  key={item.id}
                  className={`border rounded-lg p-5 transition-all ${
                    item.status === 'approved'
                      ? 'bg-emerald-950/20 border-emerald-900/60'
                      : 'bg-[#030712] border-[#1e293b] hover:border-slate-700'
                  }`}
                >
                  <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 mb-4 pb-4 border-b border-[#1e293b]">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
                          item.level === 'HIGH'
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                            : 'bg-blue-950 text-blue-300 border-blue-800'
                        }`}
                      >
                        {item.level} CONFIDENCE ({item.score.toFixed(0)}%)
                      </span>
                      <span className="text-[10px] font-mono text-slate-400 bg-[#0b1120] px-2 py-0.5 rounded border border-[#1e293b]">
                        Status: <strong className="uppercase text-slate-200">{item.status}</strong>
                      </span>
                    </div>

                    {/* Officer Actions */}
                    {!isViewer && (
                      <div className="flex items-center gap-2">
                        {item.status === 'pending' ? (
                          <>
                            <button
                              onClick={() =>
                                setConfirmModal({
                                  action: 'approve',
                                  matchId: item.id,
                                  title: 'Approve Entity Merge',
                                  message: `Merge "${item.entity_a.name}" and "${item.entity_b.name}" into a unified Master Profile? Original records remain intact.`,
                                })
                              }
                              className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded transition-colors"
                            >
                              Approve Merge
                            </button>
                            <button
                              onClick={() =>
                                setConfirmModal({
                                  action: 'reject',
                                  matchId: item.id,
                                  title: 'Reject Match Suggestion',
                                  message: 'Mark this match as rejected? These entities will remain separate.',
                                })
                              }
                              className="px-3 py-1 bg-[#1e293b] hover:bg-[#334155] text-slate-300 text-xs font-medium rounded transition-colors"
                            >
                              Reject
                            </button>
                          </>
                        ) : item.status === 'approved' ? (
                          <button
                            onClick={() =>
                              setConfirmModal({
                                action: 'undo',
                                matchId: item.id,
                                title: 'Undo Master Profile Merge',
                                message: 'Undo this merge? The Master Profile will be unlinked and the original entity view graph restored.',
                              })
                            }
                            className="px-3 py-1 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 text-xs font-medium rounded transition-colors"
                          >
                            Undo Merge
                          </button>
                        ) : null}
                      </div>
                    )}
                  </div>

                  {/* Side-by-Side Comparison */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Entity A */}
                    <div className="bg-[#0b1120] border border-[#1e293b] rounded p-4">
                      <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">
                        Record A • Source: {item.entity_a.source_file} ({item.entity_a.source_ref})
                      </div>
                      <div className="text-sm font-bold text-white mb-2">{item.entity_a.name}</div>
                      <div className="space-y-1.5 text-xs text-slate-300 font-mono">
                        {item.entity_a.phones.length > 0 && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-slate-500 text-[10px]">PHONE:</span>
                            <span className="text-[#38bdf8] bg-[#030712] px-1.5 py-0.5 rounded border border-[#1e293b]">
                              {item.entity_a.phones.join(', ')}
                            </span>
                          </div>
                        )}
                        {item.entity_a.accounts.length > 0 && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-slate-500 text-[10px]">A/C:</span>
                            <span className="text-amber-300 bg-[#030712] px-1.5 py-0.5 rounded border border-[#1e293b]">
                              {item.entity_a.accounts.join(', ')}
                            </span>
                          </div>
                        )}
                        {item.entity_a.vehicles.length > 0 && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-slate-500 text-[10px]">VEHICLE:</span>
                            <span className="text-purple-300 bg-[#030712] px-1.5 py-0.5 rounded border border-[#1e293b]">
                              {item.entity_a.vehicles.join(', ')}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Entity B */}
                    <div className="bg-[#0b1120] border border-[#1e293b] rounded p-4">
                      <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">
                        Record B • Source: {item.entity_b.source_file} ({item.entity_b.source_ref})
                      </div>
                      <div className="text-sm font-bold text-white mb-2">{item.entity_b.name}</div>
                      <div className="space-y-1.5 text-xs text-slate-300 font-mono">
                        {item.entity_b.phones.length > 0 && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-slate-500 text-[10px]">PHONE:</span>
                            <span className="text-[#38bdf8] bg-[#030712] px-1.5 py-0.5 rounded border border-[#1e293b]">
                              {item.entity_b.phones.join(', ')}
                            </span>
                          </div>
                        )}
                        {item.entity_b.accounts.length > 0 && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-slate-500 text-[10px]">A/C:</span>
                            <span className="text-amber-300 bg-[#030712] px-1.5 py-0.5 rounded border border-[#1e293b]">
                              {item.entity_b.accounts.join(', ')}
                            </span>
                          </div>
                        )}
                        {item.entity_b.vehicles.length > 0 && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-slate-500 text-[10px]">VEHICLE:</span>
                            <span className="text-purple-300 bg-[#030712] px-1.5 py-0.5 rounded border border-[#1e293b]">
                              {item.entity_b.vehicles.join(', ')}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Reasons & Mathematical Evidence */}
                  <div className="mt-3 pt-3 border-t border-[#1e293b]/60">
                    <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1.5">
                      Algorithmic Provenance & Match Rationale:
                    </div>
                    <ul className="space-y-1 text-xs text-slate-300">
                      {item.reasons.map((r, r_idx) => (
                        <li key={r_idx} className="flex items-center gap-2">
                          <span className="text-emerald-400 text-xs">✓</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 2: Master Profiles Dossier */}
        {activeSubTab === 'dossier' && (
          <div className="pt-6">
            {profiles.length === 0 ? (
              <div className="p-12 text-center text-slate-400 font-mono text-xs border border-dashed border-[#1e293b] rounded-lg">
                <p>No consolidated Master Profiles created yet.</p>
                <p className="mt-1 text-slate-500">
                  Approve high-confidence matches in the review queue to build unified person dossiers.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Profile List Selector */}
                <div className="space-y-2">
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono mb-2">
                    Active Master Profiles ({profiles.length})
                  </div>
                  {profiles.map((p) => (
                    <button
                      key={p.profile_id}
                      onClick={() => setSelectedProfileId(p.profile_id)}
                      className={`w-full text-left p-3 rounded-lg border transition-all ${
                        selectedProfileId === p.profile_id
                          ? 'bg-[#1e293b] border-[#0284c7] text-white'
                          : 'bg-[#030712] border-[#1e293b] text-slate-300 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mb-1">
                        <span>{p.profile_id}</span>
                        <span className="text-emerald-400">{p.member_count} records merged</span>
                      </div>
                      <div className="text-xs font-bold text-white">{p.display_name}</div>
                      <div className="text-[11px] text-slate-400 mt-1 truncate">
                        Aliases: {p.also_known_as.join(', ')}
                      </div>
                    </button>
                  ))}
                </div>

                {/* Dossier Detail View */}
                <div className="lg:col-span-2">
                  {detailLoading ? (
                    <div className="p-12 text-center text-slate-400 font-mono text-xs bg-[#030712] border border-[#1e293b] rounded-lg">
                      <div className="inline-block animate-spin w-5 h-5 border-2 border-slate-600 border-t-[#38bdf8] rounded-full mb-2"></div>
                      <p>Compiling forensic dossier...</p>
                    </div>
                  ) : profileDetail ? (
                    <div className="bg-[#030712] border border-[#1e293b] rounded-lg p-6 space-y-6">
                      {/* Dossier Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1e293b]">
                        <div>
                          <div className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800 inline-block mb-1">
                            CONSOLIDATED PROFILE: {profileDetail.profile_id}
                          </div>
                          <h3 className="text-lg font-bold text-white">{profileDetail.display_name}</h3>
                          <div className="flex flex-wrap items-center gap-1.5 mt-2">
                            <span className="text-[10px] font-mono text-slate-500">ALSO KNOWN AS:</span>
                            {profileDetail.also_known_as.map((alias, a_idx) => (
                              <span
                                key={a_idx}
                                className="text-xs text-slate-200 bg-[#0b1120] border border-[#1e293b] px-2 py-0.5 rounded font-mono"
                              >
                                {alias}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Top Stats */}
                        <div className="grid grid-cols-2 gap-2 text-right">
                          <div className="bg-[#0b1120] p-2 rounded border border-[#1e293b]">
                            <div className="text-[10px] font-mono text-slate-400">TOTAL CALLS</div>
                            <div className="text-xs font-bold text-white">{profileDetail.stats?.total_calls || 0}</div>
                          </div>
                          <div className="bg-[#0b1120] p-2 rounded border border-[#1e293b]">
                            <div className="text-[10px] font-mono text-slate-400">TXN VOLUME</div>
                            <div className="text-xs font-bold text-emerald-400">
                              {formatPaise(profileDetail.stats?.total_volume_paise)}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Merged Member Records */}
                      <div>
                        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono mb-2">
                          1. Resolved Member Records ({profileDetail.members?.length || 0})
                        </h4>
                        <div className="space-y-1.5">
                          {profileDetail.members?.map((m, m_idx) => (
                            <div
                              key={m_idx}
                              className="bg-[#0b1120] border border-[#1e293b] p-2.5 rounded text-xs flex items-center justify-between font-mono"
                            >
                              <span className="text-white font-semibold">{m.name}</span>
                              <span className="text-slate-400 text-[11px]">
                                Source: {m.source_file} ({m.source_ref})
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Linked Phones */}
                      <div>
                        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono mb-2">
                          2. Linked Mobile Numbers ({profileDetail.phones?.length || 0})
                        </h4>
                        {profileDetail.phones?.length === 0 ? (
                          <p className="text-xs text-slate-500 font-mono">No phones directly linked.</p>
                        ) : (
                          <div className="flex flex-wrap gap-2">
                            {profileDetail.phones.map((p, p_idx) => (
                              <div
                                key={p_idx}
                                className="bg-[#0b1120] border border-[#1e293b] px-3 py-1.5 rounded text-xs font-mono flex items-center gap-2"
                              >
                                <span className="text-[#38bdf8] font-bold">{p.number}</span>
                                <span className="text-[10px] text-slate-500">
                                  ({p.provenance?.source_file})
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Linked Bank Accounts */}
                      <div>
                        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono mb-2">
                          3. Linked Bank Accounts ({profileDetail.accounts?.length || 0})
                        </h4>
                        {profileDetail.accounts?.length === 0 ? (
                          <p className="text-xs text-slate-500 font-mono">No bank accounts directly linked.</p>
                        ) : (
                          <div className="flex flex-wrap gap-2">
                            {profileDetail.accounts.map((acc, a_idx) => (
                              <div
                                key={a_idx}
                                className="bg-[#0b1120] border border-[#1e293b] px-3 py-1.5 rounded text-xs font-mono flex items-center gap-2"
                              >
                                <span className="text-amber-400 font-bold">{acc.account}</span>
                                <span className="text-[10px] text-slate-500">
                                  ({acc.provenance?.source_file})
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Linked Vehicles & FIRs */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono mb-2">
                            4. Vehicles ({profileDetail.vehicles?.length || 0})
                          </h4>
                          {profileDetail.vehicles?.length === 0 ? (
                            <p className="text-xs text-slate-500 font-mono">None</p>
                          ) : (
                            <div className="space-y-1">
                              {profileDetail.vehicles.map((v, v_idx) => (
                                <div
                                  key={v_idx}
                                  className="bg-[#0b1120] border border-[#1e293b] p-2 rounded text-xs font-mono text-purple-300 font-semibold"
                                >
                                  {v.vehicle}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        <div>
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono mb-2">
                            5. Document Mentions ({profileDetail.firs?.length || 0})
                          </h4>
                          {profileDetail.firs?.length === 0 ? (
                            <p className="text-xs text-slate-500 font-mono">None</p>
                          ) : (
                            <div className="space-y-1">
                              {profileDetail.firs.map((f, f_idx) => (
                                <div
                                  key={f_idx}
                                  className="bg-[#0b1120] border border-[#1e293b] p-2 rounded text-xs font-mono text-slate-200"
                                >
                                  {f.fir_id} ({f.provenance?.source_ref})
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Shared Device Warnings */}
        {activeSubTab === 'shared' && (
          <div className="pt-6 space-y-4">
            <div className="p-4 bg-amber-950/30 border border-amber-900 rounded-lg text-xs text-amber-200 leading-relaxed font-mono">
              <strong>Rule 5 & Phase 7 Safeguard:</strong> When two records share a phone or account but have completely distinct, incompatible names (such as family members sharing a phone, or multiple users of a public kiosk), automatic or human merge is strictly prohibited to prevent misattribution.
            </div>

            {sharedDeviceFlags.length === 0 ? (
              <div className="p-12 text-center text-slate-400 font-mono text-xs border border-dashed border-[#1e293b] rounded-lg">
                No shared device or family conflicts detected in this case.
              </div>
            ) : (
              sharedDeviceFlags.map((item) => (
                <div
                  key={item.id}
                  className="bg-[#030712] border border-amber-900/60 rounded-lg p-5"
                >
                  <div className="flex items-center justify-between mb-3 pb-3 border-b border-[#1e293b]">
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 uppercase">
                      SHARED DEVICE / RELATIVE FLAG • MERGE PROHIBITED
                    </span>
                    <span className="text-xs font-mono text-slate-400">Score: {item.score}</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                    <div className="bg-[#0b1120] p-3 rounded border border-[#1e293b]">
                      <div className="text-[10px] font-mono text-slate-500">ENTITY A</div>
                      <div className="text-xs font-bold text-white mt-1">{item.entity_a.name}</div>
                      <div className="text-[11px] text-[#38bdf8] font-mono mt-1">
                        {item.entity_a.phones.join(', ')}
                      </div>
                    </div>
                    <div className="bg-[#0b1120] p-3 rounded border border-[#1e293b]">
                      <div className="text-[10px] font-mono text-slate-500">ENTITY B</div>
                      <div className="text-xs font-bold text-white mt-1">{item.entity_b.name}</div>
                      <div className="text-[11px] text-[#38bdf8] font-mono mt-1">
                        {item.entity_b.phones.join(', ')}
                      </div>
                    </div>
                  </div>

                  <div className="text-xs text-amber-300 font-mono">
                    {item.reasons.map((r, idx) => (
                      <div key={idx}>⚠ {r}</div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 4: Possible Matches (Low) */}
        {activeSubTab === 'possible' && (
          <div className="pt-6 space-y-3">
            <p className="text-xs text-slate-400 font-mono">
              Low-confidence similarity based purely on similar names without any corroborating identifiers. Listed for audit only; merge buttons are disabled per Rule 5.
            </p>
            {possibleLowMatches.length === 0 ? (
              <div className="p-12 text-center text-slate-400 font-mono text-xs border border-dashed border-[#1e293b] rounded-lg">
                No low-confidence name-only suggestions found.
              </div>
            ) : (
              possibleLowMatches.map((item) => (
                <div
                  key={item.id}
                  className="bg-[#030712] border border-[#1e293b] p-3 rounded text-xs flex items-center justify-between font-mono"
                >
                  <div>
                    <span className="text-white font-semibold">{item.entity_a.name}</span>
                    <span className="text-slate-500 mx-2">vs</span>
                    <span className="text-white font-semibold">{item.entity_b.name}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-400 text-[10px]">
                    LOW CONFIDENCE ({item.score}%)
                  </span>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {confirmModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-2">
              {confirmModal.title}
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed mb-6 font-mono">
              {confirmModal.message}
            </p>

            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setConfirmModal(null)}
                className="px-3.5 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 text-xs rounded transition-colors font-mono"
              >
                Cancel
              </button>

              {confirmModal.action === 'approve' && (
                <button
                  onClick={() => handleApprove(confirmModal.matchId)}
                  className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded transition-colors"
                >
                  Confirm Approval
                </button>
              )}
              {confirmModal.action === 'reject' && (
                <button
                  onClick={() => handleReject(confirmModal.matchId)}
                  className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded transition-colors"
                >
                  Confirm Rejection
                </button>
              )}
              {confirmModal.action === 'undo' && (
                <button
                  onClick={() => handleUndo(confirmModal.matchId)}
                  className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded transition-colors"
                >
                  Confirm Undo
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
