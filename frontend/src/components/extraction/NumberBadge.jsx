import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, Eye, Info } from 'lucide-react';
import RevealPiiModal from './RevealPiiModal';

/**
 * Objective forensic badge for extracted identifiers (Phones, Accounts, Aadhaar, PAN).
 * - "Format valid — ownership unverified"
 * - "Potential Anomaly" (with reasons tooltip)
 * - PII Masking with audited reveal action
 */
export default function NumberBadge({
  value,
  raw,
  isValid = true,
  isAnomaly = false,
  anomalyReasons = [],
  isMasked = false,
  entityId = null,
  recordId = null,
  fieldName = 'identifier',
  caseId = null,
  onRevealed = null,
}) {
  const [revealModalOpen, setRevealModalOpen] = useState(false);
  const [unmaskedValue, setUnmaskedValue] = useState(null);

  const displayValue = unmaskedValue || value || raw || '—';

  return (
    <div className="inline-flex items-center gap-1.5 flex-wrap font-mono text-xs">
      <span className="text-text font-semibold tracking-wide">
        {displayValue}
      </span>

      {/* Validation status badge */}
      {isValid ? (
        <span
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/60"
          title="Format verified against statutory schema. Historical ownership unverified without telecom/bank confirmation."
        >
          <ShieldCheck className="w-3 h-3 text-emerald-400" />
          <span>Format valid — ownership unverified</span>
        </span>
      ) : (
        <span
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-950/60 text-amber-300 border border-amber-800/60"
          title="Value format does not conform to national standard schema"
        >
          <Info className="w-3 h-3 text-amber-300" />
          <span>Unverified</span>
        </span>
      )}

      {/* Potential Anomaly badge */}
      {isAnomaly && (
        <span
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-rose-950/60 text-rose-300 border border-rose-800/60 group relative cursor-help"
        >
          <AlertTriangle className="w-3 h-3 text-rose-400" />
          <span>Potential Anomaly</span>
          {anomalyReasons && anomalyReasons.length > 0 && (
            <div className="hidden group-hover:block absolute bottom-full left-0 mb-1 z-30 p-2 rounded bg-ink-2 border border-rose-800 text-[11px] text-text min-w-[200px] shadow-xl">
              <div className="font-semibold text-rose-400 mb-1">Anomaly Indicators:</div>
              <ul className="list-disc list-inside space-y-0.5 text-muted">
                {anomalyReasons.map((r, i) => (
                  <li key={i}>{typeof r === 'string' ? r : r.explanation || r.reason_code}</li>
                ))}
              </ul>
            </div>
          )}
        </span>
      )}

      {/* Reveal Action if masked */}
      {(isMasked || (value && value.includes('XXXX'))) && !unmaskedValue && caseId && (
        <button
          onClick={() => setRevealModalOpen(true)}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-accent/15 text-accent border border-accent/40 hover:bg-accent/25 transition-colors"
          title="Reveal unmasked PII with statutory justification (creates Section 63 BSA audit log)"
        >
          <Eye className="w-3 h-3" />
          <span>Reveal</span>
        </button>
      )}

      {revealModalOpen && (
        <RevealPiiModal
          isOpen={revealModalOpen}
          onClose={() => setRevealModalOpen(false)}
          caseId={caseId}
          entityId={entityId}
          recordId={recordId}
          fieldName={fieldName}
          maskedValue={displayValue}
          onSuccess={(revealed) => {
            setUnmaskedValue(revealed);
            if (onRevealed) onRevealed(revealed);
          }}
        />
      )}
    </div>
  );
}

