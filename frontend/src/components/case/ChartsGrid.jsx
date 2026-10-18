import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { Activity, BarChart2, PieChart as PieIcon, Clock, TrendingUp, Grid, Shield } from 'lucide-react';

export const ChartsGrid = ({ chartsData }) => {
  // 1. Calls per day (MAD burst detection)
  const callsPerDay = chartsData?.calls_per_day || [
    { date: '10-Oct', calls: 14 },
    { date: '11-Oct', calls: 22 },
    { date: '12-Oct', calls: 18 },
    { date: '13-Oct', calls: 31 },
    { date: '14-Oct', calls: 86, spike: true }, // Spike marker
    { date: '15-Oct', calls: 42 },
    { date: '16-Oct', calls: 24 },
  ];

  // 2. Transactions per day (Layering volume)
  const txnsPerDay = chartsData?.txns_per_day || [
    { date: '10-Oct', amount: 8.5 },
    { date: '11-Oct', amount: 14.0 },
    { date: '12-Oct', amount: 9.2 },
    { date: '13-Oct', amount: 22.0 },
    { date: '14-Oct', amount: 56.5 },
    { date: '15-Oct', amount: 48.0 },
    { date: '16-Oct', amount: 26.3 },
  ];

  // 3. Evidence vector distribution
  const vectorSplit = chartsData?.vector_distribution || [
    { name: 'CDR Telecom', value: 58, color: '#3FB6A8' },
    { name: 'Bank Layering', value: 28, color: '#F2A33A' },
    { name: 'IP / SIM-Box', value: 14, color: '#E5484D' },
  ];

  // 4. Centrality Influence Rank
  const centralityRanks = chartsData?.centrality || [
    { entity: 'Node-01 (Focal)', score: 94 },
    { entity: 'Node-03 (Courier)', score: 78 },
    { entity: 'Node-04 (Mule A/C)', score: 71 },
    { entity: 'Node-06 (Holder)', score: 58 },
    { entity: 'Node-05 (Gateway)', score: 44 },
  ];

  // Custom Dark Tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="glass-sm p-2.5 rounded-lg border border-white/10 text-xs font-mono shadow-xl">
          <p className="text-text font-semibold">{label}</p>
          <p className="text-accent">{payload[0].name || 'Value'}: {payload[0].value}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <section id="forensics" className="w-full py-16 px-4 sm:px-6 max-w-6xl mx-auto relative z-10">
      {/* Header */}
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass-sm text-[11px] font-mono text-accent mb-2">
          <Activity className="w-3 h-3 text-accent" />
          <span>SECTION 04 · QUANTITATIVE FORENSIC METRICS</span>
        </div>
        <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-text tracking-tight">
          Corroborated analytical metrics.
        </h2>
        <p className="text-xs sm:text-sm text-muted font-normal mt-1.5 max-w-xl">
          Algorithmic anomaly detection across temporal call frequency, fund velocity, and topological centrality.
        </p>
      </div>

      {/* Grid of 6 Glass Panels */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* Panel 1: Calls Per Day Line Chart */}
        <div className="glass p-5 rounded-2xl border border-white/10 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono text-muted uppercase tracking-wider flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-data" />
                <span>Call Volume Frequency</span>
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-alert/15 text-alert border border-alert/30">
                Oct-14 Spike (86)
              </span>
            </div>
            <p className="font-serif text-xl text-text mb-4">
              Peak Traffic Spike
            </p>
          </div>

          <div className="w-full h-44">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={callsPerDay} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <XAxis dataKey="date" stroke="#8B93A1" fontSize={9} tickLine={false} />
                <YAxis stroke="#8B93A1" fontSize={9} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="calls"
                  stroke="#3FB6A8"
                  strokeWidth={2.5}
                  dot={{ fill: '#3FB6A8', r: 3 }}
                  activeDot={{ r: 6, fill: '#F2A33A' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Panel 2: Daily Transaction Volume Bar Chart */}
        <div className="glass p-5 rounded-2xl border border-white/10 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono text-muted uppercase tracking-wider flex items-center gap-1.5">
                <BarChart2 className="w-3.5 h-3.5 text-accent" />
                <span>Layering Histogram</span>
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent/15 text-accent border border-accent/30">
                ₹ Lakhs / Day
              </span>
            </div>
            <p className="font-serif text-xl text-text mb-4">
              Fund Movement Velocity
            </p>
          </div>

          <div className="w-full h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={txnsPerDay} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <XAxis dataKey="date" stroke="#8B93A1" fontSize={9} tickLine={false} />
                <YAxis stroke="#8B93A1" fontSize={9} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="amount" fill="#F2A33A" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Panel 3: Evidence Type Donut Chart */}
        <div className="glass p-5 rounded-2xl border border-white/10 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono text-muted uppercase tracking-wider flex items-center gap-1.5">
                <PieIcon className="w-3.5 h-3.5 text-data" />
                <span>Vector Split</span>
              </span>
              <span className="text-[10px] font-mono text-muted">
                3 Artifact Sources
              </span>
            </div>
            <p className="font-serif text-xl text-text mb-2">
              Cross-Evidence Weights
            </p>
          </div>

          <div className="w-full h-36 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={vectorSplit}
                  cx="50%"
                  cy="50%"
                  innerRadius={36}
                  outerRadius={56}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {vectorSplit.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="flex items-center justify-around text-[10px] font-mono text-muted pt-2 border-t border-white/5">
            {vectorSplit.map((v, i) => (
              <span key={i} className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: v.color }} />
                <span>{v.name.split(' ')[0]} {v.value}%</span>
              </span>
            ))}
          </div>
        </div>

        {/* Panel 4: Curfew Night Surge Heatmap */}
        <div className="glass p-5 rounded-2xl border border-white/10 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono text-muted uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-alert" />
                <span>Temporal Heatmap</span>
              </span>
              <span className="text-[10px] font-mono text-alert">
                01:00 - 04:00 Surge
              </span>
            </div>
            <p className="font-serif text-xl text-text mb-3">
              Midnight Activity Concentration
            </p>
          </div>

          {/* Mini 7x4 Heat Grid */}
          <div className="grid grid-cols-7 gap-1.5 py-2">
            {[
              2, 1, 0, 8, 9, 2, 0,
              1, 0, 1, 7, 8, 3, 1,
              0, 2, 0, 9, 10, 4, 0,
              1, 1, 2, 6, 9, 2, 1,
            ].map((density, idx) => {
              const bg = density > 7 ? 'bg-alert/80' : density > 4 ? 'bg-accent/60' : density > 1 ? 'bg-data/40' : 'bg-white/[0.04]';
              return (
                <div
                  key={idx}
                  className={`h-5 rounded-md ${bg} transition-colors hover:scale-105`}
                  title={`Hour Window Density: ${density}`}
                />
              );
            })}
          </div>

          <div className="flex items-center justify-between text-[10px] font-mono text-muted pt-2 border-t border-white/5">
            <span>Day: 08:00 - 20:00 (Muted)</span>
            <span className="text-alert">Night: 01:00 - 04:00 (Peak)</span>
          </div>
        </div>

        {/* Panel 5: Centrality Influence Ranking */}
        <div className="glass p-5 rounded-2xl border border-white/10 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono text-muted uppercase tracking-wider flex items-center gap-1.5">
                <Grid className="w-3.5 h-3.5 text-accent" />
                <span>Network Centrality</span>
              </span>
              <span className="text-[10px] font-mono text-accent">
                Eigenvector / Degree
              </span>
            </div>
            <p className="font-serif text-xl text-text mb-3">
              Topological Key Nodes
            </p>
          </div>

          <div className="space-y-2 py-1">
            {centralityRanks.map((item, idx) => (
              <div key={idx} className="space-y-1">
                <div className="flex justify-between text-[11px] font-mono">
                  <span className="text-text truncate max-w-[170px]">{item.entity}</span>
                  <span className="text-accent font-semibold">{item.score}</span>
                </div>
                <div className="w-full bg-white/[0.05] h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-accent h-full rounded-full"
                    style={{ width: `${item.score}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="text-[10px] font-mono text-muted pt-2 border-t border-white/5">
            Normalized against 51 nodes across telecom/bank topology
          </div>
        </div>

        {/* Panel 6: Sub-Clusters Louvain Modularity */}
        <div className="glass p-5 rounded-2xl border border-white/10 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono text-muted uppercase tracking-wider flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-data" />
                <span>Syndicate Partition</span>
              </span>
              <span className="text-[10px] font-mono text-data">
                Modularity Q = 0.64
              </span>
            </div>
            <p className="font-serif text-xl text-text mb-3">
              Louvain Modularity Clusters
            </p>
          </div>

          <div className="space-y-2.5 py-1">
            <div className="glass-sm p-2.5 rounded-xl border border-alert/20 flex items-center justify-between text-xs font-mono">
              <span className="text-alert font-bold">Cluster α · Orchestration</span>
              <span className="text-muted">4 Nodes</span>
            </div>
            <div className="glass-sm p-2.5 rounded-xl border border-accent/20 flex items-center justify-between text-xs font-mono">
              <span className="text-accent font-bold">Cluster β · Gujarat Layering</span>
              <span className="text-muted">7 Accounts</span>
            </div>
            <div className="glass-sm p-2.5 rounded-xl border border-data/20 flex items-center justify-between text-xs font-mono">
              <span className="text-data font-bold">Cluster γ · Noida SIM-Box</span>
              <span className="text-muted">11 SIMs</span>
            </div>
          </div>

          <div className="text-[10px] font-mono text-muted pt-2 border-t border-white/5">
            Zero community bridging leakage outside attributed syndicate
          </div>
        </div>
      </div>
    </section>
  );
};

export default ChartsGrid;
