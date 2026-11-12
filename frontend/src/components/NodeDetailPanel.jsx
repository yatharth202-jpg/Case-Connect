import React, { useState, useEffect } from 'react';
import {
  X,
  Layers,
  Phone,
  Landmark,
  User,
  Globe,
  Smartphone,
  FileText,
  Calendar,
  DollarSign,
  ChevronLeft,
  ChevronRight,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { graphApi } from '../api/client';

export default function NodeDetailPanel({
  caseId,
  nodeId,
  onClose,
  onExpandNode,
}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [typeFilter, setTypeFilter] = useState('');

  const fetchNeighbours = async (targetPage = 1, currentFilter = typeFilter) => {
    if (!caseId || !nodeId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await graphApi.getNodeNeighbours(caseId, nodeId, {
        page: targetPage,
        page_size: pageSize,
        type_filter: currentFilter || undefined,
      });
      setData(res);
      setPage(res.page || 1);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load node neighbours');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
    fetchNeighbours(1, typeFilter);
  }, [caseId, nodeId, typeFilter]);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= (data?.total_pages || 1)) {
      fetchNeighbours(newPage, typeFilter);
    }
  };

  const getNodeIcon = (type) => {
    switch (type) {
      case 'Phone':
        return <Phone className="w-3.5 h-3.5 text-emerald-400" />;
      case 'Account':
      case 'VPA':
        return <Landmark className="w-3.5 h-3.5 text-amber-400" />;
      case 'Person':
        return <User className="w-3.5 h-3.5 text-blue-400" />;
      case 'IP':
        return <Globe className="w-3.5 h-3.5 text-cyan-400" />;
      case 'Device':
        return <Smartphone className="w-3.5 h-3.5 text-slate-400" />;
      default:
        return <Layers className="w-3.5 h-3.5 text-purple-400" />;
    }
  };

  if (!nodeId) return null;

  return (
    <div className="w-96 bg-slate-900 border-l border-slate-800 flex flex-col h-full text-slate-100 shadow-2xl z-20">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-start justify-between gap-3 bg-slate-950/80">
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="p-2 rounded bg-slate-800 text-slate-300 shrink-0 mt-0.5">
            {getNodeIcon(data?.node?.node_type)}
          </div>
          <div className="min-w-0">
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 uppercase">
              {data?.node?.node_type || 'Node'}
            </span>
            <h3 className="text-sm font-bold text-white truncate mt-1">
              {data?.node?.label || nodeId}
            </h3>
            <p className="text-[11px] font-mono text-slate-500 truncate">ID: {nodeId}</p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Action Toolbar */}
      {onExpandNode && (
        <div className="p-2.5 bg-slate-950/40 border-b border-slate-800 flex items-center justify-between">
          <button
            onClick={() => onExpandNode(nodeId)}
            className="w-full py-1.5 px-3 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded text-xs font-medium flex items-center justify-center gap-1.5 transition"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Expand 1-Hop in Graph
          </button>
        </div>
      )}

      {/* Filter and Notice Bar */}
      <div className="p-3 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between text-xs">
        <span className="font-mono text-slate-400">
          {loading ? 'Evaluating neighbours...' : (data?.notice || `showing ${data?.total_neighbours || 0} neighbours`)}
        </span>

        {data?.total_pages > 1 && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => handlePageChange(page - 1)}
              disabled={page <= 1}
              className="p-1 rounded bg-slate-800 disabled:opacity-40 text-slate-300 hover:text-white"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono text-[11px] text-slate-400">
              {page} / {data.total_pages}
            </span>
            <button
              onClick={() => handlePageChange(page + 1)}
              disabled={page >= data.total_pages}
              className="p-1 rounded bg-slate-800 disabled:opacity-40 text-slate-300 hover:text-white"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Main Connections List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {loading && (
          <div className="py-12 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-emerald-400" />
            <span>Loading topological connections...</span>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-950/30 border border-red-800 rounded text-xs text-red-300">
            {error}
          </div>
        )}

        {!loading && !error && Object.keys(data?.grouped_neighbours || {}).length === 0 && (
          <div className="py-12 text-center text-xs text-slate-500">
            No direct connections found for this entity.
          </div>
        )}

        {!loading &&
          !error &&
          Object.entries(data?.grouped_neighbours || {}).map(([typeGroup, nbrs]) => (
            <div key={typeGroup} className="space-y-2">
              <div className="flex items-center justify-between border-b border-slate-800 pb-1">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wide flex items-center gap-1.5">
                  {getNodeIcon(typeGroup)}
                  {typeGroup} ({nbrs.length})
                </span>
              </div>

              <div className="space-y-2">
                {nbrs.map((nbr) => (
                  <div
                    key={nbr.node_id}
                    className="p-3 bg-slate-950/50 border border-slate-800/80 rounded-md space-y-2 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-medium text-white truncate max-w-[180px]">
                        {nbr.label}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                        {nbr.connections?.length || 1} link(s)
                      </span>
                    </div>

                    {/* Edge Details */}
                    {nbr.connections?.map((conn, cIdx) => (
                      <div
                        key={cIdx}
                        className="text-[11px] p-2 bg-slate-900/90 rounded border border-slate-800/60 space-y-1 font-mono"
                      >
                        <div className="flex items-center justify-between text-slate-300">
                          <span className="text-emerald-400 font-bold">{conn.edge_type}</span>
                          <span className="text-slate-400">({conn.direction})</span>
                        </div>

                        {conn.total_paise > 0 && (
                          <div className="flex items-center gap-1.5 text-amber-300">
                            <DollarSign className="w-3 h-3 text-amber-400" />
                            <span>{conn.total_inr}</span>
                          </div>
                        )}

                        {conn.count > 1 && (
                          <div className="text-slate-400">Events: {conn.count}</div>
                        )}

                        {(conn.first_seen || conn.last_seen) && (
                          <div className="text-slate-500 text-[10px] flex items-center gap-1 truncate">
                            <Calendar className="w-2.5 h-2.5" />
                            {conn.first_seen?.slice(0, 10)} → {conn.last_seen?.slice(0, 10)}
                          </div>
                        )}

                        {/* Evidence Chips */}
                        {conn.source_evidence_ids && conn.source_evidence_ids.length > 0 && (
                          <div className="pt-1 flex flex-wrap gap-1">
                            {conn.source_evidence_ids.map((src, sIdx) => (
                              <span
                                key={sIdx}
                                className="text-[9px] px-1 py-0.5 bg-slate-950 rounded border border-slate-800 text-slate-400 truncate max-w-[150px]"
                                title={src}
                              >
                                {src}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}

