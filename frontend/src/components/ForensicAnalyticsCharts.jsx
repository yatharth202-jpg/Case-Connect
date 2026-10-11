import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar
} from 'recharts';

export default function ForensicAnalyticsCharts({ charts = {}, metrics = {} }) {
  const hourlyData = charts.hourly_activity || [];
  const entityData = charts.entity_distribution || [];
  const financialData = charts.financial_flow || [];
  const centralityData = charts.centrality_ranking || [];

  // Conditional flags: only show charts if meaningful data exists, avoid blank boxes per user requirement
  const hasHourlyData = hourlyData.length > 0 && hourlyData.some(d => (d.calls || 0) > 0 || (d.transactions || 0) > 0);
  const hasFinancialData = financialData.length > 0 && financialData.some(d => (d.amount || 0) > 0);
  const hasEntityData = entityData.length > 0;
  const hasCentralityData = centralityData.length > 0;

  // If literally no chart data exists, omit section cleanly
  if (!hasHourlyData && !hasFinancialData && !hasEntityData && !hasCentralityData) {
    return null;
  }

  return (
    <div className="space-y-5 select-none animate-fadeIn">
      {/* Section Header */}
      <div className="flex items-center justify-between border-b border-[#182640] pb-2.5">
        <div className="flex items-center gap-2.5">
          <span className="text-lg">📊</span>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
              Temporal Dynamics & Syndicate Flow Analytics
            </h3>
            <p className="text-[10px] text-slate-400 font-mono">
              Dynamic multi-evidence telemetry — automatically rendered when relevant data is ingested
            </p>
          </div>
        </div>
        <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-blue-950/80 text-cyan-300 border border-blue-500/40">
          Live Forensic Synthesis
        </span>
      </div>

      {/* Row 1: Charts that are active */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* 24-Hour Activity Spline Curve (Only rendered if hourly telecom/transaction calls exist) */}
        {hasHourlyData && (
          <div className={`${hasEntityData ? 'lg:col-span-7' : 'lg:col-span-12'} bg-cardBg/90 border border-cyan-500/30 rounded-2xl p-4 shadow-xl flex flex-col justify-between backdrop-blur-md`}>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                    24-Hour Operational Activity (Hourly Spline)
                  </h4>
                </div>
                <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800">
                  🌙 Nocturnal Burst: 23:00 - 04:00 AM
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono mb-3">
                Telemetry timestamps of telecommunication calls and financial movements across the 24-hour spectrum.
              </p>
            </div>

            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={hourlyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="callsGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00F0FF" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#00F0FF" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="txnsGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="hour"
                    stroke="#475569"
                    tick={{ fill: '#94a3b8', fontSize: 9, fontFamily: 'monospace' }}
                    interval={2}
                  />
                  <YAxis
                    stroke="#475569"
                    tick={{ fill: '#94a3b8', fontSize: 9, fontFamily: 'monospace' }}
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="bg-[#050914] border border-cyan-500/40 p-2.5 rounded-xl shadow-xl text-xs font-mono">
                            <div className="text-white font-bold mb-1 flex items-center justify-between gap-3">
                              <span>Window: {label}</span>
                              {data.is_nocturnal && (
                                <span className="text-[9px] text-rose-400 font-bold bg-rose-950/80 px-1 rounded">
                                  NOCTURNAL
                                </span>
                              )}
                            </div>
                            <div className="text-cyan-400">Calls Ingested: {data.calls}</div>
                            <div className="text-rose-400">Transactions: {data.transactions}</div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="calls"
                    stroke="#00F0FF"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#callsGrad)"
                    name="Phone Calls"
                  />
                  <Area
                    type="monotone"
                    dataKey="transactions"
                    stroke="#f43f5e"
                    strokeWidth={1.5}
                    fillOpacity={1}
                    fill="url(#txnsGrad)"
                    name="Transactions"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Entity Threat Composition (Donut Pie Chart) */}
        {hasEntityData && (
          <div className={`${hasHourlyData ? 'lg:col-span-5' : 'lg:col-span-12'} bg-cardBg/90 border border-emerald-500/30 rounded-2xl p-4 shadow-xl flex flex-col justify-between backdrop-blur-md`}>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                    Entity Threat Distribution (Pie/Donut)
                  </h4>
                </div>
                <span className="text-[10px] font-mono text-cyan-300 font-bold">
                  {metrics.total_entities || 0} Total Nodes
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono mb-2">
                Composition of correlated physical suspects, telecom numbers & financial vectors.
              </p>
            </div>

            <div className="h-52 w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={entityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {entityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} stroke="#080d1d" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="bg-[#050914] border border-emerald-500/40 p-2 rounded-lg text-xs font-mono text-white">
                            <span className="font-bold" style={{ color: d.color }}>{d.name}:</span> {d.value} Entities
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Custom Legend Badges */}
            <div className="grid grid-cols-2 gap-1.5 pt-2 border-t border-[#142038] text-[10px] font-mono">
              {entityData.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between px-2 py-1 rounded bg-[#060a17] border border-[#142038]">
                  <div className="flex items-center gap-1.5 truncate">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                    <span className="text-slate-300 truncate">{item.name}</span>
                  </div>
                  <span className="font-bold text-white shrink-0">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Row 2: Financial Streams (Omitted if 0 money data) & Centrality */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Financial Channels Bar Chart (Only rendered if financial transactions exist!) */}
        {hasFinancialData && (
          <div className={`${hasCentralityData ? 'lg:col-span-6' : 'lg:col-span-12'} bg-cardBg/90 border border-emerald-500/30 rounded-2xl p-4 shadow-xl backdrop-blur-md`}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                  Financial Transaction Streams
                </h4>
              </div>
              <span className="text-xs font-mono text-emerald-400 font-bold">
                {metrics.money_volume_formatted || '₹0'} Ingested
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono mb-3">
              Routed funds through identified accounts and flagged intermediary channels.
            </p>

            <div className="h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={financialData} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                  <XAxis
                    dataKey="channel"
                    stroke="#475569"
                    tick={{ fill: '#94a3b8', fontSize: 9, fontFamily: 'monospace' }}
                    angle={-15}
                    textAnchor="end"
                  />
                  <YAxis
                    stroke="#475569"
                    tick={{ fill: '#94a3b8', fontSize: 9, fontFamily: 'monospace' }}
                    tickFormatter={(val) => `₹${val >= 100000 ? `${(val / 100000).toFixed(1)}L` : val}`}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="bg-[#050914] border border-emerald-500/40 p-2.5 rounded-xl shadow-xl text-xs font-mono">
                            <div className="text-white font-bold">{d.channel}</div>
                            <div className="text-emerald-400 font-bold mt-1">Transferred: {d.formatted}</div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="amount" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Centrality Degree Ranking (Rendered if nodes have linkages) */}
        {hasCentralityData && (
          <div className={`${hasFinancialData ? 'lg:col-span-6' : 'lg:col-span-12'} bg-cardBg/90 border border-violet-500/30 rounded-2xl p-4 shadow-xl backdrop-blur-md`}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-violet-400" />
                <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                  Network Degree Centrality (Key Influencers)
                </h4>
              </div>
              <span className="text-xs font-mono text-cyan-400 font-bold">
                {metrics.total_links || 0} Total Edges
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono mb-3">
              Entities with highest multi-hop operational linkages across cases and intercepts.
            </p>

            <div className="h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={centralityData}
                  layout="vertical"
                  margin={{ top: 5, right: 20, left: 30, bottom: 5 }}
                >
                  <XAxis
                    type="number"
                    stroke="#475569"
                    tick={{ fill: '#94a3b8', fontSize: 9, fontFamily: 'monospace' }}
                  />
                  <YAxis
                    dataKey="name"
                    type="category"
                    stroke="#475569"
                    tick={{ fill: '#cbd5e1', fontSize: 9, fontFamily: 'monospace' }}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="bg-[#050914] border border-violet-500/40 p-2 rounded-lg text-xs font-mono text-white">
                            <span className="font-bold text-cyan-400">{d.name}</span> ({d.type}): {d.degree} Connections
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="degree" fill="#8B5CF6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
