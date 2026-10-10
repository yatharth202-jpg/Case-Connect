import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Please provide both username and password.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      await login(username.trim(), password);
      window.location.href = '/';
    } catch (err) {
      const msg = err.response?.data?.detail || 'Authentication failed. Please verify credentials.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (u, p) => {
    setUsername(u);
    setPassword(p);
    setError('');
    setLoading(true);
    try {
      await login(u, p);
      window.location.href = '/';
    } catch (err) {
      const msg = err.response?.data?.detail || 'Authentication failed. Please verify credentials.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 flex flex-col md:flex-row">
      {/* Left Hero Panel */}
      <div className="md:w-1/2 p-8 md:p-16 flex flex-col justify-between border-b md:border-b-0 md:border-r border-[#1e293b] bg-[#0b1120]">
        <div>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-[#0284c7] rounded-md flex items-center justify-center text-white">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">Case Connect AI</h1>
              <p className="text-xs text-[#38bdf8] font-mono">Team UNITx | PS SIH26189</p>
            </div>
          </div>

          <div className="max-w-md space-y-4">
            <h2 className="text-2xl font-bold text-white tracking-tight">
              Crime Network Analysis & Evidence Dissection Platform
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              Automated telecommunication CDR, banking transaction, and multi-jurisdiction FIR correlation engine engineered for Indian law enforcement agencies.
            </p>

            <div className="pt-4 space-y-2.5">
              <div className="flex items-start gap-2.5 text-xs text-slate-300">
                <span className="text-[#38bdf8] mt-0.5 font-bold">[OK]</span>
                <span>Section 63 Bharatiya Sakshya Adhiniyam (BSA) 2023 compliant audit ledger</span>
              </div>
              <div className="flex items-start gap-2.5 text-xs text-slate-300">
                <span className="text-[#38bdf8] mt-0.5 font-bold">[OK]</span>
                <span>Deterministic SHA-256 chain of custody verification</span>
              </div>
              <div className="flex items-start gap-2.5 text-xs text-slate-300">
                <span className="text-[#38bdf8] mt-0.5 font-bold">[OK]</span>
                <span>Air-gapped offline operation without external network dependencies</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-[#1e293b] text-[11px] text-slate-500 font-mono">
          Secured Investigation Terminal | Authorized Law Enforcement Personnel Only
        </div>
      </div>

      {/* Right Login Form Panel */}
      <div className="md:w-1/2 p-8 md:p-16 flex items-center justify-center">
        <div className="w-full max-w-sm bg-[#0b1120] border border-[#1e293b] rounded-lg p-8 shadow-xl">
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-white tracking-tight">Officer Authentication</h3>
            <p className="text-xs text-slate-400 mt-1">Enter your assigned badge credentials to open your workspace.</p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-rose-950/60 border border-rose-800 rounded text-rose-200 text-xs flex items-start gap-2">
              <span className="font-bold">!</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5" htmlFor="username">
                Official Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. officer_admin"
                className="w-full px-3 py-2 bg-[#030712] border border-[#334155] rounded text-white text-xs placeholder-slate-600 focus:outline-none focus:border-[#38bdf8]"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3 py-2 bg-[#030712] border border-[#334155] rounded text-white text-xs placeholder-slate-600 focus:outline-none focus:border-[#38bdf8]"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-[#0284c7] hover:bg-[#0369a1] text-white rounded text-xs font-semibold tracking-wide transition-colors mt-2 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                  </svg>
                  <span>Authenticating...</span>
                </>
              ) : (
                'Secure Authentication'
              )}
            </button>
          </form>

          <div className="mt-5 pt-3.5 border-t border-[#1e293b] space-y-2">
            <div className="text-[10px] text-slate-400 font-mono text-center uppercase tracking-wider">
              1-Click Instant Badge Sign-In:
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                disabled={loading}
                onClick={() => handleQuickLogin('admin', 'admin123')}
                className="py-2 px-2 bg-[#071128] hover:bg-[#0e2352] border border-[#1e3461] rounded text-[11px] font-mono text-cyan-300 transition-colors text-center flex flex-col items-center disabled:opacity-50"
              >
                <span className="font-bold">⚡ Admin</span>
                <span className="text-[9px] text-slate-400">admin / admin123</span>
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={() => handleQuickLogin('investigator', 'inves123')}
                className="py-2 px-2 bg-[#071128] hover:bg-[#0e2352] border border-[#1e3461] rounded text-[11px] font-mono text-emerald-300 transition-colors text-center flex flex-col items-center disabled:opacity-50"
              >
                <span className="font-bold">⚡ Investigator</span>
                <span className="text-[9px] text-slate-400">investigator / inves123</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
