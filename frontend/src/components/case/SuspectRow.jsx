import React from 'react';
import { ArrowRight, User } from 'lucide-react';

export const SuspectRow = ({ leads = [], onSelectLead, selectedLeadId }) => {
  if (!leads || leads.length === 0) {
    return null;
  }

  return (
    <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 mb-12 relative z-10">
      <div className="flex items-center justify-between mb-3 px-1">
        <span className="text-xs font-mono uppercase tracking-wider text-muted">
          Correlated High-Priority Entities ({leads.length})
        </span>
        <span className="text-[11px] font-mono text-accent">
          Click any card to inspect full dossier
        </span>
      </div>

      {/* Horizontal Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {leads.map((lead, idx) => {
          const name = lead.name || lead.display_name || `Entity ${idx + 1}`;
          const role = lead.role || lead.label || 'Correlated Lead';
          const score = Math.round(lead.score ?? lead.risk_score ?? lead.confidence ?? 60);
          const city = lead.city || lead.location || 'Linked Node';
          const isSelected = (lead.canonical_id || lead.id) === selectedLeadId;

          const initials = name
            .split(' ')
            .filter(Boolean)
            .map(p => p[0])
            .slice(0, 2)
            .join('')
            .toUpperCase() || 'ID';

          const scoreColor = score > 60 ? 'text-alert' : score >= 31 ? 'text-accent' : 'text-data';
          const barBg = score > 60 ? 'bg-alert' : score >= 31 ? 'bg-accent' : 'bg-data';

          return (
            <button
              key={lead.canonical_id || lead.id || idx}
              type="button"
              onClick={() => onSelectLead(lead)}
              className={`glass p-4 text-left transition-all duration-200 group relative border rounded-2xl flex flex-col justify-between ${
                isSelected
                  ? 'border-accent shadow-glow-accent bg-white/[0.06]'
                  : 'border-white/10 hover:border-white/25 hover:bg-white/[0.04]'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="w-9 h-9 rounded-full bg-white/[0.05] border border-white/10 flex items-center justify-center font-mono text-xs font-bold text-accent">
                    {initials}
                  </div>
                  <span className={`font-mono text-lg font-bold ${scoreColor}`}>
                    {score}%
                  </span>
                </div>

                <h4 className="font-serif text-lg text-text truncate group-hover:text-accent transition-colors">
                  {name}
                </h4>

                <p className="text-[11px] font-mono text-muted truncate mt-0.5">
                  {role} • {city}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-white/[0.06]">
                <div className="w-full bg-white/[0.06] h-1 rounded-full overflow-hidden mb-2">
                  <div className={`h-full rounded-full ${barBg}`} style={{ width: `${score}%` }} />
                </div>
                <div className="flex items-center justify-between text-[10px] font-mono text-muted group-hover:text-text">
                  <span>View Details</span>
                  <ArrowRight className="w-3 h-3 text-accent transform group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SuspectRow;
