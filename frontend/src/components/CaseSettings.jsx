import React, { useState, useEffect } from 'react';
import { casesApi } from '../api/client';

export default function CaseSettings({ caseId, isViewer, onClose, onSettingsUpdated }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [recomputing, setRecomputing] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Settings form state
  const [activeSection, setActiveSection] = useState('comm');
  const [settings, setSettings] = useState({
    communication: {
      spike: { mad_multiplier: 3.0, baseline_window_days: 14, min_history_days: 5, min_call_floor: 5 },
      frequent_pair: { iqr_multiplier: 1.5 },
      new_connection: { window_days: 7, min_early_calls: 5 },
      bridge: { min_betweenness_ratio: 0.1 },
    },
    money: {
      fan_in: { min_sources: 3, window_days: 7 },
      fan_out: { min_destinations: 3, window_days: 7 },
      rapid_pass_through: { inflow_percent: 80.0, max_hours: 48 },
      splitting: { reporting_limit_rupees: 0, min_transfers: 3, window_days: 3, threshold_ratio: 0.9 },
    },
    matching: {
      thresholds: {
        surname_similarity_min: 0.9,
        first_name_similarity_min: 0.85,
        high_level_min: 70,
        medium_level_min: 40,
      },
      strengths: {
        same_account: 95,
        same_phone: 90,
        same_vehicle: 90,
        same_email: 85,
        same_device_imei: 70,
        dob_plus_similar_name: 60,
        same_address: 35,
        similar_name_only: 25,
        same_ip: 20,
      },
    },
    lead_advisor: {
      weights: {
        money_flow: 30,
        bridge: 25,
        unusual_communication: 20,
        timing: 15,
        multi_document: 10,
      },
      levels: {
        high_priority_min: 70,
        medium_priority_min: 40,
      },
    },
  });

  const fetchSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await casesApi.getSettings(caseId);
      if (data && Object.keys(data).length > 0) {
        setSettings((prev) => ({
          communication: { ...prev.communication, ...(data.communication || {}) },
          money: { ...prev.money, ...(data.money || {}) },
          matching: { ...prev.matching, ...(data.matching || {}) },
          lead_advisor: { ...prev.lead_advisor, ...(data.lead_advisor || {}) },
        }));
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
      setError(err.response?.data?.detail || 'Failed to load case settings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchSettings();
    }
  }, [caseId]);

  const handleChange = (section, subsection, key, value) => {
    const num = Number(value);
    const parsedVal = isNaN(num) ? value : num;
    setSettings((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [subsection]: {
          ...prev[section][subsection],
          [key]: parsedVal,
        },
      },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await casesApi.updateSettings(caseId, settings);
      setSuccessMsg('Case settings updated and audited successfully.');
      if (onSettingsUpdated) onSettingsUpdated();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const handleRecompute = async () => {
    setRecomputing(true);
    setError(null);
    setSuccessMsg(null);
    try {
      // First save settings
      await casesApi.updateSettings(caseId, settings);
      // Then recompute
      const res = await casesApi.recomputeAnalytics(caseId);
      setSuccessMsg(`Analytics recomputed successfully: ${res.alerts_count} alerts and ${res.leads_count} leads refreshed.`);
      if (onSettingsUpdated) onSettingsUpdated();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to recompute analytics.');
    } finally {
      setRecomputing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg max-w-3xl w-full p-6 shadow-2xl my-8">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] mb-4">
          <div>
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">
              Case Parameter Engine
            </span>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>⚙️</span> Case Algorithmic Settings & Thresholds
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-xs font-mono"
          >
            ✕ CLOSE
          </button>
        </div>

        {error && (
          <div className="bg-rose-950/40 border border-rose-800 text-rose-300 p-3 rounded text-xs mb-4">
            {error}
          </div>
        )}

        {successMsg && (
          <div className="bg-emerald-950/40 border border-emerald-800 text-emerald-300 p-3 rounded text-xs mb-4 flex items-center gap-2">
            <span>✓</span> {successMsg}
          </div>
        )}

        {/* Section Tabs */}
        <div className="flex items-center gap-1 border-b border-[#1e293b] pb-3 mb-5 overflow-x-auto">
          {[
            { id: 'comm', label: '1. Communication Spikes & Pairs' },
            { id: 'money', label: '2. Money Laundering & Mules' },
            { id: 'matching', label: '3. Entity Deduplication' },
            { id: 'leads', label: '4. Lead Advisor Weights' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveSection(tab.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors whitespace-nowrap ${
                activeSection === tab.id
                  ? 'bg-[#0284c7] text-white font-semibold'
                  : 'text-slate-400 hover:text-white hover:bg-[#1e293b]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Section 1: Communication */}
        {activeSection === 'comm' && (
          <div className="space-y-4">
            <div className="bg-[#030712] p-4 rounded border border-[#1e293b]">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
                Sudden Spike Detection (Self-Baseline Median + MAD)
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    MAD Multiplier (k factor in median + k * 1.4826 * MAD):
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    disabled={isViewer}
                    value={settings.communication.spike.mad_multiplier}
                    onChange={(e) => handleChange('communication', 'spike', 'mad_multiplier', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 3.0 (Gaussian 99.7% equivalent)</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Baseline Window (Days):
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.communication.spike.baseline_window_days}
                    onChange={(e) => handleChange('communication', 'spike', 'baseline_window_days', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 14 days historical baseline</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Min Call Daily Floor (Minimum calls before trigger):
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.communication.spike.min_call_floor}
                    onChange={(e) => handleChange('communication', 'spike', 'min_call_floor', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 5 calls/day minimum</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Min History Days Required:
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.communication.spike.min_history_days}
                    onChange={(e) => handleChange('communication', 'spike', 'min_history_days', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 5 days prior observation</span>
                </div>
              </div>
            </div>

            <div className="bg-[#030712] p-4 rounded border border-[#1e293b]">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
                Frequent Pair & Bridge Anomalies
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Frequent Pair IQR Multiplier (Q3 + k * IQR):
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    disabled={isViewer}
                    value={settings.communication.frequent_pair.iqr_multiplier}
                    onChange={(e) => handleChange('communication', 'frequent_pair', 'iqr_multiplier', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 1.5</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Min Betweenness Centrality Ratio (Bridge Broker):
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    disabled={isViewer}
                    value={settings.communication.bridge.min_betweenness_ratio}
                    onChange={(e) => handleChange('communication', 'bridge', 'min_betweenness_ratio', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 0.10</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Section 2: Money Laundering */}
        {activeSection === 'money' && (
          <div className="space-y-4">
            <div className="bg-[#030712] p-4 rounded border border-[#1e293b]">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
                Mule Account Funnels (Fan-In & Fan-Out)
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Fan-In Min Distinct Sources:
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.money.fan_in.min_sources}
                    onChange={(e) => handleChange('money', 'fan_in', 'min_sources', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 3 distinct remitter accounts</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Fan-In Time Window (Days):
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.money.fan_in.window_days}
                    onChange={(e) => handleChange('money', 'fan_in', 'window_days', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 7 days</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Fan-Out Min Distinct Destinations:
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.money.fan_out.min_destinations}
                    onChange={(e) => handleChange('money', 'fan_out', 'min_destinations', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 3 distinct beneficiary accounts</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Fan-Out Time Window (Days):
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.money.fan_out.window_days}
                    onChange={(e) => handleChange('money', 'fan_out', 'window_days', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 7 days</span>
                </div>
              </div>
            </div>

            <div className="bg-[#030712] p-4 rounded border border-[#1e293b]">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
                Rapid Pass-Through Velocity & Smurfing
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Pass-Through Outflow Threshold (% of inflow):
                  </label>
                  <input
                    type="number"
                    step="1"
                    disabled={isViewer}
                    value={settings.money.rapid_pass_through.inflow_percent}
                    onChange={(e) => handleChange('money', 'rapid_pass_through', 'inflow_percent', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 80% drained immediately</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Pass-Through Time Window (Hours):
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.money.rapid_pass_through.max_hours}
                    onChange={(e) => handleChange('money', 'rapid_pass_through', 'max_hours', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 48 hours</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Section 3: Entity Matching */}
        {activeSection === 'matching' && (
          <div className="space-y-4">
            <div className="bg-[#030712] p-4 rounded border border-[#1e293b]">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
                RapidFuzz Jaro-Winkler Similarity Thresholds
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Min Surname Similarity (Soundex Blocking):
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    disabled={isViewer}
                    value={settings.matching.thresholds.surname_similarity_min}
                    onChange={(e) => handleChange('matching', 'thresholds', 'surname_similarity_min', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 0.90 (90% Jaro-Winkler)</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Min First Name Similarity:
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    disabled={isViewer}
                    value={settings.matching.thresholds.first_name_similarity_min}
                    onChange={(e) => handleChange('matching', 'thresholds', 'first_name_similarity_min', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs focus:border-[#38bdf8] outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 0.85 (85% Jaro-Winkler)</span>
                </div>
              </div>
            </div>

            <div className="bg-[#030712] p-4 rounded border border-[#1e293b]">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
                Identifier Strengths (Weight Contribution)
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="text-slate-400 block text-[10px]">Same Bank Account</label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.matching.strengths.same_account}
                    onChange={(e) => handleChange('matching', 'strengths', 'same_account', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-1.5 text-white font-mono text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block text-[10px]">Same Mobile Phone</label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.matching.strengths.same_phone}
                    onChange={(e) => handleChange('matching', 'strengths', 'same_phone', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-1.5 text-white font-mono text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block text-[10px]">Same Vehicle Reg</label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.matching.strengths.same_vehicle}
                    onChange={(e) => handleChange('matching', 'strengths', 'same_vehicle', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-1.5 text-white font-mono text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block text-[10px]">Same Device IMEI</label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.matching.strengths.same_device_imei}
                    onChange={(e) => handleChange('matching', 'strengths', 'same_device_imei', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-1.5 text-white font-mono text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block text-[10px]">Same Email Address</label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.matching.strengths.same_email}
                    onChange={(e) => handleChange('matching', 'strengths', 'same_email', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-1.5 text-white font-mono text-xs outline-none"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block text-[10px]">Shared IP Address</label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.matching.strengths.same_ip}
                    onChange={(e) => handleChange('matching', 'strengths', 'same_ip', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-1.5 text-white font-mono text-xs outline-none"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Section 4: Lead Advisor Weights */}
        {activeSection === 'leads' && (
          <div className="space-y-4">
            <div className="bg-[#030712] p-4 rounded border border-[#1e293b]">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">
                Lead Advisor Signal Weights (Normalized Priority 0-100)
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Money Flow Throughput Weight:
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.lead_advisor.weights.money_flow}
                    onChange={(e) => handleChange('lead_advisor', 'weights', 'money_flow', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 30</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Bridge Centrality Broker Weight:
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.lead_advisor.weights.bridge}
                    onChange={(e) => handleChange('lead_advisor', 'weights', 'bridge', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 25</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Unusual Communication Spike Weight:
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.lead_advisor.weights.unusual_communication}
                    onChange={(e) => handleChange('lead_advisor', 'weights', 'unusual_communication', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 20</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Pre-FIR Timing Coordination Weight:
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.lead_advisor.weights.timing}
                    onChange={(e) => handleChange('lead_advisor', 'weights', 'timing', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 15</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    Multi-Document Cross-FIR Presence:
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.lead_advisor.weights.multi_document}
                    onChange={(e) => handleChange('lead_advisor', 'weights', 'multi_document', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 10</span>
                </div>

                <div>
                  <label className="text-slate-400 block text-[11px] mb-1">
                    High Priority Level Minimum Score:
                  </label>
                  <input
                    type="number"
                    disabled={isViewer}
                    value={settings.lead_advisor.levels.high_priority_min}
                    onChange={(e) => handleChange('lead_advisor', 'levels', 'high_priority_min', e.target.value)}
                    className="w-full bg-[#0b1120] border border-[#1e293b] rounded p-2 text-white font-mono text-xs outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">Default: 70/100 threshold</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-[#1e293b] mt-6">
          <button
            type="button"
            disabled={isViewer || loading}
            onClick={fetchSettings}
            className="text-xs text-slate-400 hover:text-white transition-colors"
          >
            ↺ Reset to Global Defaults
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={isViewer || saving || recomputing}
              onClick={handleSave}
              className="px-4 py-2 bg-[#1e293b] hover:bg-[#334155] text-white text-xs font-semibold rounded transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Overrides'}
            </button>

            <button
              type="button"
              disabled={isViewer || recomputing || saving}
              onClick={handleRecompute}
              className="px-4 py-2 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-lg shadow-cyan-950/40"
            >
              {recomputing ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  Recomputing Analytics...
                </>
              ) : (
                <>
                  <span>⚡</span> Recompute Analytics
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
