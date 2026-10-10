import React from 'react';
import { useAuth } from '../context/AuthContext';

export default function Navbar({ onOpenLegalModal }) {
  const { user, isAdmin, logout } = useAuth();

  return (
    <header className="bg-[#080d19] border-b border-[#182338] px-6 py-3 flex items-center justify-between sticky top-0 z-40">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-[#0e172c] border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-white font-bold text-sm tracking-wide">CASE CONNECT</span>
            <span className="text-[10px] px-1.5 py-0.2 bg-blue-950/80 text-blue-400 border border-blue-500/30 rounded font-mono font-semibold">
              PS SIH26189
            </span>
          </div>
          <p className="text-[10px] text-slate-400 font-mono leading-none">Evidence Correlation & Syndicate Topology</p>
        </div>
      </div>

      {/* Nav links */}
      <nav className="flex items-center gap-3 text-xs">
        <a
          href="/"
          className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-md font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <span>Investigation Workbench</span>
        </a>

        <a
          href="/cases"
          className="text-slate-300 hover:text-white px-2.5 py-1.5 rounded transition-colors"
        >
          Case Repository
        </a>

        {isAdmin && (
          <a
            href="/audit"
            className="text-[#cbd5e1] hover:text-white px-2 py-1 rounded transition-colors"
          >
            Audit Trail
          </a>
        )}

        <button
          onClick={() => onOpenLegalModal('bsa')}
          className="text-[#94a3b8] hover:text-[#38bdf8] transition-colors"
        >
          Section 63 BSA
        </button>

        <button
          onClick={() => onOpenLegalModal('dpdp')}
          className="text-[#94a3b8] hover:text-[#38bdf8] transition-colors"
        >
          DPDP 2023
        </button>
      </nav>

      {/* User profile & Logout */}
      <div className="flex items-center gap-3">
        {user ? (
          <div className="flex items-center gap-3 bg-[#030712] border border-[#1e293b] px-3 py-1.5 rounded-md">
            <div className="text-right">
              <span className="text-xs text-white font-medium block leading-tight">{user.username}</span>
              <span className="text-[10px] text-[#38bdf8] font-mono uppercase tracking-wider block">
                {user.role}
              </span>
            </div>
            <button
              onClick={logout}
              className="text-xs text-[#94a3b8] hover:text-rose-400 border-l border-[#1e293b] pl-3 py-0.5 transition-colors"
              title="Sign Out"
            >
              Logout
            </button>
          </div>
        ) : (
          <a
            href="/login"
            className="text-xs bg-[#0284c7] hover:bg-[#0369a1] text-white px-3 py-1.5 rounded-md transition-colors font-medium"
          >
            Sign In
          </a>
        )}
      </div>
    </header>
  );
}
