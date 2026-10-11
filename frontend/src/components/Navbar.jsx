import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, HelpCircle, LogOut, Activity, Lock, Database, FileText } from 'lucide-react';

export default function Navbar({ onOpenLegalModal }) {
  const { user, isAdmin, logout } = useAuth();
  const currentPath = window.location.pathname;

  const roleColors = {
    admin: 'border-violet-500/40 text-violet-300 bg-violet-950/40',
    investigator: 'border-cyan-500/40 text-cyan-300 bg-cyan-950/40',
    viewer: 'border-emerald-500/40 text-emerald-300 bg-emerald-950/40',
  };

  const userBadgeColor = roleColors[user?.role] || 'border-cyan-500/40 text-cyan-300 bg-cyan-950/40';

  return (
    <header className="relative z-40 border-b border-slate-800/80 bg-[#070D1D]/95 backdrop-blur-md px-4 sm:px-6 lg:px-12 py-3 transition-all select-none sticky top-0">
      <div className="max-w-[1720px] mx-auto flex flex-col md:flex-row items-center justify-between gap-3 sm:gap-4">
        {/* Brand & Tagline */}
        <div className="flex items-center gap-3.5 w-full md:w-auto justify-between md:justify-start">
          <div className="flex items-center gap-3">
            <div className="relative flex items-center justify-center w-10 h-10 rounded-lg border border-cyan-500/40 bg-cyan-950/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.25)] shrink-0">
              {/* Ashoka Pillar / Police Emblem Vector Symbol */}
              <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24">
                <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3z" />
                <path d="M12 7v8" />
                <path d="M9 10h6" />
                <circle cx="12" cy="11" r="2.5" />
              </svg>
              <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500" />
              </span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <a href="/" className="text-xl sm:text-2xl font-bold tracking-tight text-white font-cyber flex items-center hover:opacity-95 transition">
                  Case Connect <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500 ml-1.5 font-extrabold">AI</span>
                </a>
                <span className="text-[10px] uppercase font-mono tracking-widest px-1.5 py-0.5 rounded bg-blue-900/50 text-cyan-300 border border-blue-500/30">
                  v4.8-LEO
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium tracking-wide hidden sm:block">
                Explainable Crime Network & Evidence Dissection Platform
              </p>
            </div>
          </div>

          {/* Mobile Right Badges */}
          <div className="flex md:hidden items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399] animate-pulse" />
            <span className="text-[10px] font-mono text-emerald-400 font-bold">ONLINE</span>
          </div>
        </div>

        {/* Center: Navigation Links */}
        <nav className="flex items-center gap-2 sm:gap-2.5 text-xs font-mono">
          <a
            href="/"
            className={`px-3 py-1.5 rounded-lg font-bold transition-all flex items-center gap-1.5 ${
              currentPath === '/'
                ? 'bg-gradient-to-r from-cyan-950 via-cyan-900/70 to-cyan-950 border border-cyan-400 text-cyan-300 shadow-[0_0_15px_rgba(0,240,255,0.25)]'
                : 'text-slate-300 hover:text-white hover:bg-slate-900/80 border border-transparent'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Investigation Workbench</span>
          </a>

          <a
            href="/cases"
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              currentPath.startsWith('/cases')
                ? 'bg-gradient-to-r from-blue-950 via-blue-900/70 to-blue-950 border border-blue-400 text-blue-300 shadow-[0_0_15px_rgba(59,130,246,0.25)] font-bold'
                : 'text-slate-300 hover:text-white hover:bg-slate-900/80 border border-transparent'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Case Repository</span>
          </a>

          {isAdmin && (
            <a
              href="/audit"
              className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                currentPath === '/audit'
                  ? 'bg-gradient-to-r from-violet-950 via-violet-900/70 to-violet-950 border border-violet-400 text-violet-300 shadow-[0_0_15px_rgba(139,92,246,0.25)] font-bold'
                : 'text-slate-300 hover:text-white hover:bg-slate-900/80 border border-transparent'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Audit Trail</span>
            </a>
          )}
        </nav>

        {/* Right: Telemetry & Controls */}
        <div className="flex items-center gap-3 lg:gap-4">
          {/* Live Operations Badges (Hidden on tiny screens) */}
          <div className="hidden xl:flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-900/90 border border-slate-700/80 text-[11px] font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399] animate-pulse" />
            <span className="text-emerald-400 font-semibold tracking-wide">Live Terminal Ready</span>
          </div>

          <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-full bg-cyan-950/40 border border-cyan-500/30 text-[11px] font-medium text-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.15)] font-mono">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="tracking-wide">Secure Connection</span>
          </div>

          {/* Quick Legal Modals */}
          <button
            onClick={() => onOpenLegalModal('bsa')}
            className="hidden md:inline-flex px-2 py-1 text-[10px] font-mono text-slate-400 hover:text-cyan-300 bg-slate-900/60 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-500/40 rounded transition"
            title="Section 63 BSA 2023 Statutory Compliance"
          >
            Sec. 63 BSA
          </button>

          <button
            onClick={() => onOpenLegalModal('dpdp')}
            className="hidden md:inline-flex px-2 py-1 text-[10px] font-mono text-slate-400 hover:text-cyan-300 bg-slate-900/60 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-500/40 rounded transition"
            title="DPDP Act 2023 Law Enforcement Exemption"
          >
            DPDP 2023
          </button>

          {/* Officer profile & Logout */}
          {user ? (
            <div className="flex items-center gap-2.5 pl-2 border-l border-slate-800">
              <div className={`flex items-center gap-2 px-2.5 py-1 rounded-lg border font-mono ${userBadgeColor}`}>
                <div className="text-right">
                  <span className="text-xs text-white font-semibold block leading-tight font-sans">{user.username}</span>
                  <span className="text-[9px] uppercase tracking-wider block font-bold">
                    {user.role}
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => onOpenLegalModal('help')}
                className="w-8 h-8 flex items-center justify-center rounded-lg border border-slate-700/70 bg-slate-900/80 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition"
                title="System Manual & Operator Guidelines"
              >
                <HelpCircle className="w-4 h-4" />
              </button>

              <button
                type="button"
                onClick={logout}
                className="w-8 h-8 flex items-center justify-center rounded-lg border border-slate-700/70 bg-slate-900/80 text-slate-300 hover:text-rose-400 hover:border-rose-500/40 transition"
                title="Secure Terminal Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <a
              href="/login"
              className="cyber-btn-cut px-4 py-1.5 bg-gradient-to-r from-cyan-950 via-cyan-900/60 to-cyan-950 border border-cyan-400 text-cyan-300 font-cyber font-bold tracking-wider text-xs hover:bg-cyan-400 hover:text-black transition"
            >
              Sign In
            </a>
          )}
        </div>
      </div>
    </header>
  );
}
