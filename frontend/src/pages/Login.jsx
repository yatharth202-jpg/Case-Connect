import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Shield,
  UserCheck,
  Lock,
  ArrowRight,
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

  // Precision Particle Telemetry Canvas (Warm Saffron / Telemetry Teal / Deep Slate)
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

    const nodeCount = 48;
    const nodes = [];

    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        radius: Math.random() * 1.8 + 0.8,
        color: i % 4 === 0 ? '#F2A33A' : (i % 3 === 0 ? '#3FB6A8' : '#1E3A5F')
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

          if (dist < 130) {
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(242, 163, 58, ${0.12 * (1 - dist / 130)})`;
            ctx.lineWidth = 0.7;
            ctx.stroke();
          }
        }
      }

      // Step and draw nodes
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

  // Fast Access Role Selector
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
    <div className="min-h-screen bg-ink text-text flex flex-col font-sans overflow-x-hidden selection:bg-accent selection:text-ink relative">
      {/* Background Subtle Canvas & Grid */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <canvas ref={canvasRef} className="w-full h-full opacity-40" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(7,9,13,0.5)_0%,#07090D_85%)]" />
      </div>

      {/* Header */}
      <header className="relative z-20 border-b border-white/[0.06] bg-ink/70 backdrop-blur-md px-6 lg:px-12 py-3.5 transition-all">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="font-serif text-2xl sm:text-3xl tracking-tight text-text">
              CaseConnect
            </span>
            <span className="text-[9px] font-mono tracking-widest text-accent uppercase border border-accent/30 bg-accent/10 px-1.5 py-0.5 rounded">
              UNITx
            </span>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono">
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full glass-sm text-muted">
              <Shield className="w-3.5 h-3.5 text-data" />
              <span>BSA 2023 § 63 COMPLIANT</span>
            </div>
            <button
              onClick={() => setShowHelpModal(true)}
              className="glass-pill px-3 py-1.5 flex items-center gap-1.5 text-muted hover:text-text transition-colors"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              <span>Guide</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-12 max-w-5xl mx-auto w-full">
        {/* Editorial Heading */}
        <div className="text-center space-y-3 mb-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass-sm text-[11px] font-mono text-accent">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            <span>OFFICER AUTHENTICATION PORTAL</span>
          </div>
          <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl text-text tracking-tight">
            Forensic Network Analysis System
          </h1>
          <p className="text-sm sm:text-base text-muted font-normal max-w-xl mx-auto leading-relaxed">
            Multi-jurisdiction CDR, banking transaction, and FIR correlation engine engineered for Indian law enforcement agencies.
          </p>
        </div>

        {/* Error notification banner */}
        {error && (
          <div className="w-full max-w-md mb-6 p-3.5 rounded-xl bg-alert/10 border border-alert/30 text-alert text-xs font-mono flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* 1-Click Fast Access Role Cards */}
        <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {/* Investigator Role */}
          <button
            onClick={() => handleRoleSelect('investigator')}
            disabled={loading}
            className="glass p-6 text-left hover:border-accent/40 transition-all duration-200 group relative flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="p-2.5 rounded-xl bg-accent/10 border border-accent/20 text-accent">
                  <UserCheck className="w-5 h-5" />
                </div>
                <span className="font-mono text-[10px] uppercase tracking-wider text-accent border border-accent/30 bg-accent/5 px-2 py-0.5 rounded-full">
                  Primary Access
                </span>
              </div>
              <h3 className="font-serif text-xl text-text group-hover:text-accent transition-colors mb-1">
                Investigator
              </h3>
              <p className="text-xs text-muted leading-relaxed">
                Full investigative docket access: CDR correlation, pass-through money tracking, and lead review.
              </p>
            </div>
            <div className="mt-5 pt-4 border-t border-white/[0.06] flex items-center justify-between text-xs font-mono text-muted group-hover:text-text">
              <span>Enter Workspace</span>
              <ArrowRight className="w-4 h-4 text-accent transform group-hover:translate-x-1 transition-transform" />
            </div>
          </button>

          {/* Admin Role */}
          <button
            onClick={() => handleRoleSelect('admin')}
            disabled={loading}
            className="glass p-6 text-left hover:border-white/30 transition-all duration-200 group relative flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="p-2.5 rounded-xl bg-white/[0.05] border border-white/[0.1] text-text">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted border border-white/10 px-2 py-0.5 rounded-full">
                  Supervisor
                </span>
              </div>
              <h3 className="font-serif text-xl text-text group-hover:text-accent transition-colors mb-1">
                Admin
              </h3>
              <p className="text-xs text-muted leading-relaxed">
                Full docket + cryptographic audit trail verification, tamper simulation, and evidence custody.
              </p>
            </div>
            <div className="mt-5 pt-4 border-t border-white/[0.06] flex items-center justify-between text-xs font-mono text-muted group-hover:text-text">
              <span>Enter Workspace</span>
              <ArrowRight className="w-4 h-4 text-accent transform group-hover:translate-x-1 transition-transform" />
            </div>
          </button>

          {/* Viewer Role */}
          <button
            onClick={() => handleRoleSelect('viewer')}
            disabled={loading}
            className="glass p-6 text-left hover:border-data/40 transition-all duration-200 group relative flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="p-2.5 rounded-xl bg-data/10 border border-data/20 text-data">
                  <Database className="w-5 h-5" />
                </div>
                <span className="font-mono text-[10px] uppercase tracking-wider text-data border border-data/30 bg-data/5 px-2 py-0.5 rounded-full">
                  Read-Only
                </span>
              </div>
              <h3 className="font-serif text-xl text-text group-hover:text-data transition-colors mb-1">
                Viewer / Court
              </h3>
              <p className="text-xs text-muted leading-relaxed">
                Judicial inspect mode: view finalized charts, Section 63 BSA reports, and verified linkage paths.
              </p>
            </div>
            <div className="mt-5 pt-4 border-t border-white/[0.06] flex items-center justify-between text-xs font-mono text-muted group-hover:text-text">
              <span>Enter Workspace</span>
              <ArrowRight className="w-4 h-4 text-data transform group-hover:translate-x-1 transition-transform" />
            </div>
          </button>
        </div>

        {/* Manual Credentials Toggle */}
        <div className="text-center">
          <button
            onClick={() => setShowManualModal(true)}
            className="text-xs font-mono text-muted hover:text-accent transition-colors inline-flex items-center gap-1.5"
          >
            <KeyRound className="w-3.5 h-3.5" />
            <span>Login with custom username & password →</span>
          </button>
        </div>
      </main>

      {/* Manual Login Modal */}
      {showManualModal && (
        <div
          className="fixed inset-0 z-50 bg-ink/85 backdrop-blur-md flex items-center justify-center p-4 animate-fadeIn"
          onClick={() => setShowManualModal(false)}
        >
          <div
            className="glass max-w-md w-full p-6 relative border border-white/[0.12]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06] mb-5">
              <h3 className="font-serif text-2xl text-text">Officer Credentials</h3>
              <button
                onClick={() => setShowManualModal(false)}
                className="text-muted hover:text-text p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleManualSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-muted uppercase tracking-wider mb-1.5">
                  Officer Username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. investigator1"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-text font-mono text-xs focus:outline-none focus:border-accent"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-muted uppercase tracking-wider mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-text font-mono text-xs focus:outline-none focus:border-accent"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 px-4 rounded-xl bg-accent text-ink font-mono text-xs font-medium uppercase tracking-wider hover:bg-accent/90 transition-all flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <div className="w-4 h-4 border-2 border-ink border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      <span>Authenticate Officer</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Operational Help Modal */}
      {showHelpModal && (
        <div
          className="fixed inset-0 z-50 bg-ink/85 backdrop-blur-md flex items-center justify-center p-4 animate-fadeIn"
          onClick={() => setShowHelpModal(false)}
        >
          <div
            className="glass max-w-lg w-full p-6 relative border border-white/[0.12]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06] mb-4">
              <h3 className="font-serif text-2xl text-text">Platform Overview</h3>
              <button
                onClick={() => setShowHelpModal(false)}
                className="text-muted hover:text-text p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-3 text-xs text-muted leading-relaxed font-sans">
              <p>
                <strong className="text-text">Role-Based Access Control:</strong> Select an access level above to begin. Investigators can ingest case files and analyze money trails; Admins have full audit and tamper simulation privileges; Viewers have read-only access for court presentation.
              </p>
              <p>
                <strong className="text-text">Statutory Compliance:</strong> All evidence ingestion and analysis generates cryptographic SHA-256 hash chains conforming to Section 63 of Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023).
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="relative z-20 border-t border-white/[0.06] py-4 px-6 text-center text-xs font-mono text-muted">
        <span>Team UNITx · Smart India Hackathon · Section 63 BSA 2023 Compliant</span>
      </footer>
    </div>
  );
}
