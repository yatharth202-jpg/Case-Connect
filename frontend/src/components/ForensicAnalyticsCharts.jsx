import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, Legend
} from 'recharts';

export default function ForensicAnalyticsCharts({ charts = {}, metrics = {} }) {
  const hourlyData = charts.hourly_activity || [];
  const entityData = charts.entity_distribution || [];
  const financialData = charts.financial_flow || [];
  const centralityData = charts.centrality_ranking || [];

  return (
    <div className="space-y-6 select-none animate-fadeIn">
      {/* Section Header */}
      <div className="flex items-center justify-between border-b border-[#16243d] pb-3">
        <div className="flex items-center gap-2.5">
          <span className="text-xl">📊</span>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Temporal Dynamics & Syndicate Flow Analytics
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              Chronological 24-hour operational bursts, financial throughput, and entity threat composition
            </p>
          </div>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800">
          Recharts AI Synthesis
        </span>
      </div>

      {/* Row 1: 24-Hour Activity Spline Curve & Entity Threat Composition */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: 24-Hour Hourly Activity Spline Area Curve (7 cols) */}
        <div className="lg:col-span-7 bg-[#080d1d] border border-[#192742] rounded-2xl p-5 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
                <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                  24-Hour Operational Activity Curve (Hourly Spline)
                </h4>
              </div>
              <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800">
                🌙 Nocturnal Burst: 23:00 - 04:00 AM
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono mb-4">
              Hourly frequency of telecommunication calls and financial movements across the 24-hour spectrum.
            </p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={hourlyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="callsGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="txnsGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="hour"
                  stroke="#475569"
                  tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
                  interval={2}
                />
                <YAxis
                  stroke="#475569"
                  tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-[#050914] border border-[#1e2f52] p-2.5 rounded-xl shadow-xl text-xs font-mono">
                          <div className="text-white font-bold mb-1 flex items-center justify-between gap-3">
                            <span>Time Window: {label}</span>
                            {data.is_nocturnal && (
                              <span className="text-[9px] text-rose-400 font-bold bg-rose-950/80 px-1 rounded">
                                NOCTURNAL
                              </span>
                            )}
                          </div>
                          <div className="text-cyan-400">Calls Ingested: {data.calls}</div>
                          <div className="text-rose-400">Transactions: {data.transactions}</div>
                          <div className="text-slate-400 text-[10px] mt-0.5">
                            Total Synchronized Events: {data.total_events}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="calls"
                  stroke="#06b6d4"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#callsGrad)"
                  name="Phone Calls"
                />
                <Area
                  type="monotone"
                  dataKey="transactions"
                  stroke="#f43f5e"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#txnsGrad)"
                  name="Transactions"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 pt-3 border-t border-[#142038] flex items-center justify-between text-[10px] font-mono text-slate-400">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-cyan-400 inline-block" /> Call Record Volume
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-rose-500 inline-block" /> Financial Transfers
              </span>
            </div>
            <span className="text-slate-500">Peak Anomaly: 02:00 - 04:00 AM Intercepts</span>
          </div>
        </div>

        {/* Right: Entity Threat Composition (Donut Pie Chart) (5 cols) */}
        <div className="lg:col-span-5 bg-[#080d1d] border border-[#192742] rounded-2xl p-5 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                  Entity Threat Distribution (Pie/Donut)
                </h4>
              </div>
              <span className="text-[10px] font-mono text-cyan-300">
                {metrics.total_entities || 0} Total Nodes
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono mb-2">
              Composition of correlated physical, telecommunication, and banking vectors.
            </p>
          </div>

          <div className="h-56 w-full flex items-center justify-center">
            {entityData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={entityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
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
                          <div className="bg-[#050914] border border-[#1e2f52] p-2 rounded-lg text-xs font-mono text-white">
                            <span className="font-bold" style={{ color: d.color }}>{d.name}:</span> {d.value} Entities
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-xs font-mono text-slate-500">No entity distribution available</div>
            )}
          </div>

          {/* Custom Legend Badges */}
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#142038] text-[10px] font-mono">
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
      </div>

      {/* Row 2: Financial Fund Velocity & Top Node Centrality Ranking */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Financial Ingestion Volume per Channel (6 cols) */}
        <div className="lg:col-span-6 bg-[#080d1d] border border-[#192742] rounded-2xl p-5 shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
              <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Top Financial Transaction Streams (Bar Chart)
              </h4>
            </div>
            <span className="text-xs font-mono text-emerald-400 font-bold">
              {metrics.money_volume_formatted || '₹0'} Ingested
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-mono mb-4">
            Highest-value funds routed through suspect and mule account channels.
          </p>

          <div className="h-56 w-full">
            {financialData.length > 0 ? (
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
                    tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
                    tickFormatter={(val) => `₹${val >= 100000 ? `${(val / 100000).toFixed(1)}L` : val}`}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="bg-[#050914] border border-[#1e2f52] p-2.5 rounded-xl shadow-xl text-xs font-mono">
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
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-xs font-mono text-slate-500 bg-[#060a17] rounded-xl border border-[#142038]">
                <span>No direct monetary transfer amounts detected in uploaded narrative.</span>
                <span className="text-[10px] text-slate-600 mt-1">Upload Bank Statement CSV to visualize flow.</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Network Centrality & Operational Influence (6 cols) */}
        <div className="lg:col-span-6 bg-[#080d1d] border border-[#192742] rounded-2xl p-5 shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
              <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Top Operational Nodes by Network Degree (Centrality)
              </h4>
            </div>
            <span className="text-xs font-mono text-cyan-400 font-bold">
              {metrics.total_links || 0} Total Edges
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-mono mb-4">
            Entities exhibiting the highest number of direct cross-domain operational connections.
          </p>

          <div className="h-56 w-full">
            {centralityData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={centralityData}
                  layout="vertical"
                  margin={{ top: 5, right: 20, left: 40, bottom: 5 }}
                >
                  <XAxis
                    type="number"
                    stroke="#475569"
                    tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
                  />
                  <YAxis
                    dataKey="name"
                    type="category"
                    stroke="#475569"
                    tick={{ fill: '#cbd5e1', fontSize: 10, fontFamily: 'monospace' }}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="bg-[#050914] border border-[#1e2f52] p-2 rounded-lg text-xs font-mono text-white">
                            <span className="font-bold text-cyan-400">{d.name}</span> ({d.type}): {d.degree} Linkages
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="degree" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs font-mono text-slate-500">
                Awaiting entity correlation topology...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
