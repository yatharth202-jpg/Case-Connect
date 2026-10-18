import React, { useState, useEffect } from 'react';
import { Network, Phone, AlertCircle, ArrowRight, Shield, Layers, TrendingUp } from 'lucide-react';

export const MoneyCallArcs = ({ flowData }) => {
  const [filterMode, setFilterMode] = useState('all'); // 'all' | 'money' | 'calls'
  const [countVolume, setCountVolume] = useState(0);

  const totalVolume = flowData?.total_volume || 18450000;
  const totalCalls = flowData?.total_calls || 1842;
  const totalMules = flowData?.mule_accounts_count || 7;

  // Animated count-up simulation on view
  useEffect(() => {
    let start = 0;
    const end = totalVolume;
    const duration = 1200;
    const stepTime = 30;
    const steps = duration / stepTime;
    const increment = end / steps;

    const timer = setInterval(() => {
      start += increment;
      if (start >= end) {
        setCountVolume(end);
        clearInterval(timer);
      } else {
        setCountVolume(Math.floor(start));
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, [totalVolume]);

  const arcs = [
    {
      id: 1,
      from: 'Mumbai (MH)',
      to: 'Surat (GJ)',
      type: 'money',
      amount: '₹ 42,00,000',
      method: 'IMPS Layering (Tranche 1)',
      status: 'Mule A/C **9014',
      color: '#F2A33A'
    },
    {
      id: 2,
      from: 'Surat (GJ)',
      to: 'Chandni Chowk, Delhi',
      type: 'money',
      amount: '₹ 42,00,000',
      method: 'Return Loop (Shell Garment)',
      status: 'Looped Back to Origin',
      color: '#E5484D',
      isLoop: true
    },
    {
      id: 3,
      from: 'Delhi NCR',
      to: 'Noida (UP)',
      type: 'calls',
      amount: '41 Calls Spike',
      method: 'VoIP SIM-Box Proxy',
      status: 'Curfew Hours (01:00 - 04:00)',
      color: '#3FB6A8'
    },
    {
      id: 4,
      from: 'Kolkata (WB)',
      to: 'Jaipur (RJ)',
      type: 'money',
      amount: '₹ 28,50,000',
      method: 'RTGS High-Frequency Transfer',
      status: 'Beneficiary Entity Confirmed',
      color: '#F2A33A'
    }
  ];

  const filteredArcs = arcs.filter(arc => {
    if (filterMode === 'money') return arc.type === 'money';
    if (filterMode === 'calls') return arc.type === 'calls';
    return true;
  });

  return (
    <section id="trail" className="w-full py-16 px-4 sm:px-6 max-w-6xl mx-auto relative z-10">
      {/* Editorial Section Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass-sm text-[11px] font-mono text-accent mb-2">
            <Layers className="w-3 h-3 text-accent" />
            <span>SECTION 02 · BALLISTIC FINANCIAL & TELECOM TRAIL</span>
          </div>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-text tracking-tight">
            Follow the money and calls across India.
          </h2>
          <p className="text-xs sm:text-sm text-muted font-normal mt-1.5 max-w-xl">
            Correlated RTGS/IMPS layering hops and synchronized VoIP call bursts across state jurisdictions.
          </p>
        </div>

        {/* Filter Toggle Pills */}
        <div className="glass-pill p-1 flex items-center gap-1 self-start md:self-auto">
          <button
            onClick={() => setFilterMode('all')}
            className={`px-3 py-1.5 rounded-full text-xs font-mono transition-all ${
              filterMode === 'all' ? 'bg-white/10 text-text font-semibold' : 'text-muted hover:text-text'
            }`}
          >
            All Vectors
          </button>
          <button
            onClick={() => setFilterMode('money')}
            className={`px-3 py-1.5 rounded-full text-xs font-mono transition-all ${
              filterMode === 'money' ? 'bg-accent/20 text-accent font-semibold' : 'text-muted hover:text-text'
            }`}
          >
            Money Trails
          </button>
          <button
            onClick={() => setFilterMode('calls')}
            className={`px-3 py-1.5 rounded-full text-xs font-mono transition-all ${
              filterMode === 'calls' ? 'bg-data/20 text-data font-semibold' : 'text-muted hover:text-text'
            }`}
          >
            Call Bursts
          </button>
        </div>
      </div>

      {/* Main Container: Split Visual Arcs + Telemetry Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Ballistic Arcs List */}
        <div className="lg:col-span-8 space-y-3.5">
          {filteredArcs.map((arc) => (
            <div
              key={arc.id}
              className={`glass p-5 rounded-2xl border transition-all duration-300 relative overflow-hidden ${
                arc.isLoop ? 'border-alert/40 bg-alert/[0.04]' : 'border-white/10 hover:border-white/20'
              }`}
            >
              {arc.isLoop && (
                <div className="absolute top-0 right-0 bg-alert text-ink text-[9px] font-mono font-bold uppercase px-3 py-0.5 rounded-bl-lg">
                  Layering Loop Alert
                </div>
              )}

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                <div className="flex items-center gap-2 font-serif text-xl text-text">
                  <span>{arc.from}</span>
                  <ArrowRight className="w-4 h-4 text-accent" />
                  <span className={arc.isLoop ? 'text-alert font-bold' : ''}>{arc.to}</span>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className="font-mono text-base font-bold"
                    style={{ color: arc.color }}
                  >
                    {arc.amount}
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/[0.06] text-xs font-mono">
                <span className="text-muted">{arc.method}</span>
                <span className="text-muted/80">{arc.status}</span>
              </div>
            </div>
          ))}

          {/* Layering Return Summary Alert Box */}
          <div className="glass p-4 rounded-xl border border-alert/30 bg-alert/[0.06] flex items-center gap-3 text-xs font-mono text-text">
            <AlertCircle className="w-5 h-5 text-alert shrink-0" />
            <span>
              <strong className="text-alert font-bold">Provenance Evidence Link:</strong> ₹42,00,000 sent from Surat Axis A/C returned to Delhi origin account via fake garment invoices within 18 hours.
            </span>
          </div>
        </div>

        {/* Right: Telemetry Telemetry Side-Cards */}
        <div className="lg:col-span-4 space-y-4">
          {/* Live Volume Counter */}
          <div className="glass p-6 rounded-2xl border border-white/10 text-center space-y-2">
            <span className="text-[10px] font-mono text-muted uppercase tracking-wider">
              Total Correlated Volume Routed
            </span>
            <div className="font-mono text-3xl sm:text-4xl font-bold text-accent tracking-tight">
              ₹ {(countVolume / 100000).toFixed(2)} Lakh
            </div>
            <p className="text-[11px] font-mono text-data">
              +100% Deterministic Reconstruction
            </p>
          </div>

          {/* Telecom Telemetry */}
          <div className="glass p-5 rounded-2xl border border-white/10 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono text-muted">
              <span className="flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-data" />
                <span>Call Logs Correlated</span>
              </span>
              <span className="font-bold text-text">{totalCalls}</span>
            </div>

            <div className="flex items-center justify-between text-xs font-mono text-muted">
              <span className="flex items-center gap-1.5">
                <Network className="w-3.5 h-3.5 text-accent" />
                <span>Cell Towers Identified</span>
              </span>
              <span className="font-bold text-text">14 Towers</span>
            </div>

            <div className="flex items-center justify-between text-xs font-mono text-muted">
              <span className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-alert" />
                <span>Mule Accounts Flagged</span>
              </span>
              <span className="font-bold text-text">{totalMules} Accounts</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default MoneyCallArcs;
