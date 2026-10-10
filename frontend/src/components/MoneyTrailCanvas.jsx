import React, { useEffect, useRef, useState, useCallback } from 'react';
import cytoscape from 'cytoscape';
import { moneyApi } from '../api/client';

// Indian currency formatter helper
function formatINR(amount) {
  if (amount === undefined || amount === null || isNaN(amount)) return '₹0';
  const abs = Math.abs(amount);
  const sign = amount < 0 ? '-' : '';

  if (abs >= 10000000) {
    return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
  } else if (abs >= 100000) {
    return `${sign}₹${(abs / 100000).toFixed(2)} Lakh`;
  } else {
    return `${sign}₹${Number(abs).toLocaleString('en-IN')}`;
  }
}

export default function MoneyTrailCanvas({ caseId, isViewer }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  // Filter & Control States
  const [accountQuery, setAccountQuery] = useState('');
  const [direction, setDirection] = useState('both'); // 'in', 'out', 'both'
  const [hops, setHops] = useState(2);
  const [minAmount, setMinAmount] = useState(0);
  const [customMinInput, setCustomMinInput] = useState('');
  const [layoutMode, setLayoutMode] = useState('directed'); // 'directed' | 'force'

  // Data States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [trailData, setTrailData] = useState(null);
  const [quantiles, setQuantiles] = useState(null);
  const [candidates, setCandidates] = useState([]);

  // Selection & Inspector
  const [selectedElement, setSelectedElement] = useState(null); // { type: 'node' | 'edge', data: {} }
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'anomalies' | 'paths' | 'transactions'
  const [rawTxns, setRawTxns] = useState([]);
  const [rawTxnsLoading, setRawTxnsLoading] = useState(false);

  // 1. Fetch data-driven transaction volume quantiles on mount
  useEffect(() => {
    let mounted = true;
    const fetchQuantiles = async () => {
      try {
        const res = await moneyApi.getTxnVolume(caseId);
        if (mounted && res.quantiles) {
          setQuantiles(res.quantiles);
        }
      } catch (err) {
        // Degrades gracefully
      }
    };
    fetchQuantiles();
    return () => {
      mounted = false;
    };
  }, [caseId]);

  // 2. Fetch Money Trail Data
  const loadTrail = useCallback(
    async (acc = accountQuery, minAmt = minAmount, numHops = hops, dir = direction) => {
      setLoading(true);
      setError(null);
      try {
        const res = await moneyApi.getTrail(caseId, {
          account: acc.trim() || undefined,
          minAmount: minAmt,
          hops: numHops,
          direction: dir,
          limit: 200,
        });

        if (res.candidates && res.candidates.length > 0) {
          setCandidates(res.candidates);
        } else {
          setCandidates([]);
        }

        setTrailData(res);
        setSelectedElement(null);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load money trail');
      } finally {
        setLoading(false);
      }
    },
    [caseId, accountQuery, minAmount, hops, direction]
  );

  // Initial load
  useEffect(() => {
    loadTrail('', 0, hops, direction);
  }, [caseId]);

  // 3. Initialize & Update Cytoscape Graph
  useEffect(() => {
    if (!containerRef.current || !trailData) return;

    const elements = [];

    // Nodes
    (trailData.nodes || []).forEach((n) => {
      const isFocus = n.is_focus === true;
      const label = n.holder_name && n.holder_name !== n.id
        ? `${n.holder_name}\n[${n.id}]`
        : n.id;

      elements.push({
        group: 'nodes',
        data: {
          id: n.id,
          label: label,
          isFocus: isFocus,
          raw: n,
        },
      });
    });

    // Visible Edges (Qualifying)
    (trailData.edges || []).forEach((e) => {
      const edgeWeight = Math.min(8, Math.max(2, 2 + Math.log10(Math.max(1, e.amount_inr / 1000))));
      elements.push({
        group: 'edges',
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          label: formatINR(e.amount_inr),
          weight: edgeWeight,
          belowFilter: false,
          raw: e,
        },
      });
    });

    // Hidden Edges (Below filter)
    (trailData.hidden_edges || []).forEach((e) => {
      elements.push({
        group: 'edges',
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          label: `${formatINR(e.amount_inr)} (Filtered)`,
          weight: 1.5,
          belowFilter: true,
          raw: e,
        },
      });
    });

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const layoutConfig = layoutMode === 'directed'
      ? {
          name: 'breadthfirst',
          directed: true,
          roots: trailData.focus_account ? [`#${trailData.focus_account}`] : undefined,
          padding: 30,
          spacingFactor: 1.3,
          animate: false,
        }
      : {
          name: 'cose',
          animate: false,
          componentSpacing: 80,
          nodeOverlap: 20,
          idealEdgeLength: 90,
          gravity: 80,
          numIter: 300,
        };

    const cy = cytoscape({
      container: containerRef.current,
      elements: elements,
      style: [
        {
          selector: 'node',
          style: {
            'shape': 'roundrectangle',
            'width': '120px',
            'height': '48px',
            'background-color': '#0f172a',
            'border-width': 1.5,
            'border-color': '#334155',
            'label': 'data(label)',
            'color': '#f8fafc',
            'font-size': '10px',
            'font-family': 'Inter, system-ui, sans-serif',
            'font-weight': 500,
            'text-valign': 'center',
            'text-halign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': '110px',
            'transition-property': 'border-color, border-width, background-color',
            'transition-duration': '0.2s',
          },
        },
        {
          selector: 'node[?isFocus]',
          style: {
            'background-color': '#032b43',
            'border-color': '#38bdf8',
            'border-width': 3,
            'color': '#ffffff',
            'font-weight': 600,
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 'data(weight)',
            'line-color': '#0284c7',
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#0284c7',
            'arrow-scale': 0.8,
            'label': 'data(label)',
            'color': '#94a3b8',
            'font-size': '9px',
            'font-family': 'monospace',
            'text-rotation': 'autorotate',
            'text-margin-y': -7,
            'text-background-opacity': 0.8,
            'text-background-color': '#030712',
            'text-background-padding': '2px',
            'text-background-shape': 'roundrectangle',
            'opacity': 0.85,
          },
        },
        {
          selector: 'edge[?belowFilter]',
          style: {
            'line-color': '#475569',
            'target-arrow-color': '#475569',
            'line-style': 'dashed',
            'opacity': 0.4,
            'color': '#64748b',
          },
        },
        {
          selector: '.highlighted',
          style: {
            'border-color': '#f59e0b',
            'border-width': 3.5,
            'background-color': '#451a03',
          },
        },
      ],
      layout: layoutConfig,
    });

    // Node click
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      setSelectedElement({ type: 'node', data: node.data('raw'), id: node.id() });
    });

    // Edge click
    cy.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      setSelectedElement({ type: 'edge', data: edge.data('raw'), id: edge.id() });
    });

    // Background click
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedElement(null);
      }
    });

    cyRef.current = cy;

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [trailData, layoutMode]);

  // 4. Fetch raw transactions for inspection table
  const fetchTransactionsForAccount = async (acc) => {
    setRawTxnsLoading(true);
    try {
      const res = await moneyApi.listTransactions(caseId, { account: acc, limit: 100 });
      setRawTxns(res.items || []);
    } catch (err) {
      setRawTxns([]);
    } finally {
      setRawTxnsLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'transactions' && trailData?.focus_account) {
      fetchTransactionsForAccount(trailData.focus_account);
    }
  }, [activeTab, trailData?.focus_account]);

  // Export CSV
  const handleExportCSV = () => {
    if (!rawTxns.length) return;
    const headers = ['Transaction ID', 'From Account', 'From Name', 'To Account', 'To Name', 'Amount INR', 'Date', 'Reference'];
    const rows = rawTxns.map((t) => [
      t.fingerprint,
      t.from_account,
      `"${t.from_name || ''}"`,
      t.to_account,
      `"${t.to_name || ''}"`,
      t.amount_inr,
      t.date || '',
      `"${t.reference || ''}"`,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `money_trail_${trailData.focus_account || 'export'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleApplyQuantile = (val) => {
    setMinAmount(val);
    setCustomMinInput(val > 0 ? String(val) : '');
    loadTrail(accountQuery, val, hops, direction);
  };

  const handleApplyCustomMin = (e) => {
    e.preventDefault();
    const val = parseFloat(customMinInput) || 0;
    setMinAmount(val);
    loadTrail(accountQuery, val, hops, direction);
  };

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 30);
    }
  };

  const hasData = trailData && (trailData.nodes.length > 0 || trailData.edges.length > 0);

  return (
    <div className="flex flex-col h-[750px] bg-[#0b1120] border border-[#1e293b] rounded-lg overflow-hidden">
      {/* 1. Header Toolbar */}
      <div className="bg-[#030712] border-b border-[#1e293b] p-3 flex flex-wrap items-center justify-between gap-3">
        {/* Left: Search & Navigation */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <input
              type="text"
              placeholder="Search account no. or holder..."
              value={accountQuery}
              onChange={(e) => setAccountQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadTrail(accountQuery, minAmount, hops, direction)}
              className="bg-[#0b1120] border border-[#334155] focus:border-[#0284c7] px-3 py-1.5 rounded text-xs text-white placeholder-slate-500 w-52 focus:outline-none"
            />
            {accountQuery && (
              <button
                onClick={() => {
                  setAccountQuery('');
                  loadTrail('', minAmount, hops, direction);
                }}
                className="absolute right-2 top-2 text-slate-500 hover:text-white text-xs"
              >
                ×
              </button>
            )}
          </div>

          <button
            onClick={() => loadTrail(accountQuery, minAmount, hops, direction)}
            className="px-3 py-1.5 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded transition-colors"
          >
            Trace
          </button>

          {/* Direction Selector */}
          <div className="flex items-center gap-1 bg-[#0b1120] border border-[#1e293b] rounded p-0.5">
            {[
              { id: 'out', label: 'Outflow →' },
              { id: 'in', label: '← Inflow' },
              { id: 'both', label: '⇄ Both' },
            ].map((d) => (
              <button
                key={d.id}
                onClick={() => {
                  setDirection(d.id);
                  loadTrail(accountQuery, minAmount, hops, d.id);
                }}
                className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                  direction === d.id
                    ? 'bg-[#0284c7] text-white font-semibold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>

          {/* Hops Selector */}
          <div className="flex items-center gap-1 bg-[#0b1120] border border-[#1e293b] rounded p-0.5">
            {[1, 2, 3, 4].map((h) => (
              <button
                key={h}
                onClick={() => {
                  setHops(h);
                  loadTrail(accountQuery, minAmount, h, direction);
                }}
                className={`px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                  hops === h
                    ? 'bg-[#1e293b] text-white font-semibold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {h} {h === 1 ? 'Hop' : 'Hops'}
              </button>
            ))}
          </div>
        </div>

        {/* Right: Layout & Tools */}
        <div className="flex items-center gap-2">
          {/* Layout Toggle */}
          <div className="flex items-center gap-1 bg-[#0b1120] border border-[#1e293b] rounded p-0.5">
            <button
              onClick={() => setLayoutMode('directed')}
              className={`px-2 py-1 text-[11px] rounded transition-colors ${
                layoutMode === 'directed' ? 'bg-[#1e293b] text-white font-semibold' : 'text-slate-400'
              }`}
            >
              Hierarchy
            </button>
            <button
              onClick={() => setLayoutMode('force')}
              className={`px-2 py-1 text-[11px] rounded transition-colors ${
                layoutMode === 'force' ? 'bg-[#1e293b] text-white font-semibold' : 'text-slate-400'
              }`}
            >
              Network
            </button>
          </div>

          <button
            onClick={handleFit}
            title="Reset Zoom & Center View"
            className="px-2.5 py-1.5 bg-[#0b1120] hover:bg-[#1e293b] text-slate-400 hover:text-white text-xs rounded border border-[#1e293b] transition-colors"
          >
            Fit
          </button>
        </div>
      </div>

      {/* 2. Data-Driven Quantile Quick Filter Bar */}
      <div className="bg-[#070b14] border-b border-[#1e293b] px-4 py-2 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-slate-400 font-mono text-[11px]">MIN AMOUNT FILTER:</span>

          <button
            onClick={() => handleApplyQuantile(0)}
            className={`px-2 py-0.5 rounded text-[11px] font-mono border transition-colors ${
              minAmount === 0
                ? 'bg-[#0284c7] border-[#0284c7] text-white font-semibold'
                : 'bg-[#0b1120] border-[#334155] text-slate-300 hover:text-white'
            }`}
          >
            All (₹0)
          </button>

          {quantiles && quantiles.p50 > 0 && (
            <button
              onClick={() => handleApplyQuantile(quantiles.p50)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono border transition-colors ${
                minAmount === quantiles.p50
                  ? 'bg-[#0284c7] border-[#0284c7] text-white font-semibold'
                  : 'bg-[#0b1120] border-[#334155] text-slate-300 hover:text-white'
              }`}
            >
              p50 ({formatINR(quantiles.p50)})
            </button>
          )}

          {quantiles && quantiles.p75 > 0 && (
            <button
              onClick={() => handleApplyQuantile(quantiles.p75)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono border transition-colors ${
                minAmount === quantiles.p75
                  ? 'bg-[#0284c7] border-[#0284c7] text-white font-semibold'
                  : 'bg-[#0b1120] border-[#334155] text-slate-300 hover:text-white'
              }`}
            >
              p75 ({formatINR(quantiles.p75)})
            </button>
          )}

          {quantiles && quantiles.p90 > 0 && (
            <button
              onClick={() => handleApplyQuantile(quantiles.p90)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono border transition-colors ${
                minAmount === quantiles.p90
                  ? 'bg-[#0284c7] border-[#0284c7] text-white font-semibold'
                  : 'bg-[#0b1120] border-[#334155] text-slate-300 hover:text-white'
              }`}
            >
              p90 ({formatINR(quantiles.p90)})
            </button>
          )}

          {quantiles && quantiles.p99 > 0 && (
            <button
              onClick={() => handleApplyQuantile(quantiles.p99)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono border transition-colors ${
                minAmount === quantiles.p99
                  ? 'bg-[#0284c7] border-[#0284c7] text-white font-semibold'
                  : 'bg-[#0b1120] border-[#334155] text-slate-300 hover:text-white'
              }`}
            >
              p99 ({formatINR(quantiles.p99)})
            </button>
          )}

          {/* Custom Input */}
          <form onSubmit={handleApplyCustomMin} className="flex items-center gap-1">
            <input
              type="number"
              min="0"
              placeholder="Custom ₹"
              value={customMinInput}
              onChange={(e) => setCustomMinInput(e.target.value)}
              className="bg-[#0b1120] border border-[#334155] px-2 py-0.5 rounded text-[11px] text-white font-mono w-24 focus:outline-none"
            />
            <button
              type="submit"
              className="px-2 py-0.5 bg-[#1e293b] hover:bg-[#334155] text-slate-200 text-[11px] rounded"
            >
              Apply
            </button>
          </form>
        </div>

        {trailData?.meta && (
          <div className="text-[11px] text-slate-400 font-mono">
            Visible: {trailData.meta.count_nodes} accounts, {trailData.meta.count_edges} transfers
            {trailData.meta.count_hidden_edges > 0 && (
              <span className="text-amber-400 ml-1">
                ({trailData.meta.count_hidden_edges} dashed below filter)
              </span>
            )}
          </div>
        )}
      </div>

      {/* Disambiguation Candidates Bar */}
      {candidates.length > 0 && (
        <div className="bg-amber-950/40 border-b border-amber-900 px-4 py-2 flex items-center gap-2 overflow-x-auto text-xs">
          <span className="text-amber-300 font-semibold whitespace-nowrap">Select target account:</span>
          {candidates.map((cand) => (
            <button
              key={cand.account}
              onClick={() => {
                setAccountQuery(cand.account);
                loadTrail(cand.account, minAmount, hops, direction);
              }}
              className="px-2.5 py-0.5 bg-[#030712] hover:bg-[#1e293b] border border-amber-800 rounded text-amber-200 text-[11px] whitespace-nowrap"
            >
              {cand.holder_name} [{cand.account}] ({formatINR(cand.volume_inr)})
            </button>
          ))}
        </div>
      )}

      {/* 3. Main Workspace Area */}
      <div className="relative flex-1 flex overflow-hidden">
        {/* Cytoscape Canvas */}
        <div ref={containerRef} className="flex-1 w-full h-full bg-[#070b14]" />

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 bg-[#070b14]/70 backdrop-blur-sm flex items-center justify-center z-20">
            <div className="text-center text-xs text-slate-400">
              <div className="inline-block animate-spin w-6 h-6 border-2 border-slate-600 border-t-[#38bdf8] rounded-full mb-2" />
              <p>Reconstructing money trail flow...</p>
            </div>
          </div>
        )}

        {/* Empty State when no banking transactions */}
        {!loading && !hasData && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#070b14] z-10">
            <div className="text-center max-w-md p-6 bg-[#0b1120] border border-[#1e293b] rounded-lg">
              <div className="w-10 h-10 bg-[#030712] border border-[#1e293b] rounded-full flex items-center justify-center mx-auto mb-3 text-slate-400">
                ₹
              </div>
              <h3 className="text-sm font-bold text-white">No Bank Transaction Data</h3>
              <p className="text-xs text-slate-400 mt-1">
                Upload and ingest bank statement or bank transaction files in the Evidence Repository to activate the Money Trail Explorer.
              </p>
            </div>
          </div>
        )}

        {/* Truncated notice */}
        {trailData?.truncated && (
          <div className="absolute top-3 left-3 bg-[#030712]/90 border border-amber-600/60 rounded px-2.5 py-1 text-[11px] text-amber-300 z-10 font-mono">
            ⚠️ Flow truncated at 200 account limit. Increase minimum amount filter.
          </div>
        )}

        {/* 4. Right Inspector Drawer */}
        <div className="w-96 bg-[#030712] border-l border-[#1e293b] flex flex-col justify-between overflow-hidden z-20 shadow-2xl">
          {/* Drawer Subnav */}
          <div className="border-b border-[#1e293b] flex items-center text-xs">
            {[
              { id: 'overview', label: 'Summary' },
              { id: 'anomalies', label: `Anomalies (${trailData?.patterns?.length || 0})` },
              { id: 'paths', label: `Paths (${trailData?.ordered_paths?.length || 0})` },
              { id: 'transactions', label: 'Ledger' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 py-2 text-[11px] font-medium text-center border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-[#0284c7] text-[#38bdf8] font-semibold bg-[#0b1120]'
                    : 'border-transparent text-slate-400 hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Drawer Body */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {/* TAB 1: OVERVIEW & FOCUS TOTALS */}
            {activeTab === 'overview' && (
              <div className="space-y-4">
                {/* Focus Account Card */}
                <div>
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 bg-[#1e293b] text-[#38bdf8] rounded">
                    Focus Account
                  </span>
                  <h3 className="text-sm font-bold text-white mt-1 break-all">
                    {trailData?.focus_account || 'None'}
                  </h3>
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-[#0b1120] border border-[#1e293b] p-2.5 rounded">
                    <span className="text-[10px] text-slate-500 uppercase font-mono">Total Inflow</span>
                    <p className="text-emerald-400 font-bold font-mono mt-0.5">
                      {formatINR(trailData?.totals?.inflow_inr)}
                    </p>
                  </div>
                  <div className="bg-[#0b1120] border border-[#1e293b] p-2.5 rounded">
                    <span className="text-[10px] text-slate-500 uppercase font-mono">Total Outflow</span>
                    <p className="text-rose-400 font-bold font-mono mt-0.5">
                      {formatINR(trailData?.totals?.outflow_inr)}
                    </p>
                  </div>
                  <div className="bg-[#0b1120] border border-[#1e293b] p-2.5 rounded">
                    <span className="text-[10px] text-slate-500 uppercase font-mono">Net Flow</span>
                    <p className="text-white font-bold font-mono mt-0.5">
                      {formatINR(trailData?.totals?.net_inr)}
                    </p>
                  </div>
                  <div className="bg-[#0b1120] border border-[#1e293b] p-2.5 rounded">
                    <span className="text-[10px] text-slate-500 uppercase font-mono">Counterparties</span>
                    <p className="text-white font-bold font-mono mt-0.5">
                      {trailData?.totals?.counterparties || 0} Accounts
                    </p>
                  </div>
                </div>

                {/* Selection Inspector (When clicking a node or edge) */}
                {selectedElement && (
                  <div className="p-3 bg-[#0b1120] border border-[#334155] rounded space-y-2 text-xs">
                    <div className="flex items-center justify-between pb-1 border-b border-[#1e293b]">
                      <span className="text-[10px] font-mono text-[#38bdf8] uppercase">
                        Selected {selectedElement.type}
                      </span>
                      <button
                        onClick={() => setSelectedElement(null)}
                        className="text-slate-400 hover:text-white text-[11px]"
                      >
                        [Clear]
                      </button>
                    </div>

                    {selectedElement.type === 'node' && (
                      <div className="space-y-1">
                        <div className="font-semibold text-white">
                          {selectedElement.data.holder_name || selectedElement.data.id}
                        </div>
                        <div className="text-[11px] font-mono text-slate-400">
                          Account: {selectedElement.data.id}
                        </div>
                        <div className="flex justify-between text-[11px] pt-1">
                          <span className="text-emerald-400">In: {formatINR(selectedElement.data.inflow_inr)}</span>
                          <span className="text-rose-400">Out: {formatINR(selectedElement.data.outflow_inr)}</span>
                        </div>
                        <button
                          onClick={() => {
                            setAccountQuery(selectedElement.data.id);
                            loadTrail(selectedElement.data.id, minAmount, hops, direction);
                          }}
                          className="w-full mt-2 py-1 bg-[#1e293b] hover:bg-[#334155] text-[#38bdf8] text-[11px] rounded transition-colors"
                        >
                          Focus on this Account
                        </button>
                      </div>
                    )}

                    {selectedElement.type === 'edge' && (
                      <div className="space-y-1 text-[11px]">
                        <div className="font-mono text-slate-300">
                          {selectedElement.data.source} → {selectedElement.data.target}
                        </div>
                        <div className="text-sm font-bold text-emerald-400">
                          {formatINR(selectedElement.data.amount_inr)}
                        </div>
                        <div className="text-slate-400">
                          Transfers: {selectedElement.data.txn_count} transactions
                        </div>
                        {selectedElement.data.first_date && (
                          <div className="text-slate-400 font-mono text-[10px]">
                            Timeline: {selectedElement.data.first_date} to {selectedElement.data.last_date}
                          </div>
                        )}
                        {selectedElement.data.references && selectedElement.data.references.length > 0 && (
                          <div className="text-slate-400 font-mono text-[10px] break-all">
                            Refs: {selectedElement.data.references.join(', ')}
                          </div>
                        )}
                        <div className="text-[10px] text-slate-500 pt-1 font-mono">
                          Evidence Lineage: Section 63 BSA Verified
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: PATTERN ANOMALIES */}
            {activeTab === 'anomalies' && (
              <div className="space-y-3">
                {trailData?.patterns && trailData.patterns.length > 0 ? (
                  trailData.patterns.map((pat, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-[#0b1120] border border-amber-900/60 rounded text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="px-1.5 py-0.5 bg-amber-950 text-amber-300 border border-amber-800 rounded text-[10px] font-mono">
                          {pat.label}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">Account {pat.account}</span>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-relaxed">
                        {pat.explanation}
                      </p>
                      {pat.evidence_txn_keys && pat.evidence_txn_keys.length > 0 && (
                        <div className="text-[10px] text-slate-500 font-mono">
                          Evidence Keys: {pat.evidence_txn_keys.slice(0, 3).join(', ')}
                          {pat.evidence_txn_keys.length > 3 && ` +${pat.evidence_txn_keys.length - 3} more`}
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="py-8 text-center text-xs text-slate-500">
                    No pattern anomalies flagged under current case thresholds.
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: ORDERED PATHS */}
            {activeTab === 'paths' && (
              <div className="space-y-3">
                {trailData?.ordered_paths && trailData.ordered_paths.length > 0 ? (
                  trailData.ordered_paths.map((p, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 bg-[#0b1120] border border-[#1e293b] rounded text-xs space-y-2"
                    >
                      <div className="flex items-center justify-between font-mono text-[10px] text-slate-400">
                        <span className="uppercase text-[#38bdf8] font-semibold">{p.direction}</span>
                        <span>{p.length} hops</span>
                      </div>
                      <div className="space-y-1">
                        {p.steps &&
                          p.steps.map((st, sIdx) => (
                            <div
                              key={sIdx}
                              className="flex items-center justify-between text-[11px] font-mono border-b border-[#1e293b]/60 pb-1"
                            >
                              <span className="text-slate-300 truncate w-32">{st.from}</span>
                              <span className="text-emerald-400 font-bold">{formatINR(st.amount_inr)}</span>
                              <span className="text-slate-300 truncate w-32 text-right">{st.to}</span>
                            </div>
                          ))}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="py-8 text-center text-xs text-slate-500">
                    No multi-hop transfer sequences found under current parameters.
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: RAW LEDGER TRANSACTIONS */}
            {activeTab === 'transactions' && (
              <div className="space-y-2">
                <div className="flex items-center justify-between pb-2 border-b border-[#1e293b]">
                  <span className="text-[11px] text-slate-400 font-mono">
                    Transactions for {trailData?.focus_account}
                  </span>
                  <button
                    onClick={handleExportCSV}
                    disabled={!rawTxns.length}
                    className="px-2 py-1 bg-[#1e293b] hover:bg-[#334155] text-white text-[10px] rounded transition-colors disabled:opacity-50"
                  >
                    Export CSV
                  </button>
                </div>

                {rawTxnsLoading ? (
                  <div className="py-8 text-center text-xs text-slate-500">Loading ledger records...</div>
                ) : rawTxns.length > 0 ? (
                  <div className="space-y-1.5 max-h-96 overflow-y-auto">
                    {rawTxns.map((t) => (
                      <div
                        key={t.id}
                        className="p-2 bg-[#0b1120] border border-[#1e293b] rounded text-[11px] space-y-1"
                      >
                        <div className="flex justify-between items-center">
                          <span className="text-emerald-400 font-bold font-mono">
                            {formatINR(t.amount_inr)}
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono">{t.date || 'Unknown Date'}</span>
                        </div>
                        <div className="text-slate-300 font-mono text-[10px]">
                          {t.from_account} → {t.to_account}
                        </div>
                        {t.reference && (
                          <div className="text-[9px] text-slate-500 font-mono truncate">
                            Ref: {t.reference}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-8 text-center text-xs text-slate-500">
                    No transactions found for this account.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Drawer Footer */}
          <div className="p-3 border-t border-[#1e293b] text-[10px] text-slate-500 font-mono">
            Section 63 BSA 2023 Compliant Financial Evidence Trail.
          </div>
        </div>
      </div>
    </div>
  );
}
