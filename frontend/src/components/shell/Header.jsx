import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Shield, FolderOpen, LogOut, ChevronRight, User } from 'lucide-react';

export const Header = ({ onOpenSavedCases, activeSection = 'intake' }) => {
  const { user, logout } = useAuth();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 40);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToAnchor = (id) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const navItems = [
    { id: 'intake', label: 'Intake' },
    { id: 'lead', label: 'Lead' },
    { id: 'trail', label: 'Trail' },
    { id: 'network', label: 'Graph' },
    { id: 'forensics', label: 'Analytics' },
    { id: 'evidence', label: 'Evidence' },
  ];

  return (
    <header
      className={`sticky top-0 z-40 w-full transition-all duration-300 ${
        scrolled
          ? 'bg-ink/85 backdrop-blur-xl border-b border-white/[0.08] py-2.5 shadow-2xl'
          : 'bg-ink/40 backdrop-blur-md border-b border-white/[0.05] py-3.5'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between gap-4">
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => scrollToAnchor('intake')}
            className="flex items-center gap-2 group text-left focus:outline-none"
            title="Return to Intake Screen"
          >
            <span className="font-serif text-2xl sm:text-3xl tracking-tight text-text group-hover:text-accent transition-colors">
              CaseConnect
            </span>
            <span className="text-[9px] font-mono tracking-widest text-accent uppercase border border-accent/30 bg-accent/10 px-1.5 py-0.5 rounded">
              UNITx
            </span>
          </button>
        </div>

        {/* Navigation Anchors (Desktop) */}
        <nav className="hidden md:flex items-center gap-1 glass-pill px-3 py-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => scrollToAnchor(item.id)}
              className={`text-xs font-mono uppercase tracking-wider px-3 py-1.5 rounded-full transition-all ${
                activeSection === item.id
                  ? 'bg-white/10 text-text font-medium shadow-sm'
                  : 'text-muted hover:text-text hover:bg-white/[0.04]'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* Actions & Officer Status */}
        <div className="flex items-center gap-2.5 sm:gap-3">
          {/* Saved Cases Pill */}
          <button
            onClick={onOpenSavedCases}
            className="glass-pill px-3 py-1.5 flex items-center gap-2 text-xs font-mono text-muted hover:text-text hover:border-white/20 transition-all"
            title="View Stored Cases Ledger"
          >
            <FolderOpen className="w-3.5 h-3.5 text-accent" />
            <span className="hidden sm:inline">Saved Cases</span>
          </button>

          {/* Officer Identity Pill */}
          <div className="glass-pill px-3 py-1.5 hidden lg:flex items-center gap-2 text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-data animate-pulse" />
            <span className="text-text font-medium truncate max-w-[140px]">
              {user?.username || 'Officer'}
            </span>
            <span className="text-muted/80 text-[10px] uppercase">
              [{user?.role || 'Investigator'}]
            </span>
          </div>

          {/* Secure Air-Gap Badge */}
          <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.03] border border-white/[0.06] text-[10px] font-mono text-muted">
            <Shield className="w-3 h-3 text-data" />
            <span>AIR-GAPPED</span>
          </div>

          {/* Logout Action */}
          <button
            onClick={logout}
            className="p-1.5 rounded-full glass-sm text-muted hover:text-alert hover:border-alert/30 transition-colors"
            title="Sign Out Officer Session"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
