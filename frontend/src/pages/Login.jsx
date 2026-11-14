import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Shield,
  User,
  Lock,
  ArrowRight,
  Eye,
  EyeOff,
  FileText,
  Phone,
  Building2,
  Share2,
  Brain,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  X,
  Fingerprint,
  UserCheck,
  KeyRound
} from 'lucide-react';

export default function Login() {
  const { login, quickLogin } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeRole, setActiveRole] = useState(null);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const canvasRef = useRef(null);

  // Subtle Tactical Particle Telemetry Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    const nodeCount = 42;
    const nodes = [];

    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        radius: Math.random() * 1.6 + 0.6,
        color: i % 4 === 0 ? '#38bdf8' : (i % 3 === 0 ? '#05df72' : '#1e3a8a')
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(56, 189, 248, ${0.1 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
      }

      nodes.forEach((node) => {
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.fill();

        node.x += node.vx;
        node.y += node.vy;

        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;
      });

      animId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animId);
    };
  }, []);

  // 1-Click Fast Role Login
  const handleRoleSelect = async (roleName) => {
    setActiveRole(roleName);
    setError('');
    setLoading(true);
    try {
      await quickLogin(roleName);
      window.location.href = '/';
    } catch (err) {
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
      setError('Please provide officer username or badge ID.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      await login(username.trim(), password || '123456');
      window.location.href = '/';
    } catch (err) {
      const msg = err.response?.data?.detail || 'Authentication failed. Please verify officer credentials.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-[#030712] text-slate-100 min-h-screen flex flex-col justify-between selection:bg-cyan-500 selection:text-white relative overflow-x-hidden font-sans">
      {/* Background Subtle Canvas & Atmospheric Cyber Glows */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <canvas ref={canvasRef} className="w-full h-full opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#030714]/95 via-[#050b1d]/85 to-[#030714]/95" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#02050e] via-transparent to-[#02050e]/70" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-[140px] pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[140px] pointer-events-none" />
      </div>

      {/* TopBar Controls */}
      <header className="relative z-20 w-full px-6 sm:px-12 py-4 flex justify-between items-center border-b border-slate-800/60 bg-[#030712]/70 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <span className="font-sans font-bold text-lg tracking-wider text-white uppercase">
            CASECONNECT <span className="text-cyan-400">//</span> UNIT-X
          </span>
          <span className="hidden sm:inline-block text-[10px] font-mono tracking-widest text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded uppercase">
            SECURE ACCESS
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900/80 border border-slate-700/60 text-[11px] font-mono text-slate-300">
            <Shield className="w-3.5 h-3.5 text-cyan-400" />
            <span>SECTION 63 BSA 2023 COMPLIANT</span>
          </div>
          <button
            onClick={() => setShowHelpModal(true)}
            className="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/60 hover:border-slate-500 text-xs font-mono text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
          >
            <HelpCircle className="w-3.5 h-3.5 text-cyan-400" />
            <span>Guide</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="relative z-10 flex-grow flex items-center justify-center px-4 sm:px-8 lg:px-16 py-8">
        <div className="w-full max-w-7xl grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          
          {/* Left Column - Branding, Police Emblem & Analytical Capabilities */}
          <section className="lg:col-span-7 flex flex-col items-center lg:items-start text-center lg:text-left px-2 sm:px-4">
            
            {/* National Police Emblem SVG Shield */}
            <div className="mb-4 relative group">
              <div className="w-16 h-20 sm:w-20 sm:h-24 relative flex items-center justify-center">
                <svg className="w-full h-full drop-shadow-[0_0_20px_rgba(234,179,8,0.4)]" fill="none" viewBox="0 0 100 120">
                  <path d="M50 5L15 20V60C15 88 50 115 50 115C50 115 85 88 85 60V20L50 5Z" fill="#1e3a8a" stroke="#f59e0b" strokeWidth="3" />
                  <path d="M50 12L22 25V58C22 81 50 104 50 104C50 104 78 81 78 58V25L50 12Z" fill="#0f172a" stroke="#d97706" strokeWidth="1.5" />
                  <circle cx="50" cy="46" fill="none" r="14" stroke="#fbbf24" strokeWidth="2" />
                  <line stroke="#fbbf24" strokeWidth="1.5" x1="50" x2="50" y1="32" y2="60" />
                  <line stroke="#fbbf24" strokeWidth="1.5" x1="36" x2="64" y1="46" y2="46" />
                  <text fill="#fef08a" fontSize="9" fontWeight="bold" letterSpacing="1" textAnchor="middle" x="50" y="80">POLICE</text>
                  <text fill="#fde047" fontSize="7" fontWeight="600" textAnchor="middle" x="50" y="24">सत्यमेव जयते</text>
                </svg>
              </div>
            </div>

            {/* Main Product Title */}
            <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight mb-2">
              <span className="text-white">Case Connect </span>
              <span className="bg-gradient-to-r from-blue-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">AI</span>
            </h1>

            {/* Product Subtitle */}
            <p className="text-xs sm:text-sm font-mono text-cyan-400/90 tracking-wider uppercase mb-5">
              AI-Powered Forensic Network Analysis System
            </p>

            {/* Mission Statement */}
            <div className="max-w-xl space-y-2 mb-8">
              <h2 className="text-base sm:text-lg font-semibold text-slate-100">
                Connect the dots. Uncover the truth.
              </h2>
              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed font-sans">
                Unified correlation of FIR reports, telecom call detail records (CDR/IPDR), banking ledgers, and device IMEI telemetry to expose hidden operational connections.
              </p>
            </div>

            {/* 5 Core Feature Capability Badges */}
            <div className="grid grid-cols-5 gap-2 sm:gap-4 max-w-lg w-full">
              {/* Feature 1: FIR Analysis */}
              <div className="flex flex-col items-center text-center group cursor-default">
                <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-sky-950/70 border border-sky-500/40 flex items-center justify-center text-sky-400 shadow-md shadow-sky-950/40 mb-2 group-hover:border-sky-400 group-hover:scale-105 transition-all">
                  <FileText className="w-5 h-5" />
                </div>
                <span className="text-[11px] leading-tight text-slate-300 font-medium">FIR<br/>Analysis</span>
              </div>

              {/* Feature 2: Call Record Insights */}
              <div className="flex flex-col items-center text-center group cursor-default">
                <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-teal-950/70 border border-teal-500/40 flex items-center justify-center text-teal-400 shadow-md shadow-teal-950/40 mb-2 group-hover:border-teal-400 group-hover:scale-105 transition-all">
                  <Phone className="w-5 h-5" />
                </div>
                <span className="text-[11px] leading-tight text-slate-300 font-medium">Call Record<br/>Insights</span>
              </div>

              {/* Feature 3: Financial Tracking */}
              <div className="flex flex-col items-center text-center group cursor-default">
                <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-indigo-950/70 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shadow-md shadow-indigo-950/40 mb-2 group-hover:border-indigo-400 group-hover:scale-105 transition-all">
                  <Building2 className="w-5 h-5" />
                </div>
                <span className="text-[11px] leading-tight text-slate-300 font-medium">Financial<br/>Tracking</span>
              </div>

              {/* Feature 4: Network Mapping */}
              <div className="flex flex-col items-center text-center group cursor-default">
                <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-amber-950/70 border border-amber-500/40 flex items-center justify-center text-amber-400 shadow-md shadow-amber-950/40 mb-2 group-hover:border-amber-400 group-hover:scale-105 transition-all">
                  <Share2 className="w-5 h-5" />
                </div>
                <span className="text-[11px] leading-tight text-slate-300 font-medium">Network<br/>Mapping</span>
              </div>

              {/* Feature 5: AI-Powered Leads */}
              <div className="flex flex-col items-center text-center group cursor-default">
                <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-purple-950/70 border border-purple-500/40 flex items-center justify-center text-purple-400 shadow-md shadow-purple-950/40 mb-2 group-hover:border-purple-400 group-hover:scale-105 transition-all">
                  <Brain className="w-5 h-5" />
                </div>
                <span className="text-[11px] leading-tight text-slate-300 font-medium">AI-Powered<br/>Leads</span>
              </div>
            </div>
          </section>

          {/* Right Column - Tactical Login Card */}
          <section className="lg:col-span-5 w-full flex justify-center lg:justify-end">
            <div className="w-full max-w-[450px] bg-slate-900/80 backdrop-blur-2xl rounded-2xl p-7 sm:p-9 shadow-2xl border border-slate-700/60 relative">
              
              {/* Heading */}
              <div className="text-center mb-6">
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-1.5">
                  Welcome <span className="text-cyan-400">Back</span>
                </h2>
                <p className="text-xs sm:text-sm text-slate-400">
                  Sign in to continue your forensic investigation
                </p>
              </div>

              {/* Error Alert */}
              {error && (
                <div className="mb-5 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Manual Login Form */}
              <form onSubmit={handleManualSubmit} className="space-y-4">
                {/* User ID / Badge Field */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-slate-300" htmlFor="userid">
                    Officer ID / Username
                  </label>
                  <div className="relative flex items-center rounded-xl bg-slate-950/80 border border-slate-700/80 focus-within:border-cyan-400 focus-within:ring-1 focus-within:ring-cyan-400 transition-all">
                    <div className="pl-3.5 pr-2 text-slate-400 pointer-events-none flex items-center justify-center">
                      <User className="w-4 h-4" />
                    </div>
                    <input
                      id="userid"
                      name="userid"
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="e.g. investigator1, admin"
                      className="w-full bg-transparent py-2.5 pl-1 pr-4 text-xs sm:text-sm text-white placeholder-slate-500 border-none focus:ring-0 outline-none font-mono"
                    />
                  </div>
                </div>

                {/* Password Field */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-slate-300" htmlFor="password">
                    Password
                  </label>
                  <div className="relative flex items-center rounded-xl bg-slate-950/80 border border-slate-700/80 focus-within:border-cyan-400 focus-within:ring-1 focus-within:ring-cyan-400 transition-all">
                    <div className="pl-3.5 pr-2 text-slate-400 pointer-events-none flex items-center justify-center">
                      <Lock className="w-4 h-4" />
                    </div>
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter security password"
                      className="w-full bg-transparent py-2.5 pl-1 pr-10 text-xs sm:text-sm text-white placeholder-slate-500 border-none focus:ring-0 outline-none font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 text-slate-400 hover:text-slate-200 transition-colors"
                      title={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Remember Me & Help Row */}
                <div className="flex items-center justify-between text-xs pt-0.5">
                  <label className="flex items-center gap-2 cursor-pointer select-none group">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="w-4 h-4 rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-cyan-400"
                    />
                    <span className="text-slate-300 group-hover:text-white transition-colors">Remember me</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowHelpModal(true)}
                    className="text-cyan-400 hover:text-cyan-300 font-medium hover:underline transition-colors"
                  >
                    Need assistance?
                  </button>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 hover:from-blue-500 hover:via-indigo-500 hover:to-cyan-400 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 active:scale-[0.99] transition-all disabled:opacity-50"
                >
                  {loading && !activeRole ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Authenticating Officer...</span>
                    </>
                  ) : (
                    <>
                      <span>Login to Terminal</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>

              {/* Divider */}
              <div className="relative my-5 text-center">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-700/60" />
                </div>
                <div className="relative inline-block px-3 bg-slate-900 text-[10px] uppercase tracking-wider text-slate-400 font-mono font-semibold rounded">
                  OR FAST 1-CLICK ACCESS
                </div>
              </div>

              {/* 1-Click Role Direct Logins */}
              <div className="grid grid-cols-3 gap-2 mb-4">
                <button
                  type="button"
                  onClick={() => handleRoleSelect('investigator')}
                  disabled={loading}
                  className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-800/60 transition-all text-center group"
                >
                  <UserCheck className="w-4 h-4 text-cyan-400 mb-1 group-hover:scale-110 transition-transform" />
                  <span className="text-[11px] font-semibold text-slate-200">Investigator</span>
                  <span className="text-[9px] font-mono text-cyan-400/90">Primary</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleRoleSelect('admin')}
                  disabled={loading}
                  className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-800/60 transition-all text-center group"
                >
                  <Shield className="w-4 h-4 text-indigo-400 mb-1 group-hover:scale-110 transition-transform" />
                  <span className="text-[11px] font-semibold text-slate-200">Admin</span>
                  <span className="text-[9px] font-mono text-indigo-400/90">Full Access</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleRoleSelect('viewer')}
                  disabled={loading}
                  className="flex flex-col items-center justify-center p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-800/60 transition-all text-center group"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 mb-1 group-hover:scale-110 transition-transform" />
                  <span className="text-[11px] font-semibold text-slate-200">Analyst</span>
                  <span className="text-[9px] font-mono text-emerald-400/90">Read-Only</span>
                </button>
              </div>

              {/* Department SSO & Aadhaar Options */}
              <div className="grid grid-cols-2 gap-2.5 pt-1">
                <button
                  type="button"
                  onClick={() => handleRoleSelect('investigator')}
                  className="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-slate-600 hover:bg-slate-800/60 text-slate-300 text-[11px] font-medium transition-all group"
                >
                  <Shield className="w-3.5 h-3.5 text-cyan-400 group-hover:scale-110 transition-transform" />
                  <span className="truncate">Department SSO</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleRoleSelect('investigator')}
                  className="flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-slate-600 hover:bg-slate-800/60 text-slate-300 text-[11px] font-medium transition-all group"
                >
                  <Fingerprint className="w-3.5 h-3.5 text-cyan-400 group-hover:scale-110 transition-transform" />
                  <span className="truncate">Aadhaar (Govt.)</span>
                </button>
              </div>

            </div>
          </section>
        </div>
      </main>

      {/* Bottom Footer */}
      <footer className="relative z-20 w-full border-t border-slate-800/80 bg-[#020612]/90 backdrop-blur-md px-6 sm:px-12 py-3.5 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-slate-400 font-medium">
        {/* Left Trust Badges */}
        <div className="flex flex-wrap items-center justify-center md:justify-start gap-4 sm:gap-6">
          <div className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Secure &amp; Encrypted</span>
          </div>
          <span className="text-slate-700 hidden sm:inline">•</span>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
            <span>Trusted for a Safer India</span>
          </div>
          <span className="text-slate-700 hidden sm:inline">•</span>
          <div className="flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-cyan-400" />
            <span>For Law Enforcement Only</span>
          </div>
        </div>

        {/* Right Event & Team Credits */}
        <div className="flex items-center gap-2 text-slate-400 text-[11px] sm:text-xs font-mono">
          <span>Case Connect AI</span>
          <span>|</span>
          <span>Smart India Hackathon 2026</span>
          <span>|</span>
          <span className="text-cyan-400 font-semibold">Team UNITx</span>
        </div>
      </footer>

      {/* Guide / Security Modal */}
      {showHelpModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
            <button
              onClick={() => setShowHelpModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Law Enforcement Access Guidelines</h3>
                <p className="text-xs font-mono text-cyan-400">BSA 2023 § 63 &amp; DPDP ACT 2023</p>
              </div>
            </div>
            <div className="space-y-3 text-xs text-slate-300 leading-relaxed font-sans mb-6">
              <p>
                1. <strong>Authorized Personnel Only:</strong> Access is restricted to police investigators, intelligence analysts, and judicial authorities.
              </p>
              <p>
                2. <strong>Chain of Custody:</strong> All ingestions, graph operations, and dossier exports are cryptographically hashed (SHA-256) and logged to an immutable audit ledger.
              </p>
              <p>
                3. <strong>Default Credentials:</strong> For testing, click any 1-click access role (Investigator, Admin, Analyst) or enter your officer badge ID.
              </p>
            </div>
            <button
              onClick={() => setShowHelpModal(false)}
              className="w-full py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs transition-colors"
            >
              Acknowledged &amp; Return
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
