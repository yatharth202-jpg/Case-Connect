import React, { useState, useEffect } from 'react';
import { auditApi } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function AuditLog() {
  const { isAdmin } = useAuth();
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Chain Verification state
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await auditApi.logs(100, 0);
      setLogs(data.logs);
      setTotal(data.total);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load audit trail logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      fetchLogs();
    }
  }, [isAdmin]);

  const handleVerifyChain = async () => {
    setVerifying(true);
    try {
      const res = await auditApi.verify();
      setVerifyResult(res);
    } catch (err) {
      setVerifyResult({
        valid: false,
        error: err.response?.data?.detail || 'Verification call failed',
      });
    } finally {
      setVerifying(false);
    }
  };

  if (!isAdmin) {
    return (
      <div className="max-w-xl mx-auto px-6 py-20 text-center">
        <div className="p-6 bg-[#0b1120] border border-rose-900 rounded-lg">
          <h2 className="text-sm font-bold text-rose-400 mb-2">Restricted Access</h2>
          <p className="text-xs text-slate-400 mb-4">
            The Cryptographic Audit Trail is strictly reserved for administrative compliance officers.
          </p>
          <a
            href="/cases"
            className="inline-block px-3 py-1.5 bg-[#1e293b] text-white text-xs rounded hover:bg-[#334155]"
          >
            Back to Cases
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#1e293b] mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white tracking-tight">Cryptographic Audit Trail</h1>
            <span className="text-[10px] font-mono px-2 py-0.5 bg-emerald-950/60 text-emerald-400 border border-emerald-800 rounded">
              Section 63 BSA 2023
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Immutable SHA-256 hash-chained log ledger recording every mutating system action.
          </p>
        </div>

        <button
          onClick={handleVerifyChain}
          disabled={verifying}
          className="flex items-center gap-2 px-4 py-2 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded-md transition-colors disabled:opacity-50 shadow-sm"
        >
          {verifying ? (
            <>
              <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
              </svg>
              <span>Traversing Hash Chain...</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <span>Verify Hash Chain Integrity</span>
            </>
          )}
        </button>
      </div>

      {/* Verification Result Banner */}
      {verifyResult && (
        <div
          className={`p-4 rounded-lg border mb-6 text-xs flex items-start gap-3 ${
            verifyResult.valid
              ? 'bg-emerald-950/40 border-emerald-800 text-emerald-200'
              : 'bg-rose-950/60 border-rose-800 text-rose-200'
          }`}
        >
          <div className="font-bold text-sm shrink-0">
            {verifyResult.valid ? '[PASS]' : '[FAIL]'}
          </div>
          <div>
            <div className="font-semibold text-sm">
              {verifyResult.valid
                ? 'Cryptographic Hash Chain Verified Intact'
                : 'Hash Chain Broken / Tampering Detected'}
            </div>
            <p className="mt-1 font-mono text-[11px] opacity-90">
              {verifyResult.valid
                ? `Checked ${verifyResult.checked_rows} immutable record(s). All hashes chain sequentially from GENESIS to latest HEAD.`
                : verifyResult.error || `Integrity violation detected at row ${verifyResult.broken_at}.`}
            </p>
          </div>
        </div>
      )}

      {/* Audit Log Table */}
      <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg overflow-hidden">
        <div className="p-4 border-b border-[#1e293b] flex items-center justify-between text-xs">
          <span className="font-bold text-white uppercase tracking-wider">
            Ledger Entries ({total} Total Records)
          </span>
          <span className="text-slate-400 font-mono text-[11px]">
            Genesis Hash: <code className="text-[#38bdf8]">GENESIS</code>
          </span>
        </div>

        {loading ? (
          <div className="py-16 text-center text-xs text-slate-500">
            Loading cryptographic audit ledger...
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center text-xs text-slate-500">
            No audit records created yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#030712] text-slate-400 font-mono text-[11px] uppercase border-b border-[#1e293b]">
                <tr>
                  <th className="px-4 py-3">Timestamp (UTC)</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">User ID</th>
                  <th className="px-4 py-3">Target Object</th>
                  <th className="px-4 py-3">Previous Hash</th>
                  <th className="px-4 py-3">Current Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e293b] font-mono text-[11px]">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-[#030712]/40 transition-colors">
                    <td className="px-4 py-2.5 text-slate-300">
                      {new Date(log.timestamp).toISOString().replace('T', ' ').substring(0, 19)}
                    </td>

                    <td className="px-4 py-2.5">
                      <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-[#1e293b] text-[#38bdf8] border border-[#334155]">
                        {log.action}
                      </span>
                    </td>

                    <td className="px-4 py-2.5 text-slate-400 truncate max-w-[120px]" title={log.user_id}>
                      {log.user_id.substring(0, 8)}
                    </td>

                    <td className="px-4 py-2.5 text-slate-400">
                      {log.object_type ? `${log.object_type}:${(log.object_id || '').substring(0, 8)}` : '-'}
                    </td>

                    <td className="px-4 py-2.5 text-slate-500">
                      {log.prev_hash === 'GENESIS' ? (
                        <span className="text-amber-400 font-bold">GENESIS</span>
                      ) : (
                        <span>{log.prev_hash.substring(0, 8)}...</span>
                      )}
                    </td>

                    <td className="px-4 py-2.5 text-emerald-400 font-bold">
                      {log.hash.substring(0, 8)}...
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
