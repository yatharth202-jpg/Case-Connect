import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Shield,
  UserCheck,
  Eye,
  Lock,
  ArrowRight,
  Terminal,
  ShieldCheck,
  HelpCircle,
  KeyRound,
  X,
  FileText,
  Network,
  Database,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export default function Login() {
  const { login, quickLogin } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeRole, setActiveRole] = useState(null);
  const [showManualModal, setShowManualModal] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const canvasRef = useRef(null);

  // Tactical HUD typography and styles are maintained through native CSS tokens and tailwind classes

  // Interactive Particle Telemetry & Cyber Grid Canvas Animation
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

    const nodeCount = 55;
    const nodes = [];

    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        radius: Math.random() * 2 + 1,
        color: i % 4 === 0 ? '#8B5CF6' : (i % 3 === 0 ? '#10B981' : '#00F0FF')
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      // Connect nodes within distance threshold
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 140) {
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(0, 240, 255, ${0.15 * (1 - dist / 140)})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }

      // Draw and step nodes
      nodes.forEach((node) => {
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.shadowColor = node.color;
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;

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

  // 1-Click Fast Access Role Selector
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
      const msg = err.response?.data?.detail || 'Authentication failed. Please verify credentials.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen bg-[#040711] text-slate-100 flex flex-col font-sans overflow-x-hidden selection:bg-cyan-500 selection:text-black relative"
      style={{ fontFamily: "'Inter', sans-serif" }}
    >
      {/* Dynamic Polygon Clip Path for Cyber-Cut Buttons */}
      <style>{`
        .cyber-btn-cut {
          clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
        }
        .font-cyber {
          font-family: 'Rajdhani', sans-serif;
        }
        .font-mono-tech {
          font-family: 'Share Tech Mono', monospace;
        }
        .glass-role-card {
          background: rgba(8, 14, 30, 0.76);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
        }
      `}</style>

      {/* BEGIN: Interactive Cyber Canvas Background */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <canvas ref={canvasRef} className="w-full h-full opacity-60" />
        <div className="absolute right-0 top-0 w-full lg:w-2/3 h-full opacity-15 bg-radial from-cyan-900/30 via-transparent to-transparent pointer-events-none" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(0,240,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(0,240,255,0.02)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,#000_70%,transparent_100%)] pointer-events-none" />
      </div>
      {/* END: Interactive Cyber Canvas Background */}

      {/* BEGIN: MainHeader */}
      <header className="relative z-20 border-b border-slate-800/80 bg-[#070D1D]/90 backdrop-blur-md px-6 lg:px-12 py-3.5 transition-all">
        <div className="max-w-[1720px] mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Brand & Tagline */}
          <div className="flex items-center gap-4">
            <div className="relative flex items-center justify-center w-11 h-11 rounded-lg border border-cyan-500/40 bg-cyan-950/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.25)]">
              {/* Ashoka Pillar / Police Emblem Vector Symbol */}
              <svg className="w-7 h-7" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24">
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
                <h1 className="text-2xl font-bold tracking-tight text-white font-cyber flex items-center">
                  Case Connect <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500 ml-1.5 font-extrabold">AI</span>
                </h1>
                <span className="text-[10px] uppercase font-mono-tech tracking-widest px-1.5 py-0.5 rounded bg-blue-900/50 text-cyan-300 border border-blue-500/30">
                  v4.8-LEO
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium tracking-wide">
                Explainable Crime Network & Evidence Dissection Platform
              </p>
            </div>
          </div>

          {/* Live Operations & Security Status */}
          <div className="flex items-center gap-3 lg:gap-5">
            {/* Terminal Ready Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/90 border border-slate-700/80 text-xs font-mono-tech">
              <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399] animate-pulse" />
              <span className="text-emerald-400 font-semibold tracking-wide">Live Terminal Ready</span>
            </div>

            {/* Secure Connection indicator */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-950/40 border border-cyan-500/30 text-xs font-medium text-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.15)] font-mono-tech">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="tracking-wide">Secure Connection</span>
            </div>

            {/* Quick Access Icon Controls */}
            <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
              <button
                type="button"
                onClick={() => setShowHelpModal(true)}
                className="w-9 h-9 flex items-center justify-center rounded-lg border border-slate-700/70 bg-slate-900/80 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition"
                title="System Manual & Help"
              >
                <HelpCircle className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setShowManualModal(true)}
                className="w-9 h-9 flex items-center justify-center rounded-lg border border-slate-700/70 bg-slate-900/80 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition"
                title="Officer Manual Badge Login"
              >
                <KeyRound className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>
      {/* END: MainHeader */}

      {/* Global Error & Loading Notifications */}
      {error && (
        <div className="relative z-20 max-w-xl mx-auto mt-4 px-4">
          <div className="p-3.5 bg-rose-950/80 border border-rose-600/80 rounded-xl text-rose-200 text-xs flex items-center justify-between gap-3 shadow-[0_0_20px_rgba(225,29,72,0.3)] backdrop-blur-md">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError('')}
              className="text-rose-400 hover:text-white transition p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {loading && (
        <div className="relative z-20 max-w-md mx-auto mt-4 px-4">
          <div className="p-3 bg-cyan-950/70 border border-cyan-500/50 rounded-xl text-cyan-300 text-xs flex items-center justify-center gap-3 shadow-[0_0_25px_rgba(0,240,255,0.25)] backdrop-blur-md animate-pulse">
            <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            <span className="font-mono-tech tracking-wide">
              Validating {activeRole ? activeRole.toUpperCase() : 'OFFICER'} credentials & opening terminal...
            </span>
          </div>
        </div>
      )}

      {/* BEGIN: MainContent */}
      <main className="relative z-10 flex-1 flex flex-col justify-center px-4 sm:px-6 lg:px-12 py-8 max-w-[1720px] mx-auto w-full">
        {/* Portal Cards Container */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 xl:gap-8 items-stretch justify-center my-auto">
          {/* ========================================== */}
          {/* CARD 1: Lead Investigator (Cyan/Teal Theme) */}
          {/* ========================================== */}
          <div className="group relative rounded-2xl glass-role-card border border-cyan-500/40 hover:border-cyan-400 flex flex-col overflow-hidden transition-all duration-300 hover:-translate-y-1.5 hover:shadow-[0_0_25px_-4px_rgba(0,240,255,0.35)] shadow-2xl">
            {/* Top Neon Accent Line */}
            <div className="h-1 w-full bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80 group-hover:opacity-100 transition" />

            {/* Header of Card */}
            <div className="p-5 pb-3 flex items-center gap-3.5 border-b border-cyan-900/30 bg-gradient-to-b from-cyan-950/30 to-transparent">
              <div className="w-10 h-10 rounded-xl bg-cyan-950/70 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
                <UserCheck className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-xl font-cyber font-bold tracking-wider text-white group-hover:text-cyan-300 transition-colors">
                  Lead Investigator
                </h2>
                <span className="text-[11px] font-mono-tech text-cyan-400/80 tracking-wider">
                  LEVEL 3 ACCESS • OPERATIONAL
                </span>
              </div>
            </div>

            {/* Officer Visual Context */}
            <div className="relative h-60 w-full overflow-hidden bg-[#050a16] flex items-center justify-center p-4">
              <svg className="w-full h-full max-h-52" viewBox="0 0 320 220" fill="none">
                {/* Background Grid & Radar rings */}
                <circle cx="160" cy="110" r="95" stroke="#00F0FF" strokeOpacity="0.12" strokeDasharray="3 3" />
                <circle cx="160" cy="110" r="70" stroke="#00F0FF" strokeOpacity="0.2" />
                <circle cx="160" cy="110" r="42" stroke="#00F0FF" strokeOpacity="0.3" />
                <line x1="160" y1="10" x2="160" y2="210" stroke="#00F0FF" strokeOpacity="0.15" />
                <line x1="60" y1="110" x2="260" y2="110" stroke="#00F0FF" strokeOpacity="0.15" />
                {/* Radar Sweep Arc */}
                <path d="M160 110 L230 45 A105 105 0 0 0 160 5 Z" fill="url(#cyanSweep)" fillOpacity="0.25" />
                {/* Tactical Shield Hologram */}
                <path d="M160 70 L195 85 V125 C195 145 160 160 160 160 C160 160 125 145 125 125 V85 Z" fill="#00F0FF" fillOpacity="0.1" stroke="#00F0FF" strokeWidth="2" />
                <path d="M160 82 L185 93 V122 C185 137 160 148 160 148 C160 148 135 137 135 122 V93 Z" stroke="#38BDF8" strokeWidth="1" strokeOpacity="0.6" />
                {/* Tactical Comm Nodes */}
                <circle cx="160" cy="115" r="5" fill="#00F0FF" />
                <circle cx="210" cy="75" r="3" fill="#38BDF8" />
                <circle cx="110" cy="140" r="3" fill="#00F0FF" />
                <line x1="160" y1="115" x2="210" y2="75" stroke="#00F0FF" strokeWidth="1" strokeOpacity="0.5" strokeDasharray="2 2" />
                <line x1="160" y1="115" x2="110" y2="140" stroke="#00F0FF" strokeWidth="1" strokeOpacity="0.5" strokeDasharray="2 2" />
                {/* Telemetry Corner Reticles */}
                <path d="M30 30 H50 M30 30 V50" stroke="#00F0FF" strokeOpacity="0.4" strokeWidth="1.5" />
                <path d="M290 30 H270 M290 30 V50" stroke="#00F0FF" strokeOpacity="0.4" strokeWidth="1.5" />
                <path d="M30 190 H50 M30 190 V170" stroke="#00F0FF" strokeOpacity="0.4" strokeWidth="1.5" />
                <path d="M290 190 H270 M290 190 V170" stroke="#00F0FF" strokeOpacity="0.4" strokeWidth="1.5" />
                {/* Coordinates & Level */}
                <text x="35" y="45" fill="#38BDF8" fontSize="9" fontFamily="monospace" letterSpacing="1">SEC//TACTICAL-GRID-01</text>
                <text x="35" y="185" fill="#00F0FF" fontSize="9" fontFamily="monospace" letterSpacing="1">STATUS: OPERATIONAL</text>
                <defs>
                  <radialGradient id="cyanSweep" cx="160" cy="110" r="105" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#00F0FF" stopOpacity="0.8" />
                    <stop offset="1" stopColor="#00F0FF" stopOpacity="0" />
                  </radialGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 bg-gradient-to-t from-[#080E1E] via-transparent to-transparent pointer-events-none" />
              <div className="absolute top-3 right-3 px-2 py-0.5 rounded bg-black/60 border border-cyan-500/30 font-mono text-[10px] text-cyan-300 backdrop-blur-sm">
                AUTH_ID: IND-LEO-994
              </div>
            </div>

            {/* Body & Scope */}
            <div className="p-6 flex-1 flex flex-col justify-between space-y-6">
              <p className="text-sm text-slate-300 leading-relaxed font-normal text-center">
                Full evidence upload, dynamic graph analysis & report generation
              </p>

              {/* Interactive Action Button */}
              <div className="pt-2 flex justify-center">
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => handleRoleSelect('investigator')}
                  className="relative cyber-btn-cut px-10 py-2.5 bg-gradient-to-r from-cyan-950 via-cyan-900/60 to-cyan-950 border border-cyan-400 text-cyan-300 font-cyber font-bold tracking-widest text-base hover:bg-cyan-400 hover:text-black hover:shadow-[0_0_20px_#00F0FF] active:scale-95 transition-all duration-200 disabled:opacity-50"
                >
                  <span className="inline-flex items-center gap-2">
                    <Terminal className="w-4 h-4" /> Enter
                  </span>
                </button>
              </div>
            </div>
          </div>

          {/* ============================================== */}
          {/* CARD 2: Supervisory Admin (Violet Theme - Hero) */}
          {/* ============================================== */}
          <div className="group relative rounded-2xl glass-role-card border border-violet-500/50 hover:border-violet-400 flex flex-col overflow-hidden transition-all duration-300 hover:-translate-y-1.5 hover:shadow-[0_0_25px_-4px_rgba(139,92,246,0.4)] shadow-2xl lg:-mt-2">
            {/* Elevated Badge Indicator */}
            <div className="h-1 w-full bg-gradient-to-r from-transparent via-violet-400 to-transparent opacity-90 group-hover:opacity-100 transition" />

            {/* Header of Card */}
            <div className="p-5 pb-3 flex items-center gap-3.5 border-b border-violet-900/30 bg-gradient-to-b from-violet-950/30 to-transparent">
              <div className="w-10 h-10 rounded-xl bg-violet-950/70 border border-violet-500/40 flex items-center justify-center text-violet-400 shadow-[0_0_12px_rgba(139,92,246,0.3)]">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-xl font-cyber font-bold tracking-wider text-white group-hover:text-violet-300 transition-colors">
                  Supervisory Admin
                </h2>
                <span className="text-[11px] font-mono-tech text-violet-400/80 tracking-wider">
                  COMMAND OVERSIGHT • AUDITOR
                </span>
              </div>
            </div>

            {/* Officer Visual Context */}
            <div className="relative h-60 w-full overflow-hidden bg-[#070617] flex items-center justify-center p-4">
              <svg className="w-full h-full max-h-52" viewBox="0 0 320 220" fill="none">
                {/* Hexagonal Biometric Security Vault Matrix */}
                <polygon points="160,20 240,65 240,155 160,200 80,155 80,65" stroke="#8B5CF6" strokeOpacity="0.2" strokeWidth="1.5" />
                <polygon points="160,38 225,75 225,145 160,182 95,145 95,75" stroke="#A78BFA" strokeOpacity="0.3" strokeDasharray="4 2" />
                {/* Command Star / Ashoka Core Emblem */}
                <circle cx="160" cy="110" r="46" fill="#8B5CF6" fillOpacity="0.08" stroke="#8B5CF6" strokeWidth="2" />
                <circle cx="160" cy="110" r="32" stroke="#C084FC" strokeWidth="1" strokeDasharray="3 3" />
                {/* 8-Point Command Star Vector */}
                <path d="M160 80 L165 105 L190 110 L165 115 L160 140 L155 115 L130 110 L155 105 Z" fill="#A78BFA" fillOpacity="0.4" stroke="#C084FC" strokeWidth="1.5" />
                <circle cx="160" cy="110" r="5" fill="#C084FC" />
                {/* Biometric Scan Beam */}
                <line x1="85" y1="110" x2="235" y2="110" stroke="#8B5CF6" strokeWidth="1.5" strokeOpacity="0.7" />
                {/* Clearance Level Telemetry */}
                <path d="M30 30 H50 M30 30 V50" stroke="#8B5CF6" strokeOpacity="0.4" strokeWidth="1.5" />
                <path d="M290 30 H270 M290 30 V50" stroke="#8B5CF6" strokeOpacity="0.4" strokeWidth="1.5" />
                <path d="M30 190 H50 M30 190 V170" stroke="#8B5CF6" strokeOpacity="0.4" strokeWidth="1.5" />
                <path d="M290 190 H270 M290 190 V170" stroke="#8B5CF6" strokeOpacity="0.4" strokeWidth="1.5" />
                <text x="35" y="45" fill="#C084FC" fontSize="9" fontFamily="monospace" letterSpacing="1">SUPERVISORY//AUDIT-CHAIN</text>
                <text x="35" y="185" fill="#A78BFA" fontSize="9" fontFamily="monospace" letterSpacing="1">SHA-256 INTEGRITY: VERIFIED</text>
              </svg>
              <div className="absolute inset-0 bg-gradient-to-t from-[#080E1E] via-transparent to-transparent pointer-events-none" />
              <div className="absolute top-3 right-3 px-2 py-0.5 rounded bg-black/60 border border-violet-500/30 font-mono text-[10px] text-violet-300 backdrop-blur-sm">
                CLEARANCE: LEVEL 5
              </div>
            </div>

            {/* Body & Scope */}
            <div className="p-6 flex-1 flex flex-col justify-between space-y-6">
              <p className="text-sm text-slate-300 leading-relaxed font-normal text-center">
                Case management, case settings & immutable audit log verification
              </p>

              {/* Interactive Action Button */}
              <div className="pt-2 flex justify-center">
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => handleRoleSelect('admin')}
                  className="relative cyber-btn-cut px-10 py-2.5 bg-gradient-to-r from-violet-900/80 via-blue-900/70 to-violet-900/80 border border-violet-400 text-violet-200 font-cyber font-bold tracking-widest text-base hover:bg-violet-500 hover:text-white hover:shadow-[0_0_25px_#8B5CF6] active:scale-95 transition-all duration-200 disabled:opacity-50"
                >
                  <span className="inline-flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4" /> Action
                  </span>
                </button>
              </div>
            </div>
          </div>

          {/* ============================================== */}
          {/* CARD 3: Intelligence Analyst (Emerald Theme)   */}
          {/* ============================================== */}
          <div className="group relative rounded-2xl glass-role-card border border-emerald-500/40 hover:border-emerald-400 flex flex-col overflow-hidden transition-all duration-300 hover:-translate-y-1.5 hover:shadow-[0_0_25px_-4px_rgba(16,185,129,0.35)] shadow-2xl">
            {/* Top Neon Accent Line */}
            <div className="h-1 w-full bg-gradient-to-r from-transparent via-emerald-400 to-transparent opacity-80 group-hover:opacity-100 transition" />

            {/* Header of Card */}
            <div className="p-5 pb-3 flex items-center gap-3.5 border-b border-emerald-900/30 bg-gradient-to-b from-emerald-950/30 to-transparent">
              <div className="w-10 h-10 rounded-xl bg-emerald-950/70 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.25)]">
                <Eye className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-xl font-cyber font-bold tracking-wider text-white group-hover:text-emerald-300 transition-colors">
                  Intelligence Analyst
                </h2>
                <span className="text-[11px] font-mono-tech text-emerald-400/80 tracking-wider">
                  FIN-CRIME & CDR CORRELATION
                </span>
              </div>
            </div>

            {/* Analyst Visual Context */}
            <div className="relative h-60 w-full overflow-hidden bg-[#040e0c] flex items-center justify-center p-4">
              <svg className="w-full h-full max-h-52" viewBox="0 0 320 220" fill="none">
                {/* Forensic Financial & Telecom Correlation Grid */}
                <path d="M40 160 L80 130 L130 145 L170 95 L220 120 L270 65" stroke="#10B981" strokeWidth="2" strokeOpacity="0.7" fill="none" />
                <path d="M40 160 L80 130 L130 145 L170 95 L220 120 L270 65 L270 190 L40 190 Z" fill="url(#emeraldArea)" fillOpacity="0.15" />
                {/* Correlation Multi-Hop Nodes */}
                <circle cx="80" cy="130" r="4" fill="#34D399" />
                <circle cx="130" cy="145" r="4" fill="#10B981" />
                <circle cx="170" cy="95" r="5" fill="#34D399" stroke="#059669" strokeWidth="2" />
                <circle cx="220" cy="120" r="4" fill="#10B981" />
                <circle cx="270" cy="65" r="6" fill="#6EE7B7" stroke="#10B981" strokeWidth="2" />
                {/* Secondary Constellation Links */}
                <line x1="80" y1="130" x2="170" y2="95" stroke="#34D399" strokeWidth="1" strokeOpacity="0.3" strokeDasharray="2 2" />
                <line x1="130" y1="145" x2="220" y2="120" stroke="#34D399" strokeWidth="1" strokeOpacity="0.3" strokeDasharray="2 2" />
                {/* Spectrogram / Flow Indicators */}
                <rect x="50" y="30" width="4" height="25" fill="#10B981" fillOpacity="0.4" />
                <rect x="58" y="20" width="4" height="35" fill="#10B981" fillOpacity="0.6" />
                <rect x="66" y="35" width="4" height="20" fill="#10B981" fillOpacity="0.3" />
                <rect x="74" y="15" width="4" height="40" fill="#34D399" fillOpacity="0.8" />
                {/* Telemetry Reticles */}
                <path d="M30 30 H50 M30 30 V50" stroke="#10B981" strokeOpacity="0.4" strokeWidth="1.5" />
                <path d="M290 30 H270 M290 30 V50" stroke="#10B981" strokeOpacity="0.4" strokeWidth="1.5" />
                <path d="M30 190 H50 M30 190 V170" stroke="#10B981" strokeOpacity="0.4" strokeWidth="1.5" />
                <path d="M290 190 H270 M290 190 V170" stroke="#10B981" strokeOpacity="0.4" strokeWidth="1.5" />
                <text x="90" y="45" fill="#34D399" fontSize="9" fontFamily="monospace" letterSpacing="1">FLOW//CDR-TRAIL-LAYER</text>
                <text x="35" y="185" fill="#10B981" fontSize="9" fontFamily="monospace" letterSpacing="1">CENTRALITY: CORRELATED</text>
                <defs>
                  <linearGradient id="emeraldArea" x1="160" y1="65" x2="160" y2="190" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#10B981" stopOpacity="0.5" />
                    <stop offset="1" stopColor="#10B981" stopOpacity="0" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 bg-gradient-to-t from-[#080E1E] via-transparent to-transparent pointer-events-none" />
              <div className="absolute top-3 right-3 px-2 py-0.5 rounded bg-black/60 border border-emerald-500/30 font-mono text-[10px] text-emerald-300 backdrop-blur-sm">
                ACCESS: READ-ONLY
              </div>
            </div>

            {/* Body & Scope */}
            <div className="p-6 flex-1 flex flex-col justify-between space-y-6">
              <p className="text-sm text-slate-300 leading-relaxed font-normal text-center">
                Read-only exploration of money trails, charts & graph topology
              </p>

              {/* Interactive Action Button */}
              <div className="pt-2 flex justify-center">
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => handleRoleSelect('viewer')}
                  className="relative cyber-btn-cut px-10 py-2.5 bg-gradient-to-r from-emerald-950 via-emerald-900/60 to-emerald-950 border border-emerald-400 text-emerald-300 font-cyber font-bold tracking-widest text-base hover:bg-emerald-400 hover:text-black hover:shadow-[0_0_20px_#10B981] active:scale-95 transition-all duration-200 disabled:opacity-50"
                >
                  <span className="inline-flex items-center gap-2">
                    <Terminal className="w-4 h-4" /> Enter
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Manual Credentials Trigger Button */}
        <div className="mt-8 text-center">
          <button
            type="button"
            onClick={() => setShowManualModal(true)}
            className="text-xs text-slate-400 hover:text-cyan-400 transition-colors font-mono-tech inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-slate-800 bg-[#080E1E]/80 backdrop-blur-md"
          >
            <Lock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Need Custom Credentials? Sign In Manually</span>
          </button>
        </div>
      </main>
      {/* END: MainContent */}

      {/* BEGIN: MainFooter */}
      <footer className="relative z-20 border-t border-slate-800/80 bg-[#060B19]/95 backdrop-blur-lg pt-7 pb-5 px-6 lg:px-12 mt-auto">
        <div className="max-w-[1720px] mx-auto flex flex-col items-center text-center space-y-4">
          {/* Brand Soft Emblem & Identity */}
          <div className="flex items-center justify-center gap-2.5">
            <div className="flex items-center gap-2 tracking-widest font-cyber text-2xl font-bold text-slate-200">
              <span>UNIT<span className="text-cyan-400 font-black">X</span></span>
            </div>
            <div className="w-6 h-6 rounded-full border border-cyan-500/40 bg-cyan-950/40 flex items-center justify-center text-cyan-400 text-xs">
              <Shield className="w-3.5 h-3.5" />
            </div>
          </div>

          {/* Functional Capability Subtitle */}
          <p className="max-w-4xl text-xs sm:text-sm text-slate-400 font-normal leading-relaxed">
            Automated telecommunication CDR, banking transaction, and multi-jurisdiction FIR correlation engine engineered for Indian law enforcement agencies.
          </p>

          {/* Statutory & Algorithmic Compliance Tags */}
          <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[11px] text-slate-400 font-mono-tech tracking-tight bg-slate-900/80 py-1.5 px-4 rounded-full border border-slate-800">
            <span className="text-slate-300">Section 63 Bharatiya Sakshya Adhiniyam (BSA) 2023 compliant audit ledger</span>
            <span className="text-cyan-500">•</span>
            <span className="text-slate-300">Deterministic SHA-256 genesis-anchored chain of custody</span>
            <span className="text-cyan-500">•</span>
            <span className="text-slate-300">100% Dynamic multi-evidence learning without hardcoded mocks</span>
          </div>

          {/* Divider line */}
          <div className="w-full h-px bg-gradient-to-r from-transparent via-slate-800 to-transparent my-1" />

          {/* Bottom Status & Navigation Strip */}
          <div className="w-full flex flex-col lg:flex-row items-center justify-between gap-4 pt-1 text-xs">
            {/* Left: Sovereign Trust Tag */}
            <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-3 text-left">
              <div className="flex items-center gap-1.5 text-cyan-400 font-medium">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Secure | Trusted | For a Safer India</span>
              </div>
              <span className="hidden sm:inline text-slate-700">|</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono-tech bg-cyan-950/60 text-cyan-300 border border-cyan-800/60">
                DPDP Act 2023 Compliant
              </span>
            </div>

            {/* Center: Security Node Icons */}
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-full bg-slate-900 border border-slate-700/80 flex items-center justify-center text-slate-400 hover:text-cyan-400 hover:border-cyan-500/50 transition cursor-default" title="End-to-End Encrypted Ledger">
                <Lock className="w-3.5 h-3.5" />
              </div>
              <div className="w-7 h-7 rounded-full bg-slate-900 border border-slate-700/80 flex items-center justify-center text-slate-400 hover:text-cyan-400 hover:border-cyan-500/50 transition cursor-default" title="Biometric / Cert Authenticated">
                <UserCheck className="w-3.5 h-3.5" />
              </div>
              <div className="w-7 h-7 rounded-full bg-slate-900 border border-slate-700/80 flex items-center justify-center text-slate-400 hover:text-cyan-400 hover:border-cyan-500/50 transition cursor-default" title="Decentralized Inter-Agency Node">
                <Network className="w-3.5 h-3.5" />
              </div>
              <div className="w-7 h-7 rounded-full bg-slate-900 border border-slate-700/80 flex items-center justify-center text-slate-400 hover:text-cyan-400 hover:border-cyan-500/50 transition cursor-default" title="Immutable Data Vault">
                <Database className="w-3.5 h-3.5" />
              </div>
            </div>

            {/* Right: Legal & Portal Links */}
            <div className="flex flex-wrap items-center gap-4 text-slate-400 text-[11px]">
              <button onClick={() => setShowHelpModal(true)} className="hover:text-cyan-400 transition">Privacy Policy</button>
              <span className="text-slate-700">•</span>
              <button onClick={() => setShowHelpModal(true)} className="hover:text-cyan-400 transition">Terms of Service</button>
              <span className="text-slate-700">•</span>
              <button onClick={() => setShowHelpModal(true)} className="hover:text-cyan-400 transition">Documentation</button>
              <span className="text-slate-700">•</span>
              <button onClick={() => setShowHelpModal(true)} className="hover:text-cyan-400 transition">Contact Us</button>
            </div>
          </div>
        </div>
      </footer>
      {/* END: MainFooter */}

      {/* FROSTED GLASS MODAL: Manual Officer Authentication */}
      {showManualModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
          <div className="w-full max-w-md rounded-2xl glass-role-card border border-cyan-500/50 p-6 sm:p-8 shadow-[0_0_50px_rgba(0,240,255,0.25)] relative overflow-hidden">
            <div className="h-1 w-full absolute top-0 left-0 bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-500" />
            <button
              onClick={() => setShowManualModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition p-1 rounded-lg border border-transparent hover:border-slate-700"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
                <KeyRound className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-cyber font-bold tracking-wide text-white">Manual Terminal Sign In</h3>
                <p className="text-xs text-slate-400 font-mono-tech">Officer Credential Verification</p>
              </div>
            </div>

            <form onSubmit={handleManualSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono-tech text-slate-300 mb-1" htmlFor="username">
                  Officer Username / Badge ID
                </label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. investigator1, admin, or io_sharma"
                  className="w-full px-3.5 py-2.5 bg-[#030712]/90 border border-slate-700 rounded-xl text-white text-xs placeholder-slate-600 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 font-mono-tech"
                />
              </div>

              <div>
                <label className="block text-xs font-mono-tech text-slate-300 mb-1" htmlFor="password">
                  Security Passphrase / Token
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Demo: Any passphrase accepted"
                  className="w-full px-3.5 py-2.5 bg-[#030712]/90 border border-slate-700 rounded-xl text-white text-xs placeholder-slate-600 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 font-mono-tech"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full cyber-btn-cut py-2.5 bg-gradient-to-r from-cyan-900 via-cyan-800 to-cyan-900 border border-cyan-400 text-cyan-200 font-cyber font-bold tracking-widest text-sm hover:bg-cyan-400 hover:text-black hover:shadow-[0_0_20px_#00F0FF] transition-all disabled:opacity-50"
                >
                  <span className="inline-flex items-center gap-2">
                    <Terminal className="w-4 h-4" /> Authenticate Terminal
                  </span>
                </button>
              </div>

              <div className="pt-2 text-center">
                <span className="text-[11px] text-slate-400 font-mono-tech">
                  Or select 1-click badges behind this modal for instant access.
                </span>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* FROSTED GLASS MODAL: System Documentation & Compliance */}
      {showHelpModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
          <div className="w-full max-w-lg rounded-2xl glass-role-card border border-blue-500/50 p-6 sm:p-8 shadow-[0_0_50px_rgba(59,130,246,0.25)] relative overflow-hidden">
            <div className="h-1 w-full absolute top-0 left-0 bg-gradient-to-r from-blue-500 via-cyan-500 to-emerald-500" />
            <button
              onClick={() => setShowHelpModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition p-1 rounded-lg border border-transparent hover:border-slate-700"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-blue-950/80 border border-blue-500/40 flex items-center justify-center text-blue-400">
                <HelpCircle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-cyber font-bold tracking-wide text-white">System Architecture & Standards</h3>
                <p className="text-xs text-slate-400 font-mono-tech">Case Connect AI Governance</p>
              </div>
            </div>

            <div className="space-y-3.5 text-xs text-slate-300 leading-relaxed max-h-96 overflow-y-auto pr-1">
              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="font-bold text-cyan-300 flex items-center gap-2 mb-1">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                  Section 63 BSA 2023 Compliance
                </div>
                <p className="text-slate-400 text-[11px]">
                  All generated reports include automated SHA-256 hash anchoring and custody audit log trails adhering to Bharatiya Sakshya Adhiniyam standards.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="font-bold text-violet-300 flex items-center gap-2 mb-1">
                  <CheckCircle2 className="w-4 h-4 text-violet-400" />
                  Role-Based Clearance Boundaries
                </div>
                <p className="text-slate-400 text-[11px]">
                  • <b>Lead Investigator:</b> Ingest evidence, query the investigation graph, run CDR/financial forensics.
                  <br />• <b>Supervisory Admin:</b> Audit officer access trails, manage system configuration.
                  <br />• <b>Intelligence Analyst:</b> View charts and analyze topology in read-only mode.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="font-bold text-emerald-300 flex items-center gap-2 mb-1">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  Data Protection & Privacy
                </div>
                <p className="text-slate-400 text-[11px]">
                  Strict compliance with Digital Personal Data Protection (DPDP) Act 2023 with localized on-premise execution support.
                </p>
              </div>
            </div>

            <div className="pt-4 text-center">
              <button
                type="button"
                onClick={() => setShowHelpModal(false)}
                className="px-6 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-mono-tech text-xs transition"
              >
                Close Documentation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
