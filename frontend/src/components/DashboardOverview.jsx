import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ReferenceDot,
} from 'recharts';
import { analyticsApi, casesApi } from '../api/client';

const ENTITY_COLORS = {
  phone: '#38bdf8', // Cyan
  account: '#34d399', // Emerald
  person: '#a855f7', // Purple
  vehicle: '#f59e0b', // Amber
  email: '#ec4899', // Pink
  ip: '#64748b', // Slate
  other: '#94a3b8',
};

const formatIndianCurrency = (rupees) => {
  if (rupees === undefined || rupees === null) return '₹0';
  const val = Number(rupees);
  if (val >= 10000000) {
    return `₹${(val / 10000000).toFixed(2)} Cr`;
  } else if (val >= 100000) {
    return `₹${(val / 100000).toFixed(2)} L`;
  } else if (val >= 1000) {
    return `₹${(val / 1000).toFixed(1)} K`;
  }
  return `₹${val.toLocaleString('en-IN')}`;
};

export default function DashboardOverview({ caseId, isViewer, onNavigateTab }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Data states
  const [overview, setOverview] = useState(null);
  const [callsSeries, setCallsSeries] = useState([]);
  const [txnsSeries, setTxnsSeries] = useState([]);
  const [topEntities, setTopEntities] = useState([]);
  const [heatmap, setHeatmap] = useState([]);
  const [degreeDist, setDegreeDist] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [leads, setLeads] = useState([]);

  // Controls
  const [topMetric, setTopMetric] = useState('degree');
  const [selectedPhone, setSelectedPhone] = useState('');
  const [selectedAccount, setSelectedAccount] = useState('');
  const [dateFilter, setDateFilter] = useState({ from: '', to: '' });

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        overviewRes,
        callsRes,
        txnsRes,
        topEntitiesRes,
        heatmapRes,
        degreeDistRes,
        alertsRes,
        leadsRes,
      ] = await Promise.all([
        analyticsApi.getOverview(caseId, { fromDate: dateFilter.from, toDate: dateFilter.to }),
        analyticsApi.getCallsPerDay(caseId, {
          phone: selectedPhone || undefined,
          fromDate: dateFilter.from,
          toDate: dateFilter.to,
        }),
        analyticsApi.getTxnsPerDay(caseId, {
          account: selectedAccount || undefined,
          fromDate: dateFilter.from,
          toDate: dateFilter.to,
        }),
        analyticsApi.getTopEntities(caseId, { metric: topMetric, limit: 8 }),
        analyticsApi.getCallHeatmap(caseId),
        analyticsApi.getDegreeDistribution(caseId),
        analyticsApi.getAlerts(caseId, { severity: 'high' }),
        analyticsApi.getLeads(caseId, { limit: 4 }),
      ]);

      setOverview(overviewRes);
      setCallsSeries(callsRes.daily_calls || []);
      setTxnsSeries(txnsRes.daily_txns || []);
      setTopEntities(topEntitiesRes.entities || []);
      setHeatmap(heatmapRes.heatmap || []);
      setDegreeDist(degreeDistRes.distribution || []);
      setAlerts(alertsRes.alerts || []);
      setLeads(leadsRes.leads || []);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
      setError(err.response?.data?.detail || 'Failed to load executive dashboard analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchDashboardData();
    }
  }, [caseId, topMetric, selectedPhone, selectedAccount]);

  const handleApplyDateFilter = (e) => {
    e.preventDefault();
    fetchDashboardData();
  };

  const handleResetDateFilter = () => {
    setDateFilter({ from: '', to: '' });
    setSelectedPhone('');
    setSelectedAccount('');
  };

  if (loading && !overview) {
    return (
      <div className="flex flex-col items-center justify-center p-20 space-y-4">
        <div className="w-10 h-10 border-2 border-[#38bdf8] border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs text-slate-400 font-mono tracking-wider">COMPILING EXECUTIVE INTELLIGENCE DOSSIER...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-950/40 border border-rose-800 rounded-lg p-6 text-center my-6">
        <p className="text-sm font-semibold text-rose-300">{error}</p>
        <button
          onClick={fetchDashboardData}
          className="mt-3 px-3 py-1 bg-rose-800 hover:bg-rose-700 text-white text-xs rounded transition-colors"
        >
          Retry Compilation
        </button>
      </div>
    );
  }

  // Prep entity composition donut data
  const entityDonutData = overview?.entity_counts
    ? Object.entries(overview.entity_counts).map(([type, count]) => ({
        name: type.charAt(0).toUpperCase() + type.slice(1),
        value: count,
        color: ENTITY_COLORS[type.toLowerCase()] || ENTITY_COLORS.other,
      }))
    : [];

  const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  return (
    <div className="space-y-6">
      {/* 1. Header Toolbar with Global Filters */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-[#0b1120] border border-[#1e293b] p-4 rounded-lg">
        <div>
          <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Operational Intelligence Dashboard
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Temporal analysis, communication anomalies, financial throughput & network centrality
          </p>
        </div>

        {/* Date & Entity Filter Bar */}
        <form onSubmit={handleApplyDateFilter} className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 bg-[#030712] border border-[#1e293b] rounded px-2.5 py-1">
            <span className="text-[11px] font-mono text-slate-400">FROM</span>
            <input
              type="date"
              value={dateFilter.from}
              onChange={(e) => setDateFilter((prev) => ({ ...prev, from: e.target.value }))}
              className="bg-transparent text-xs text-white outline-none font-mono"
            />
          </div>
          <div className="flex items-center gap-1.5 bg-[#030712] border border-[#1e293b] rounded px-2.5 py-1">
            <span className="text-[11px] font-mono text-slate-400">TO</span>
            <input
              type="date"
              value={dateFilter.to}
              onChange={(e) => setDateFilter((prev) => ({ ...prev, to: e.target.value }))}
              className="bg-transparent text-xs text-white outline-none font-mono"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded transition-colors"
          >
            Apply
          </button>
          {(dateFilter.from || dateFilter.to || selectedPhone || selectedAccount) && (
            <button
              type="button"
              onClick={handleResetDateFilter}
              className="px-2.5 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 text-xs rounded transition-colors"
            >
              Reset
            </button>
          )}
        </form>
      </div>

      {/* 2. Executive Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-[#0b1120] border border-[#1e293b] p-3.5 rounded-lg">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Evidence Files</div>
          <div className="text-xl font-bold text-white mt-1">{overview?.files_count || 0}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            {overview?.rows_ingested?.toLocaleString() || 0} rows staged
          </div>
        </div>

        <div className="bg-[#0b1120] border border-[#1e293b] p-3.5 rounded-lg">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Total Entities</div>
          <div className="text-xl font-bold text-[#38bdf8] mt-1">{overview?.total_entities || 0}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            {overview?.total_edges || 0} graph relations
          </div>
        </div>

        <div className="bg-[#0b1120] border border-[#1e293b] p-3.5 rounded-lg">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Calls Recorded</div>
          <div className="text-xl font-bold text-white mt-1">{overview?.total_calls?.toLocaleString() || 0}</div>
          <div className="text-[10px] text-emerald-400 mt-0.5 font-mono">
            {callsSeries.filter((c) => c.is_spike).length} sudden spikes
          </div>
        </div>

        <div className="bg-[#0b1120] border border-[#1e293b] p-3.5 rounded-lg">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Transactions</div>
          <div className="text-xl font-bold text-white mt-1">{overview?.total_txns?.toLocaleString() || 0}</div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            {txnsSeries.length} active dates
          </div>
        </div>

        <div className="bg-[#0b1120] border border-[#1e293b] p-3.5 rounded-lg">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Money Volume</div>
          <div className="text-xl font-bold text-emerald-400 mt-1">
            {formatIndianCurrency(overview?.total_money_volume_rs || 0)}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
            ₹{((overview?.total_money_volume_paise || 0) / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
        </div>

        <div className="bg-[#0b1120] border border-[#1e293b] p-3.5 rounded-lg">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Temporal Span</div>
          <div className="text-xl font-bold text-amber-400 mt-1">
            {overview?.date_span?.days || 0} <span className="text-xs font-normal text-slate-400">days</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5 font-mono truncate">
            {overview?.date_span?.earliest || 'N/A'} → {overview?.date_span?.latest || 'N/A'}
          </div>
        </div>
      </div>

      {/* 3. Primary Charts Grid: Calls Per Day & Transactions Volume */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Calls Per Day Chart */}
        <div className="bg-[#0b1120] border border-[#1e293b] p-5 rounded-lg flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white">Daily Call Volume & Sudden Spikes</h3>
              <p className="text-xs text-slate-400">
                Median Absolute Deviation (MAD) spike markers highlighted in red
              </p>
            </div>
            {callsSeries.some((c) => c.is_spike) && (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-950/60 border border-rose-800 text-rose-300">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping"></span>
                SPIKE DETECTED
              </span>
            )}
          </div>

          <div className="h-64 w-full">
            {callsSeries.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">
                No call records ingested for this case date window.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={callsSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="callsGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke="#64748b"
                    fontSize={10}
                    tickFormatter={(val) => val.slice(5)}
                  />
                  <YAxis stroke="#64748b" fontSize={10} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#030712',
                      borderColor: '#1e293b',
                      borderRadius: '6px',
                      fontSize: '12px',
                    }}
                    labelStyle={{ color: '#94a3b8', fontFamily: 'monospace' }}
                    formatter={(val, name, props) => {
                      const item = props.payload;
                      if (item.is_spike) {
                        return [`${val} calls [SPIKE ALERT: ${item.spike_info?.explanation || 'Anomalous deviation'}]`, 'Calls'];
                      }
                      return [`${val} calls`, 'Calls'];
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#38bdf8"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#callsGrad)"
                  />
                  {callsSeries
                    .filter((c) => c.is_spike)
                    .map((c, idx) => (
                      <ReferenceDot
                        key={`spike-${idx}`}
                        x={c.date}
                        y={c.count}
                        r={5}
                        fill="#f43f5e"
                        stroke="#fff"
                        strokeWidth={1.5}
                      />
                    ))}
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Transactions Per Day Chart */}
        <div className="bg-[#0b1120] border border-[#1e293b] p-5 rounded-lg flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white">Daily Financial Throughput</h3>
              <p className="text-xs text-slate-400">
                Aggregated transaction volume (INR) across collection & mule routes
              </p>
            </div>
            <span className="text-xs font-mono font-semibold text-emerald-400">
              Peak: {formatIndianCurrency(overview?.total_money_volume_rs ? overview.total_money_volume_rs / Math.max(1, txnsSeries.length) : 0)}/day avg
            </span>
          </div>

          <div className="h-64 w-full">
            {txnsSeries.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">
                No financial transactions staged for this case date window.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={txnsSeries} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke="#64748b"
                    fontSize={10}
                    tickFormatter={(val) => val.slice(5)}
                  />
                  <YAxis
                    stroke="#64748b"
                    fontSize={10}
                    tickFormatter={(val) => {
                      if (val >= 10000000) return `${(val / 10000000).toFixed(1)}Cr`;
                      if (val >= 100000) return `${(val / 100000).toFixed(0)}L`;
                      if (val >= 1000) return `${(val / 1000).toFixed(0)}k`;
                      return val;
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#030712',
                      borderColor: '#1e293b',
                      borderRadius: '6px',
                      fontSize: '12px',
                    }}
                    labelStyle={{ color: '#94a3b8', fontFamily: 'monospace' }}
                    formatter={(val) => [formatIndianCurrency(val), 'Volume']}
                  />
                  <Bar dataKey="volume_inr" fill="#34d399" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* 4. Top Entities Ranking & Entity Composition Donut */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Entities Bar Chart (2 Cols) */}
        <div className="lg:col-span-2 bg-[#0b1120] border border-[#1e293b] p-5 rounded-lg flex flex-col">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
            <div>
              <h3 className="text-sm font-bold text-white">Top Central Entities</h3>
              <p className="text-xs text-slate-400">Ranked by topological influence and throughput</p>
            </div>

            {/* Metric Switcher */}
            <div className="flex items-center gap-1 bg-[#030712] border border-[#1e293b] p-0.5 rounded">
              {[
                { id: 'degree', label: 'Degree Centrality' },
                { id: 'calls', label: 'Call Volume' },
                { id: 'throughput', label: 'Financial Vol' },
              ].map((m) => (
                <button
                  key={m.id}
                  onClick={() => setTopMetric(m.id)}
                  className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                    topMetric === m.id
                      ? 'bg-[#0284c7] text-white font-semibold'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          <div className="h-64 w-full">
            {topEntities.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">
                No entities available for ranking.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={topEntities}
                  layout="vertical"
                  margin={{ top: 5, right: 20, left: 40, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                  <XAxis
                    type="number"
                    stroke="#64748b"
                    fontSize={10}
                    tickFormatter={(val) =>
                      topMetric === 'throughput' ? formatIndianCurrency(val) : val
                    }
                  />
                  <YAxis
                    dataKey="display_name"
                    type="category"
                    stroke="#64748b"
                    fontSize={10}
                    width={110}
                    tickFormatter={(val) => (val && val.length > 14 ? `${val.slice(0, 12)}..` : val)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#030712',
                      borderColor: '#1e293b',
                      borderRadius: '6px',
                      fontSize: '12px',
                    }}
                    labelStyle={{ color: '#fff', fontWeight: 'bold' }}
                    formatter={(val, name, props) => {
                      const ent = props.payload;
                      if (topMetric === 'throughput') {
                        return [formatIndianCurrency(val), 'Financial Volume'];
                      }
                      if (topMetric === 'calls') {
                        return [`${val} calls`, 'Total Calls'];
                      }
                      return [`${val} links`, 'Direct Connections'];
                    }}
                  />
                  <Bar
                    dataKey={
                      topMetric === 'throughput'
                        ? 'financial_volume_rs'
                        : topMetric === 'calls'
                        ? 'calls_count'
                        : 'degree'
                    }
                    fill="#38bdf8"
                    radius={[0, 4, 4, 0]}
                  >
                    {topEntities.map((ent, idx) => (
                      <Cell
                        key={`cell-${idx}`}
                        fill={ENTITY_COLORS[ent.label?.toLowerCase()] || '#38bdf8'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Entity Breakdown Donut (1 Col) */}
        <div className="bg-[#0b1120] border border-[#1e293b] p-5 rounded-lg flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white">Entity Network Composition</h3>
            <p className="text-xs text-slate-400">Distribution by forensic identifier class</p>
          </div>

          <div className="h-52 w-full my-auto">
            {entityDonutData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">
                No entities staged.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={entityDonutData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={75}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {entityDonutData.map((entry, index) => (
                      <Cell key={`donut-${index}`} fill={entry.color} stroke="#0b1120" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#030712',
                      borderColor: '#1e293b',
                      borderRadius: '6px',
                      fontSize: '12px',
                    }}
                    formatter={(val) => [`${val} entities`, 'Count']}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="grid grid-cols-2 gap-1.5 pt-3 border-t border-[#1e293b]">
            {entityDonutData.map((d, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[11px]">
                <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: d.color }}></span>
                <span className="text-slate-400 truncate">{d.name}:</span>
                <span className="text-white font-mono font-semibold ml-auto">{d.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 5. 24x7 Call Activity Heatmap Grid */}
      <div className="bg-[#0b1120] border border-[#1e293b] p-5 rounded-lg">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-white">Weekly Communication Heatmap (Day × Hour)</h3>
            <p className="text-xs text-slate-400">
              Identifies off-hours, late-night coordination and temporal operational cadence
            </p>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
            <span>Low</span>
            <span className="w-3 h-3 bg-[#1e293b] rounded"></span>
            <span className="w-3 h-3 bg-[#0369a1] rounded"></span>
            <span className="w-3 h-3 bg-[#0284c7] rounded"></span>
            <span className="w-3 h-3 bg-[#38bdf8] rounded"></span>
            <span>High Intensity</span>
          </div>
        </div>

        {/* Heatmap Grid */}
        <div className="overflow-x-auto">
          <div className="min-w-[680px]">
            {/* Hours Header (0-23) */}
            <div className="grid grid-cols-[50px_repeat(24,_1fr)] gap-1 mb-1 text-[10px] font-mono text-slate-500 text-center">
              <div></div>
              {Array.from({ length: 24 }).map((_, h) => (
                <div key={h}>{h}</div>
              ))}
            </div>

            {/* Weekday Rows */}
            {daysOfWeek.map((dayName, dayIdx) => {
              const dayCells = heatmap.filter((cell) => cell.weekday === dayIdx);
              const maxVal = Math.max(...heatmap.map((c) => c.count || 0), 1);

              return (
                <div
                  key={dayName}
                  className="grid grid-cols-[50px_repeat(24,_1fr)] gap-1 mb-1 items-center"
                >
                  <div className="text-[11px] font-mono text-slate-400 font-semibold">{dayName}</div>
                  {Array.from({ length: 24 }).map((_, h) => {
                    const match = dayCells.find((c) => c.hour === h);
                    const cnt = match?.count || 0;
                    const ratio = cnt / maxVal;

                    let bgClass = 'bg-[#111827] text-transparent';
                    if (cnt > 0) {
                      if (ratio > 0.75) bgClass = 'bg-[#38bdf8] text-[#030712] font-bold';
                      else if (ratio > 0.4) bgClass = 'bg-[#0284c7] text-white';
                      else if (ratio > 0.15) bgClass = 'bg-[#0369a1] text-white';
                      else bgClass = 'bg-[#1e293b] text-slate-400';
                    }

                    return (
                      <div
                        key={h}
                        title={`${dayName} ${h}:00 - ${h}:59: ${cnt} calls`}
                        className={`h-6 rounded text-[9px] flex items-center justify-center font-mono cursor-default transition-transform hover:scale-110 ${bgClass}`}
                      >
                        {cnt > 0 ? cnt : ''}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 6. Intelligence Alerts & Priority Leads Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Latest Active High-Priority Alerts */}
        <div className="bg-[#0b1120] border border-[#1e293b] p-5 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                Urgent Intelligence Alerts ({alerts.length})
              </h3>
              <button
                onClick={() => onNavigateTab && onNavigateTab('leads')}
                className="text-xs text-[#38bdf8] hover:underline font-medium"
              >
                Inspect Leads →
              </button>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Algorithmic pattern detections triggering statutory review thresholds
            </p>

            <div className="space-y-2.5">
              {alerts.length === 0 ? (
                <div className="text-xs text-slate-500 font-mono text-center py-6">
                  No high-severity anomaly alerts currently active for this case.
                </div>
              ) : (
                alerts.slice(0, 4).map((al) => (
                  <div
                    key={al.id}
                    className="p-3 bg-[#030712] border border-rose-950/60 rounded flex items-start gap-3"
                  >
                    <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase rounded bg-rose-950 text-rose-300 border border-rose-800 shrink-0">
                      {al.pattern_type.replace('_', ' ')}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="text-xs font-semibold text-white truncate">{al.entity_id}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">
                        {al.explanation}
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500 shrink-0">
                      {al.alert_date}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Top Investigative Leads */}
        <div className="bg-[#0b1120] border border-[#1e293b] p-5 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#38bdf8]"></span>
                Top Priority Leads ({leads.length})
              </h3>
              <button
                onClick={() => onNavigateTab && onNavigateTab('leads')}
                className="text-xs text-[#38bdf8] hover:underline font-medium"
              >
                View Advisor →
              </button>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Data-driven multi-source lead ranking normalized across available evidentiary sources
            </p>

            <div className="space-y-2.5">
              {leads.length === 0 ? (
                <div className="text-xs text-slate-500 font-mono text-center py-6">
                  No prioritized investigative leads computed yet.
                </div>
              ) : (
                leads.slice(0, 4).map((ld) => (
                  <div
                    key={ld.entity_id}
                    className="p-3 bg-[#030712] border border-[#1e293b] rounded flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-white truncate">{ld.display_name}</span>
                        <span
                          className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded border font-semibold ${
                            ld.level === 'HIGH'
                              ? 'bg-rose-950/60 text-rose-300 border-rose-800'
                              : 'bg-amber-950/60 text-amber-300 border-amber-800'
                          }`}
                        >
                          {ld.level}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1 line-clamp-1">
                        {ld.narrative}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-sm font-bold text-[#38bdf8] font-mono">{ld.priority}</div>
                      <div className="text-[9px] text-slate-500 font-mono">Lead Score</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
