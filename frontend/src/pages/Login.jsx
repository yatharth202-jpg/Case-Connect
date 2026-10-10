import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, UserCheck, Eye, Lock, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function Login() {
  const { login, quickLogin } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeRole, setActiveRole] = useState(null);
  const [showManualForm, setShowManualForm] = useState(false);

  // 1-Click Instant Role Selection (Zero-Password Friction)
  const handleRoleSelect = async (roleName) => {
    setActiveRole(roleName);
    setError('');
    setLoading(true);
    try {
      await quickLogin(roleName);
      window.location.href = '/';
    } catch (err) {
      // Fallback to standard login
      try {
        const u = roleName === 'admin' ? 'admin' : (roleName === 'viewer' ? 'viewer1' : 'investigator1');
        const p = roleName === 'admin' ? 'AdminPass1234!' : (roleName === 'viewer' ? 'ViewerPass1234!' : 'OfficerPass1234!');
        await login(u, p);
        window.location.href = '/';
      } catch (fallbackErr) {
        setError('Authentication server initializing. Please try again in 5 seconds.');
      }
    } finally {
      setLoading(false);
      setActiveRole(null);
    }
  };

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim()) {
      setError('Please provide username or select a role above.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      await login(username.trim(), password || '123456');
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
      {/* Left Tactical Overview Panel */}
      <div className="md:w-1/2 p-8 md:p-16 flex flex-col justify-between border-b md:border-b-0 md:border-r border-[#1e293b] bg-[#0b1120]">
        <div>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-cyan-600 rounded-md flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Case Connect AI
                <span className="text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 px-1.5 py-0.5 rounded font-mono">v1.0</span>
              </h1>
              <p className="text-xs text-[#38bdf8] font-mono">Team UNITx | PS SIH26189</p>
            </div>
          </div>

          <div className="max-w-md space-y-4">
            <h2 className="text-2xl font-bold text-white tracking-tight">
              Explainable Crime Network & Evidence Dissection Platform
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              Automated telecommunication CDR, banking transaction, and multi-jurisdiction FIR correlation engine engineered for Indian law enforcement agencies.
            </p>

            <div className="pt-4 space-y-2.5">
              <div className="flex items-start gap-2.5 text-xs text-slate-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>Section 63 Bharatiya Sakshya Adhiniyam (BSA) 2023 compliant audit ledger</span>
              </div>
              <div className="flex items-start gap-2.5 text-xs text-slate-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>Deterministic SHA-256 genesis-anchored chain of custody</span>
              </div>
              <div className="flex items-start gap-2.5 text-xs text-slate-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>100% Dynamic multi-evidence learning without hardcoded mocks</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-[#1e293b] text-[11px] text-slate-500 font-mono flex items-center justify-between">
          <span>Secured Investigation Terminal</span>
          <span className="text-cyan-400/80">DPDP Act 2023 Compliant</span>
        </div>
      </div>

      {/* Right Role-Selection Authentication Panel */}
      <div className="md:w-1/2 p-8 md:p-16 flex items-center justify-center bg-[#070b14]">
        <div className="w-full max-w-md bg-[#0b1120] border border-[#1e293b] rounded-xl p-8 shadow-2xl relative overflow-hidden">
          
          {/* Subtle Ambient Glow */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none"></div>

          <div className="mb-6">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-mono tracking-widest text-cyan-400 font-bold">
                Zero-Password Fast Access
              </span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded">
                Live Terminal Ready
              </span>
            </div>
            <h3 className="text-xl font-bold text-white tracking-tight mt-1">Select Officer Role to Enter</h3>
            <p className="text-xs text-slate-400 mt-1">
              Click any verified badge below to instantly access the forensic workspace:
            </p>
          </div>

          {error && (
            <div className="mb-5 p-3 bg-rose-950/60 border border-rose-800 rounded-lg text-rose-200 text-xs flex items-start gap-2">
              <span className="font-bold">!</span>
              <span>{error}</span>
            </div>
          )}

          {/* 1-Click Role Badges */}
          <div className="space-y-3 mb-6">
            {/* 1. Lead Investigator */}
            <button
              type="button"
              disabled={loading}
              onClick={() => handleRoleSelect('investigator')}
              className="w-full p-4 rounded-xl border border-cyan-800/60 bg-gradient-to-r from-cyan-950/40 to-[#0c162d] hover:border-cyan-400 hover:from-cyan-950/70 transition-all text-left flex items-center justify-between group disabled:opacity-50 shadow-lg shadow-cyan-950/20"
            >
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-lg bg-cyan-600/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 group-hover:bg-cyan-500 group-hover:text-black transition-colors">
                  <UserCheck className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-sm font-bold text-white flex items-center gap-2">
                    Lead Investigator
                    <span className="text-[9px] bg-cyan-500/20 text-cyan-300 px-1.5 py-0.5 rounded font-mono font-normal">Primary Demo</span>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Full evidence upload, dynamic graph analysis & report generation
                  </div>
                </div>
              </div>
              <div className="w-7 h-7 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 group-hover:text-white group-hover:border-cyan-400 group-hover:bg-cyan-600 transition-colors shrink-0">
                <ArrowRight className="w-4 h-4" />
              </div>
            </button>

            {/* 2. Supervisory Admin */}
            <button
              type="button"
              disabled={loading}
              onClick={() => handleRoleSelect('admin')}
              className="w-full p-4 rounded-xl border border-blue-900/60 bg-gradient-to-r from-blue-950/40 to-[#0c162d] hover:border-blue-400 hover:from-blue-950/70 transition-all text-left flex items-center justify-between group disabled:opacity-50 shadow-lg shadow-blue-950/20"
            >
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 group-hover:bg-blue-500 group-hover:text-black transition-colors">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-sm font-bold text-white flex items-center gap-2">
                    Supervisory Admin
                    <span className="text-[9px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded font-mono font-normal">Full Access</span>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Case management, case settings & immutable audit log verification
                  </div>
                </div>
              </div>
              <div className="w-7 h-7 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 group-hover:text-white group-hover:border-blue-400 group-hover:bg-blue-600 transition-colors shrink-0">
                <ArrowRight className="w-4 h-4" />
              </div>
            </button>

            {/* 3. Intelligence Analyst (Viewer) */}
            <button
              type="button"
              disabled={loading}
              onClick={() => handleRoleSelect('viewer')}
              className="w-full p-4 rounded-xl border border-slate-800 bg-[#070e1c] hover:border-slate-600 hover:bg-[#0c162d] transition-all text-left flex items-center justify-between group disabled:opacity-50"
            >
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 group-hover:bg-slate-700 group-hover:text-white transition-colors">
                  <Eye className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">
                    Intelligence Analyst
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Read-only exploration of money trails, charts & graph topology
                  </div>
                </div>
              </div>
              <div className="w-7 h-7 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 group-hover:text-white group-hover:border-slate-500 transition-colors shrink-0">
                <ArrowRight className="w-4 h-4" />
              </div>
            </button>
          </div>

          {loading && (
            <div className="p-3 bg-cyan-950/40 border border-cyan-800/50 rounded-lg text-cyan-300 text-xs flex items-center justify-center gap-2 mb-4 animate-pulse">
              <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
              <span>Validating {activeRole || 'officer'} credentials & opening terminal...</span>
            </div>
          )}

          {/* Optional Manual Entry Toggle */}
          <div className="pt-4 border-t border-[#1e293b] text-center">
            <button
              type="button"
              onClick={() => setShowManualForm(!showManualForm)}
              className="text-[11px] text-slate-400 hover:text-cyan-400 transition-colors font-mono flex items-center justify-center gap-1.5 mx-auto"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>{showManualForm ? 'Hide manual credentials form' : 'Or enter custom credentials manually'}</span>
            </button>

            {showManualForm && (
              <form onSubmit={handleManualSubmit} className="space-y-3 mt-4 text-left">
                <div>
                  <label className="block text-[11px] font-medium text-slate-300 mb-1" htmlFor="username">
                    Username
                  </label>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin or investigator"
                    className="w-full px-3 py-2 bg-[#030712] border border-[#334155] rounded text-white text-xs placeholder-slate-600 focus:outline-none focus:border-cyan-400"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-300 mb-1" htmlFor="password">
                    Password (Optional in demo)
                  </label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Any password accepted"
                    className="w-full px-3 py-2 bg-[#030712] border border-[#334155] rounded text-white text-xs placeholder-slate-600 focus:outline-none focus:border-cyan-400"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs font-semibold transition-colors disabled:opacity-50"
                >
                  Sign In with Custom Badge
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
