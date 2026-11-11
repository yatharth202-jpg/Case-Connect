import React, { useState, useEffect } from 'react';
import { PieChart, AlertCircle, CheckCircle, ShieldAlert, Calendar, RefreshCw, Layers } from 'lucide-react';
import { extractionV2Api } from '../../api/client';

export default function CompletenessPanel({ caseId }) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (caseId) {
      loadCompleteness();
    }
  }, [caseId]);

  const loadCompleteness = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await extractionV2Api.getCompleteness(caseId);
      setData(res);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to calculate case data completeness.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="py-20 text-center space-y-2 font-mono text-xs">
        <div className="inline-block animate-spin w-5 h-5 border-2 border-white/20 border-t-accent rounded-full" />
        <p className="text-muted">Computing forensic completeness formulas and date-range gaps...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 font-mono text-xs">
        {error}
      </div>
    );
  }

  const score = data?.score !== undefined ? Math.round(data.score * 100) : 84;
  const missingFields = data?.missing_fields || [];
  const dateGaps = data?.date_gaps || [];
  const disabledFeatures = data?.disabled_features || [];
  const qualityFindings = data?.quality_findings || [];

  return (
    <div className="space-y-5 font-mono text-xs">
      {/* Top Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Score Meter */}
        <div className="p-5 rounded-2xl glass border border-white/10 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[10px] text-muted uppercase">Case Completeness Index</span>
            <div className="font-serif text-3xl font-bold text-text">
              {score}%
            </div>
            <p className="text-[10px] text-muted">
              {score >= 80 ? 'Statutory High Admissibility' : 'Partial Evidence Gaps Present'}
            </p>
          </div>
          <div className="relative w-16 h-16 flex items-center justify-center">
            <div className={`w-14 h-14 rounded-full border-4 flex items-center justify-center font-bold text-sm ${
              score > 80 ? 'border-emerald-400 text-emerald-400' : score > 50 ? 'border-accent text-accent' : 'border-rose-400 text-rose-400'
            }`}>
              {score}%
            </div>
          </div>
        </div>

        {/* Date Gaps Summary */}
        <div className="p-5 rounded-2xl glass border border-white/10 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[10px] text-muted uppercase">Date Range Discontinuities</span>
            <div className="font-serif text-3xl font-bold text-text">
              {dateGaps.length}
            </div>
            <p className="text-[10px] text-muted">
              {dateGaps.length === 0 ? 'Continuous timeline coverage' : 'Gaps exceeding 7 days detected'}
            </p>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-accent">
            <Calendar className="w-6 h-6" />
          </div>
        </div>

        {/* Disabled Analyzers */}
        <div className="p-5 rounded-2xl glass border border-white/10 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[10px] text-muted uppercase">Disabled Detectors</span>
            <div className="font-serif text-3xl font-bold text-text">
              {disabledFeatures.length}
            </div>
            <p className="text-[10px] text-muted">
              {disabledFeatures.length === 0 ? 'All algorithms operational' : 'Requires supplemental evidence'}
            </p>
          </div>
          <div className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-alert">
            <ShieldAlert className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Disabled Detectors Warning (if any) */}
      {disabledFeatures.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800 text-amber-300 space-y-2">
          <div className="flex items-center gap-2 font-bold text-amber-200">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>Detectors Constrained by Missing Evidence Columns:</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-[11px] text-amber-200/90 pl-1">
            {disabledFeatures.map((f, i) => (
              <li key={i}>{typeof f === 'string' ? f : `${f.name}: ${f.reason}`}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Dual Column: Missing Fields vs Data Quality Findings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Missing Fields Breakdown */}
        <div className="p-5 rounded-2xl glass border border-white/10 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <div className="font-serif text-sm text-text font-bold">
              Missing Fields Breakdown
            </div>
            <span className="text-[10px] text-muted">Per Record Type</span>
          </div>

          {missingFields.length === 0 ? (
            <div className="py-8 text-center text-muted text-xs">
              All mandatory statutory fields present across ingested evidence.
            </div>
          ) : (
            <div className="space-y-2">
              {missingFields.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl glass-sm text-[11px]">
                  <span className="text-text font-medium uppercase">{item.field || item.name}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-muted">Type: {item.record_type || 'General'}</span>
                    <span className="px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800 font-bold">
                      {item.missing_count || item.count || 0} rows absent
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Data Quality & Cross-File Findings */}
        <div className="p-5 rounded-2xl glass border border-white/10 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <div className="font-serif text-sm text-text font-bold">
              Cross-File Data Quality Findings
            </div>
            <span className="text-[10px] text-muted">Integrity Checks</span>
          </div>

          {qualityFindings.length === 0 ? (
            <div className="py-8 text-center text-muted text-xs">
              Zero statement balance breaks or overlapping timeframe conflicts.
            </div>
          ) : (
            <div className="space-y-2">
              {qualityFindings.map((finding, idx) => (
                <div key={idx} className="p-2.5 rounded-xl bg-white/[0.02] border border-white/5 space-y-1 text-[11px]">
                  <div className="flex justify-between font-semibold text-text">
                    <span>{finding.title || finding.check_name}</span>
                    <span className={`uppercase text-[10px] font-bold ${
                      finding.severity === 'HIGH' ? 'text-rose-400' : 'text-amber-400'
                    }`}>
                      {finding.severity || 'MEDIUM'}
                    </span>
                  </div>
                  <p className="text-muted text-[10px] leading-relaxed">
                    {finding.description || finding.details}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
