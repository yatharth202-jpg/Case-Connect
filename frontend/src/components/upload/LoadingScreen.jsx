import React, { useEffect, useState } from 'react';
import { useCaseFlow } from '../../context/CaseFlowContext';
import { Shield, Cpu, Binary, CheckCircle2 } from 'lucide-react';

export const LoadingScreen = () => {
  const { loadingProgress, loadingStepText, phase } = useCaseFlow();
  const [tokens, setTokens] = useState([]);

  // Generate ambient floating evidence tokens converging toward the center
  useEffect(() => {
    if (phase !== 'loading') return;

    const sampleTokens = [
      'IMPS/₹42,00,000', 'AXIS_9014', 'CDR:+91-98210-XXXXX',
      'IP:103.24.18.9', 'TOWER:DEL-NOI-04', 'SHA-256:e3b0c442...',
      'RTGS/CHANDNI_CHOWK', 'SDR:MULE_SIM_08', 'NEO4J_SYNTHESIS'
    ];

    const generated = sampleTokens.map((text, i) => ({
      id: i,
      text,
      angle: (i / sampleTokens.length) * 2 * Math.PI,
      delay: i * 0.4,
    }));

    setTokens(generated);
  }, [phase]);

  if (phase !== 'loading') return null;

  const circumference = 2 * Math.PI * 42; // ~263.89
  const strokeOffset = circumference - (circumference * loadingProgress) / 100;

  return (
    <div className="fixed inset-0 z-50 bg-ink/90 backdrop-blur-2xl flex flex-col items-center justify-center p-6 text-center animate-fadeIn select-none overflow-hidden">
      {/* Background Animated Evidence Particles */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {tokens.map((tok) => (
          <div
            key={tok.id}
            className="absolute font-mono text-[10px] text-accent/40 px-2 py-0.5 rounded-full border border-accent/20 bg-accent/5 backdrop-blur-sm animate-pulse"
            style={{
              top: `${50 + 35 * Math.sin(tok.angle)}%`,
              left: `${50 + 38 * Math.cos(tok.angle)}%`,
              transform: 'translate(-50%, -50%)',
              animationDuration: `${3 + tok.id * 0.5}s`,
            }}
          >
            {tok.text}
          </div>
        ))}
      </div>

      {/* Center Forensic Progress Hub */}
      <div className="relative z-10 glass max-w-md w-full p-8 sm:p-10 border border-white/10 flex flex-col items-center space-y-6">
        {/* Animated Progress Ring */}
        <div className="relative w-32 h-32 flex items-center justify-center">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 96 96">
            {/* Background Track */}
            <circle
              cx="48"
              cy="48"
              r="42"
              fill="none"
              stroke="rgba(255, 255, 255, 0.08)"
              strokeWidth="4"
            />
            {/* Animated Dynamic Amber Stroke */}
            <circle
              cx="48"
              cy="48"
              r="42"
              fill="none"
              stroke="#F2A33A"
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeOffset}
              style={{ transition: 'stroke-dashoffset 0.4s ease-out' }}
            />
          </svg>

          {/* Percentage Counter in Center */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-3xl font-semibold text-text tracking-tighter">
              {Math.round(loadingProgress)}%
            </span>
            <span className="font-mono text-[9px] uppercase tracking-widest text-accent">
              Synthesizing
            </span>
          </div>
        </div>

        {/* Step Indicator & Typewriter Text */}
        <div className="space-y-2 w-full">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full glass-sm text-[10px] font-mono text-data">
            <Cpu className="w-3 h-3 animate-spin text-data" />
            <span>ALGORITHMIC EXTRACTION RUNNING</span>
          </div>

          <p className="font-mono text-xs text-text min-h-[36px] flex items-center justify-center font-medium leading-relaxed px-2">
            {loadingStepText}
          </p>
        </div>

        {/* Forensic Standards Badges */}
        <div className="w-full pt-4 border-t border-white/[0.06] flex items-center justify-between text-[10px] font-mono text-muted">
          <span className="flex items-center gap-1">
            <Shield className="w-3 h-3 text-accent" />
            <span>Sec 63 BSA 2023</span>
          </span>
          <span className="flex items-center gap-1">
            <Binary className="w-3 h-3 text-data" />
            <span>SHA-256 Ledger Lock</span>
          </span>
        </div>
      </div>
    </div>
  );
};

export default LoadingScreen;
