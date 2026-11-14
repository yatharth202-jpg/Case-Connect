import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useCaseFlow } from '../../context/CaseFlowContext';
import {
  Shield,
  FolderOpen,
  LogOut,
  User,
  Power,
  Layers,
  FileSpreadsheet,
  Activity,
  CheckCircle2,
  Lock
} from 'lucide-react';

export const Header = ({ onOpenSavedCases, activeSection = 'intake' }) => {
  const { user, logout } = useAuth();
  const { phase, resetToUpload, activeCaseData, recentCases } = useCaseFlow();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 30);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToAnchor = (id) => {
    if (id === 'intake') {
      if (phase === 'case') {
        resetToUpload();
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    if (id === 'audit-trail') {
      const element = document.getElementById('section-bsa-admissibility') || document.getElementById('evidence');
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      } else {
        window.location.href = '/audit';
      }
      return;
    }

    if (id === 'graph-explorer') {
      const element = document.getElementById('section-topological-graph') || document.getElementById('network');
      if (element) element.scrollIntoView({ behavior: 'smooth' });
      return;
    }

    if (id === 'lead-triage') {
      const element = document.getElementById('lead') || document.getElementById('section-topological-graph');
      if (element) element.scrollIntoView({ behavior: 'smooth' });
      return;
    }

    if (id === 'correlation-analytics') {
      const element = document.getElementById('section-financial-flow') || document.getElementById('forensics');
      if (element) element.scrollIntoView({ behavior: 'smooth' });
      return;
    }

    if (id === 'evidence-vault') {
      const element = document.getElementById('section-bsa-admissibility') || document.getElementById('evidence');
      if (element) element.scrollIntoView({ behavior: 'smooth' });
      return;
    }

    const genericEl = document.getElementById(id);
    if (genericEl) genericEl.scrollIntoView({ behavior: 'smooth' });
  };

  const navItems = [
    { id: 'intake', label: 'INTAKE' },
    { id: 'lead-triage', label: 'LEAD TRIAGE' },
    { id: 'audit-trail', label: 'AUDIT TRAIL' },
    { id: 'graph-explorer', label: 'GRAPH EXPLORER' },
    { id: 'correlation-analytics', label: 'CORRELATION ANALYTICS' },
    { id: 'evidence-vault', label: 'EVIDENCE VAULT' }
  ];

  return (
    <header
      className={`fixed top-0 left-0 w-full z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-[#0d1117]/95 backdrop-blur-xl border-b border-[#21262d] shadow-2xl py-2'
          : 'bg-[#0d1117]/85 backdrop-blur-md border-b border-[#21262d]/70 py-2.5'
      }`}
    >
      <div className="w-full px-4 sm:px-8 flex items-center justify-between gap-4">
        
        {/* Brand / UNIT-X Identifier */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => scrollToAnchor('intake')}
            className="flex items-center gap-2.5 group text-left focus:outline-none"
            title="Return to Intake Screen"
          >
            <div className="w-7 h-7 rounded bg-[#161b22] border border-[#30363d] flex items-center justify-center text-cyan-400 group-hover:border-cyan-400 transition-colors">
              <Shield className="w-4 h-4 text-cyan-400" />
            </div>
            <span className="font-sans font-bold text-base sm:text-lg tracking-wider uppercase text-white group-hover:text-cyan-400 transition-colors">
              CaseConnect
            </span>
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#161b22] text-cyan-400 border border-cyan-500/30 font-semibold tracking-widest">
              UNITX
            </span>
          </button>

          <div className="h-4 w-px bg-[#30363d] mx-1 hidden sm:block" />

          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#161b22] border border-[#30363d]">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            <span className="font-mono text-[9px] text-amber-400 uppercase tracking-widest font-semibold">
              AIR-GAPPED CLASSIFIED
            </span>
          </div>
        </div>

        {/* Tactical Navigation Links (Desktop) */}
        <nav className="hidden xl:flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = activeSection === item.id || (item.id === 'intake' && phase === 'upload');
            return (
              <button
                key={item.id}
                onClick={() => scrollToAnchor(item.id)}
                className={`font-mono text-xs px-3 py-1.5 rounded transition-all tracking-wider uppercase ${
                  isActive
                    ? 'bg-cyan-400 text-slate-950 font-bold shadow-[0_0_15px_rgba(0,229,255,0.35)]'
                    : 'text-slate-400 hover:bg-[#161b22] hover:text-white'
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Right Actions & Officer Telemetry */}
        <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
          
          {/* Saved Cases Button */}
          <button
            onClick={onOpenSavedCases}
            className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#161b22] border border-[#30363d] text-slate-200 hover:bg-[#1c222c] hover:border-cyan-400/50 transition-all text-xs font-mono"
            title="Open Stored Case Files Ledger"
          >
            <FolderOpen className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline uppercase">Saved Cases</span>
            <span className="px-1.5 py-0.2 rounded-full bg-[#0d1117] border border-[#30363d] text-[10px] text-cyan-300 font-bold">
              {recentCases ? recentCases.length : 14}
            </span>
          </button>

          {/* Officer ID Badge */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded bg-[#161b22] border border-[#30363d] text-xs font-mono">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
            <span className="text-white font-medium truncate max-w-[120px]">
              {user?.username || 'investigator1'}
            </span>
            <span className="text-[9px] px-1 rounded bg-[#0d1117] text-cyan-400 border border-cyan-500/30 uppercase tracking-tighter">
              [LEO-AUTHORIZED]
            </span>
          </div>

          {/* Air-Gapped Secure Status */}
          <div className="flex items-center gap-1.5 text-slate-400" title="System Health: Air-Gapped Secure / Offline Enclave">
            <Lock className="w-4 h-4 text-emerald-400" />
          </div>

          {/* Profile / Switch Officer Avatar */}
          <button
            onClick={() => { window.location.href = '/login'; }}
            className="w-8 h-8 rounded-full bg-cyan-400 hover:bg-cyan-300 text-slate-950 flex items-center justify-center transition-colors"
            title="Switch User / Officer Authentication"
          >
            <User className="w-4 h-4" />
          </button>

          {/* Terminate Session / Logout Action */}
          <button
            onClick={() => {
              logout();
              window.location.href = '/login';
            }}
            className="flex items-center justify-center p-1.5 rounded text-slate-400 hover:bg-[#161b22] hover:text-red-400 transition-colors"
            title="Terminate Secure Session"
          >
            <Power className="w-4 h-4" />
          </button>

        </div>
      </div>
    </header>
  );
};

export default Header;
