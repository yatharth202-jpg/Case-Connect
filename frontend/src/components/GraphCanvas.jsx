import React, { useEffect, useRef, useState, useCallback } from 'react';
import cytoscape from 'cytoscape';
import { graphApi } from '../api/client';

const NODE_COLORS = {
  Person: '#2563eb',       // Blue
  Phone: '#059669',        // Emerald
  BankAccount: '#d97706',  // Amber
  Vehicle: '#0891b2',      // Cyan
  IP: '#db2777',           // Rose
  Organization: '#4f46e5', // Indigo
  FIR: '#dc2626',          // Red
  Default: '#64748b',      // Slate
};

export default function GraphCanvas({ caseId, isViewer }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  // Graph state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [hops, setHops] = useState(2);
  const [viewMode, setViewMode] = useState('entity'); // 'entity' | 'detail'
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [truncated, setTruncated] = useState(false);
  const [candidates, setCandidates] = useState([]);

  // Inspection Drawer state
  const [selectedElement, setSelectedElement] = useState(null); // { type: 'node' | 'edge', data: {} }

  // Path Finder state
  const [pathMode, setPathMode] = useState(false);
  const [pathFrom, setPathFrom] = useState('');
  const [pathTo, setPathTo] = useState('');
  const [pathResult, setPathResult] = useState(null);
  const [pathLoading, setPathLoading] = useState(false);

  // Officer Link Modal state
  const [linkModalOpen, setLinkModalOpen] = useState(false);
  const [linkSource, setLinkSource] = useState('');
  const [linkTarget, setLinkTarget] = useState('');
  const [linkType, setLinkType] = useState('USES');
  const [linkSubmitting, setLinkSubmitting] = useState(false);

  // 1. Fetch graph data
  const loadGraph = useCallback(
    async (query = searchQuery, numHops = hops, view = viewMode) => {
      setLoading(true);
      setError(null);
      try {
        const res = await graphApi.search(caseId, {
          q: query.trim() || undefined,
          hops: numHops,
          view: view,
          limit: 250,
        });

        if (res.candidates && res.candidates.length > 0) {
          setCandidates(res.candidates);
        } else {
          setCandidates([]);
        }

        setGraphData({ nodes: res.nodes || [], edges: res.edges || [] });
        setTruncated(res.truncated || false);
        setPathResult(null);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load investigation graph');
      } finally {
        setLoading(false);
      }
    },
    [caseId, searchQuery, hops, viewMode]
  );

  // Load initially
  useEffect(() => {
    loadGraph('', hops, viewMode);
  }, [caseId, viewMode]);

  // 2. Initialize & Update Cytoscape
  useEffect(() => {
    if (!containerRef.current) return;

    // Build elements array for Cytoscape
    const elements = [];

    // Nodes
    (graphData.nodes || []).forEach((n) => {
      const labelType = n.label || 'Default';
      const color = NODE_COLORS[labelType] || NODE_COLORS.Default;
      const deg = n.degree || 0;
      const size = Math.min(65, Math.max(30, 30 + deg * 2.5));
      const isShared = n.shared === true;

      let displayName = n.name || n.id || 'Node';
      if (isShared) displayName += ' [SHARED]';

      elements.push({
        group: 'nodes',
        data: {
          id: n.key,
          rawId: n.id,
          label: displayName,
          entityLabel: labelType,
          color: color,
          size: size,
          isShared: isShared,
          borderColor: isShared ? '#f97316' : '#334155',
          borderWidth: isShared ? 3 : 1.5,
          raw: n,
        },
      });
    });

    // Edges
    (graphData.edges || []).forEach((e, idx) => {
      const edgeId = e.id || e.key || `edge_${idx}`;
      let labelText = e.type || '';
      let weight = 2;

      if (e.type === 'COMMUNICATES_WITH' && e.calls) {
        labelText = `CALLED (${e.calls})`;
        weight = Math.min(7, Math.max(2, 2 + Math.log2(e.calls + 1)));
      } else if (e.type === 'PAID' && e.amount_inr) {
        labelText = `PAID ₹${Number(e.amount_inr).toLocaleString('en-IN')}`;
        weight = 3.5;
      } else if (e.type === 'CALLED' && e.count) {
        labelText = `CALLED (${e.count})`;
        weight = Math.min(6, Math.max(2, 1.5 + e.count));
      } else if (e.type === 'TRANSFERRED_TO' && e.amount_paise) {
        labelText = `₹${(e.amount_paise / 100).toLocaleString('en-IN')}`;
        weight = 3;
      }

      elements.push({
        group: 'edges',
        data: {
          id: edgeId,
          source: e.source,
          target: e.target,
          label: labelText,
          edgeType: e.type,
          weight: weight,
          raw: e,
        },
      });
    });

    // Destroy existing instance
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    // Create Cytoscape instance
    const cy = cytoscape({
      container: containerRef.current,
      elements: elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            'label': 'data(label)',
            'color': '#f8fafc',
            'font-size': '10px',
            'font-family': 'Inter, system-ui, sans-serif',
            'font-weight': 500,
            'text-valign': 'bottom',
            'text-margin-y': 5,
            'text-wrap': 'ellipsis',
            'text-max-width': '90px',
            'text-background-opacity': 0.8,
            'text-background-color': '#030712',
            'text-background-padding': '2px',
            'text-background-shape': 'roundrectangle',
            'width': 'data(size)',
            'height': 'data(size)',
            'border-color': 'data(borderColor)',
            'border-width': 'data(borderWidth)',
            'transition-property': 'background-color, border-color, border-width, opacity',
            'transition-duration': '0.2s',
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 'data(weight)',
            'line-color': '#475569',
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#475569',
            'arrow-scale': 0.8,
            'label': 'data(label)',
            'color': '#94a3b8',
            'font-size': '8px',
            'font-family': 'monospace',
            'text-rotation': 'autorotate',
            'text-margin-y': -6,
            'text-background-opacity': 0.7,
            'text-background-color': '#0b1120',
            'text-background-padding': '1px',
            'text-background-shape': 'roundrectangle',
            'opacity': 0.75,
            'transition-property': 'line-color, target-arrow-color, width, opacity',
            'transition-duration': '0.2s',
          },
        },
        {
          selector: 'edge[edgeType = "COMMUNICATES_WITH"]',
          style: {
            'target-arrow-shape': 'none', // Undirected representation
          },
        },
        {
          selector: '.highlighted',
          style: {
            'border-color': '#f59e0b',
            'border-width': 4,
            'text-background-color': '#b45309',
            'opacity': 1,
            'z-index': 999,
          },
        },
        {
          selector: '.edge-highlighted',
          style: {
            'line-color': '#f59e0b',
            'target-arrow-color': '#f59e0b',
            'width': 4,
            'opacity': 1,
            'color': '#fde68a',
            'z-index': 998,
          },
        },
        {
          selector: '.dimmed',
          style: {
            'opacity': 0.15,
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        randomize: false,
        componentSpacing: 100,
        nodeOverlap: 20,
        idealEdgeLength: 85,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 350,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
      },
    });

    // Click on node
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const rawData = node.data('raw');
      setSelectedElement({ type: 'node', data: rawData, key: node.id() });

      // If in path mode and selecting endpoints
      if (pathMode) {
        if (!pathFrom) {
          setPathFrom(node.id());
        } else if (!pathTo && node.id() !== pathFrom) {
          setPathTo(node.id());
        }
      }
    });

    // Click on edge
    cy.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      const rawData = edge.data('raw');
      setSelectedElement({ type: 'edge', data: rawData, id: edge.id() });
    });

    // Click on background
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
  }, [graphData]);

  // 3. Highlight shortest path when pathResult updates
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;

    cy.elements().removeClass('highlighted edge-highlighted dimmed');

    if (pathResult && pathResult.found && pathResult.path_nodes) {
      const pathNodeKeys = new Set(pathResult.path_nodes.map((n) => n.key));
      const pathEdgeKeys = new Set(pathResult.path_edges.map((e) => e.key || e.id));

      cy.elements().addClass('dimmed');

      cy.nodes().forEach((node) => {
        if (pathNodeKeys.has(node.id())) {
          node.removeClass('dimmed').addClass('highlighted');
        }
      });

      cy.edges().forEach((edge) => {
        const edgeRawKey = edge.data('raw')?.key || edge.id();
        const src = edge.source().id();
        const tgt = edge.target().id();
        if (
          pathEdgeKeys.has(edgeRawKey) ||
          (pathNodeKeys.has(src) && pathNodeKeys.has(tgt))
        ) {
          edge.removeClass('dimmed').addClass('edge-highlighted');
        }
      });
    }
  }, [pathResult]);

  // Fit & Center View
  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 40);
    }
  };

  // Execute Shortest Path
  const handleFindPath = async () => {
    if (!pathFrom || !pathTo) {
      alert('Please select or specify both source and destination nodes');
      return;
    }
    setPathLoading(true);
    setPathResult(null);
    try {
      const res = await graphApi.findPath(caseId, pathFrom, pathTo, viewMode);
      setPathResult(res);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to calculate shortest path');
    } finally {
      setPathLoading(false);
    }
  };

  const handleClearPath = () => {
    setPathFrom('');
    setPathTo('');
    setPathResult(null);
    if (cyRef.current) {
      cyRef.current.elements().removeClass('highlighted edge-highlighted dimmed');
    }
  };

  // Rebuild Graph
  const handleRebuildGraph = async () => {
    setLoading(true);
    try {
      await graphApi.rebuild(caseId);
      await loadGraph(searchQuery, hops, viewMode);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to rebuild graph projection');
      setLoading(false);
    }
  };

  // Submit Officer Link
  const handleCreateLink = async (e) => {
    e.preventDefault();
    if (!linkSource.trim() || !linkTarget.trim()) return;

    setLinkSubmitting(true);
    try {
      await graphApi.createLink(caseId, linkSource.trim(), linkTarget.trim(), linkType);
      setLinkModalOpen(false);
      setLinkSource('');
      setLinkTarget('');
      await loadGraph(searchQuery, hops, viewMode);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create officer link');
    } finally {
      setLinkSubmitting(false);
    }
  };

  // Delete Officer Link
  const handleDeleteLink = async (linkId) => {
    if (!confirm('Are you sure you want to remove this officer link annotation?')) return;
    try {
      await graphApi.deleteLink(caseId, linkId);
      setSelectedElement(null);
      await loadGraph(searchQuery, hops, viewMode);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete link');
    }
  };

  return (
    <div className="flex flex-col h-[750px] bg-[#0b1120] border border-[#1e293b] rounded-lg overflow-hidden">
      {/* 1. Header Toolbar */}
      <div className="bg-[#030712] border-b border-[#1e293b] p-3 flex flex-wrap items-center justify-between gap-3">
        {/* Left: Search & Traversal Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <input
              type="text"
              placeholder="Search name, phone, account..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadGraph(searchQuery, hops, viewMode)}
              className="bg-[#0b1120] border border-[#334155] focus:border-[#0284c7] px-3 py-1.5 rounded text-xs text-white placeholder-slate-500 w-56 focus:outline-none"
            />
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  loadGraph('', hops, viewMode);
                }}
                className="absolute right-2 top-2 text-slate-500 hover:text-white text-xs"
              >
                ×
              </button>
            )}
          </div>

          <button
            onClick={() => loadGraph(searchQuery, hops, viewMode)}
            className="px-3 py-1.5 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded transition-colors"
          >
            Expand
          </button>

          {/* Hops Selector */}
          <div className="flex items-center gap-1 bg-[#0b1120] border border-[#1e293b] rounded p-0.5">
            {[1, 2, 3, 4].map((h) => (
              <button
                key={h}
                onClick={() => {
                  setHops(h);
                  loadGraph(searchQuery, h, viewMode);
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

          {/* View Mode: Entity vs Detail */}
          <div className="flex items-center gap-1 bg-[#0b1120] border border-[#1e293b] rounded p-0.5">
            <button
              onClick={() => {
                setViewMode('entity');
                loadGraph(searchQuery, hops, 'entity');
              }}
              className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                viewMode === 'entity'
                  ? 'bg-[#0284c7] text-white font-semibold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Entity View
            </button>
            <button
              onClick={() => {
                setViewMode('detail');
                loadGraph(searchQuery, hops, 'detail');
              }}
              className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                viewMode === 'detail'
                  ? 'bg-[#0284c7] text-white font-semibold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Detail View
            </button>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPathMode(!pathMode)}
            className={`px-3 py-1.5 text-xs font-medium rounded border transition-colors ${
              pathMode
                ? 'bg-amber-950/60 border-amber-600 text-amber-300 font-semibold'
                : 'bg-[#0b1120] border-[#334155] text-slate-300 hover:text-white'
            }`}
          >
            {pathMode ? 'Close Path Finder' : 'Path Finder'}
          </button>

          {!isViewer && (
            <button
              onClick={() => setLinkModalOpen(true)}
              className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-white text-xs font-medium rounded border border-[#334155] transition-colors"
            >
              + Link Entity
            </button>
          )}

          <button
            onClick={handleRebuildGraph}
            title="Recalculate graph projection from staging tables"
            className="px-2.5 py-1.5 bg-[#0b1120] hover:bg-[#1e293b] text-slate-400 hover:text-white text-xs rounded border border-[#1e293b] transition-colors"
          >
            Rebuild
          </button>

          <button
            onClick={handleFit}
            title="Reset zoom & center graph"
            className="px-2.5 py-1.5 bg-[#0b1120] hover:bg-[#1e293b] text-slate-400 hover:text-white text-xs rounded border border-[#1e293b] transition-colors"
          >
            Fit
          </button>
        </div>
      </div>

      {/* Path Finder Bar (when active) */}
      {pathMode && (
        <div className="bg-[#0b1120] border-b border-[#1e293b] px-4 py-2 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-amber-400 font-semibold font-mono">SHORTEST PATH:</span>
            <input
              type="text"
              placeholder="From Node Key / Click Node"
              value={pathFrom}
              onChange={(e) => setPathFrom(e.target.value)}
              className="bg-[#030712] border border-[#334155] px-2 py-1 rounded text-white font-mono text-[11px] w-48"
            />
            <span className="text-slate-500">→</span>
            <input
              type="text"
              placeholder="To Node Key / Click Node"
              value={pathTo}
              onChange={(e) => setPathTo(e.target.value)}
              className="bg-[#030712] border border-[#334155] px-2 py-1 rounded text-white font-mono text-[11px] w-48"
            />
            <button
              onClick={handleFindPath}
              disabled={pathLoading || !pathFrom || !pathTo}
              className="px-3 py-1 bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded disabled:opacity-50"
            >
              {pathLoading ? 'Tracing...' : 'Trace Path'}
            </button>
            {(pathFrom || pathTo || pathResult) && (
              <button
                onClick={handleClearPath}
                className="text-slate-400 hover:text-white text-[11px]"
              >
                Clear
              </button>
            )}
          </div>

          {pathResult && (
            <div className="text-[11px] font-mono">
              {pathResult.found ? (
                <span className="text-amber-300 font-semibold">
                  Path Identified: {pathResult.length} hops ({pathResult.path_nodes?.length} nodes)
                </span>
              ) : (
                <span className="text-rose-400">No connection path found within 6 hops</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Disambiguation Candidates Bar (if search returns multiple matches) */}
      {candidates.length > 0 && (
        <div className="bg-amber-950/40 border-b border-amber-900 px-4 py-2 flex items-center gap-2 overflow-x-auto text-xs">
          <span className="text-amber-300 font-semibold whitespace-nowrap">Multiple matches found:</span>
          {candidates.map((cand) => (
            <button
              key={cand.key}
              onClick={() => {
                setSearchQuery(cand.id);
                loadGraph(cand.id, hops, viewMode);
              }}
              className="px-2 py-0.5 bg-[#030712] hover:bg-[#1e293b] border border-amber-800 rounded text-amber-200 text-[11px] whitespace-nowrap"
            >
              {cand.name || cand.id} ({cand.label})
            </button>
          ))}
        </div>
      )}

      {/* 2. Main Graph Workspace */}
      <div className="relative flex-1 flex overflow-hidden">
        {/* Cytoscape Canvas */}
        <div ref={containerRef} className="flex-1 w-full h-full bg-[#070b14]" />

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 bg-[#070b14]/70 backdrop-blur-sm flex items-center justify-center z-20">
            <div className="text-center text-xs text-slate-400">
              <div className="inline-block animate-spin w-6 h-6 border-2 border-slate-600 border-t-[#38bdf8] rounded-full mb-2" />
              <p>Projecting investigation subgraph...</p>
            </div>
          </div>
        )}

        {/* Truncated notice */}
        {truncated && (
          <div className="absolute top-3 left-3 bg-[#030712]/90 border border-amber-600/60 rounded px-2.5 py-1 text-[11px] text-amber-300 z-10 font-mono">
            ⚠️ Subgraph truncated at 250 node safety threshold. Narrow your query.
          </div>
        )}

        {/* Canvas Legend Overlay */}
        <div className="absolute bottom-3 left-3 bg-[#030712]/90 border border-[#1e293b] rounded p-2.5 z-10 text-[10px] space-y-1 backdrop-blur-sm">
          <div className="font-semibold text-slate-300 mb-1">Entity Categories:</div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="flex items-center gap-1.5 text-slate-300">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: NODE_COLORS.Person }} />
              Person
            </span>
            <span className="flex items-center gap-1.5 text-slate-300">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: NODE_COLORS.Phone }} />
              Phone
            </span>
            <span className="flex items-center gap-1.5 text-slate-300">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: NODE_COLORS.BankAccount }} />
              Account
            </span>
            <span className="flex items-center gap-1.5 text-slate-300">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: NODE_COLORS.Vehicle }} />
              Vehicle
            </span>
            <span className="flex items-center gap-1.5 text-slate-300">
              <span className="w-2.5 h-2.5 rounded-full border-2 border-[#f97316]" />
              Shared Identifier
            </span>
          </div>
        </div>

        {/* 3. Right Details Drawer */}
        {selectedElement && (
          <div className="w-80 bg-[#030712] border-l border-[#1e293b] p-4 flex flex-col justify-between overflow-y-auto z-20 shadow-2xl">
            <div className="space-y-4">
              {/* Header */}
              <div className="flex items-start justify-between pb-3 border-b border-[#1e293b]">
                <div>
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 bg-[#1e293b] text-[#38bdf8] rounded">
                    {selectedElement.type === 'node'
                      ? selectedElement.data.label || 'Entity'
                      : 'Relationship'}
                  </span>
                  <h3 className="text-sm font-bold text-white mt-1 break-words">
                    {selectedElement.type === 'node'
                      ? selectedElement.data.name || selectedElement.data.id
                      : selectedElement.data.type}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedElement(null)}
                  className="text-slate-400 hover:text-white text-xs font-mono"
                >
                  [X]
                </button>
              </div>

              {/* Node Inspector */}
              {selectedElement.type === 'node' && (
                <div className="space-y-3 text-xs">
                  {selectedElement.data.shared && (
                    <div className="p-2 bg-orange-950/60 border border-orange-700 rounded text-orange-300 text-[11px]">
                      <div className="font-bold flex items-center gap-1">⚠️ SHARED IDENTIFIER</div>
                      <p className="mt-0.5 text-orange-200">
                        This identifier is linked to multiple distinct owners (e.g. shared family phone). It has not been collapsed into a single entity.
                      </p>
                    </div>
                  )}

                  <div>
                    <label className="text-[10px] text-slate-500 uppercase font-mono">Canonical ID</label>
                    <p className="font-mono text-white text-[11px] break-all bg-[#0b1120] p-1.5 rounded border border-[#1e293b]">
                      {selectedElement.data.id}
                    </p>
                  </div>

                  {selectedElement.data.degree !== undefined && (
                    <div>
                      <label className="text-[10px] text-slate-500 uppercase font-mono">Direct Connections (Degree)</label>
                      <p className="text-white font-semibold">{selectedElement.data.degree}</p>
                    </div>
                  )}

                  {selectedElement.data.source_file && (
                    <div>
                      <label className="text-[10px] text-slate-500 uppercase font-mono">Evidence Lineage (Section 63 BSA)</label>
                      <p className="text-slate-300 text-[11px] font-mono break-all">
                        File: {selectedElement.data.source_file}
                        {selectedElement.data.source_ref && (
                          <span className="text-slate-500"> (Ref #{selectedElement.data.source_ref})</span>
                        )}
                      </p>
                    </div>
                  )}

                  {/* Actions for Node */}
                  <div className="pt-2 border-t border-[#1e293b] space-y-1.5">
                    <button
                      onClick={() => {
                        setPathMode(true);
                        setPathFrom(selectedElement.key);
                      }}
                      className="w-full text-left px-2.5 py-1.5 bg-[#0b1120] hover:bg-[#1e293b] border border-[#1e293b] text-slate-300 hover:text-white rounded text-[11px] transition-colors"
                    >
                      📍 Set as Path Source (From)
                    </button>
                    <button
                      onClick={() => {
                        setPathMode(true);
                        setPathTo(selectedElement.key);
                      }}
                      className="w-full text-left px-2.5 py-1.5 bg-[#0b1120] hover:bg-[#1e293b] border border-[#1e293b] text-slate-300 hover:text-white rounded text-[11px] transition-colors"
                    >
                      🎯 Set as Path Destination (To)
                    </button>
                    {!isViewer && (
                      <button
                        onClick={() => {
                          setLinkSource(selectedElement.data.name || selectedElement.data.id);
                          setLinkModalOpen(true);
                        }}
                        className="w-full text-left px-2.5 py-1.5 bg-[#0b1120] hover:bg-[#1e293b] border border-[#1e293b] text-[#38bdf8] rounded text-[11px] transition-colors"
                      >
                        🔗 Link this Entity
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Edge Inspector */}
              {selectedElement.type === 'edge' && (
                <div className="space-y-3 text-xs">
                  <div>
                    <label className="text-[10px] text-slate-500 uppercase font-mono">Relationship Type</label>
                    <p className="font-semibold text-white">{selectedElement.data.type}</p>
                  </div>

                  {selectedElement.data.calls !== undefined && (
                    <div>
                      <label className="text-[10px] text-slate-500 uppercase font-mono">Call Volume</label>
                      <p className="text-white font-mono text-sm">{selectedElement.data.calls} calls</p>
                    </div>
                  )}

                  {selectedElement.data.amount_inr !== undefined && (
                    <div>
                      <label className="text-[10px] text-slate-500 uppercase font-mono">Transfer Amount</label>
                      <p className="text-emerald-400 font-mono text-sm font-bold">
                        ₹{Number(selectedElement.data.amount_inr).toLocaleString('en-IN')}
                      </p>
                      {selectedElement.data.txn_count && (
                        <p className="text-slate-400 text-[10px]">
                          Across {selectedElement.data.txn_count} transactions
                        </p>
                      )}
                    </div>
                  )}

                  {selectedElement.data.first_call && (
                    <div>
                      <label className="text-[10px] text-slate-500 uppercase font-mono">Timeline</label>
                      <p className="text-slate-300 text-[11px] font-mono">
                        {selectedElement.data.first_call}
                        {selectedElement.data.last_call && ` to ${selectedElement.data.last_call}`}
                      </p>
                    </div>
                  )}

                  <div>
                    <label className="text-[10px] text-slate-500 uppercase font-mono">Attribution Method & Confidence</label>
                    <p className="text-slate-300 font-mono text-[11px]">
                      {selectedElement.data.method || 'derived'} ({Math.round((selectedElement.data.confidence || 1.0) * 100)}%)
                    </p>
                  </div>

                  {selectedElement.data.source_file && (
                    <div>
                      <label className="text-[10px] text-slate-500 uppercase font-mono">Evidence Lineage (Section 63 BSA)</label>
                      <p className="text-slate-300 text-[11px] font-mono break-all">
                        Source: {selectedElement.data.source_file}
                        {selectedElement.data.source_ref && (
                          <span className="text-slate-500"> (Ref #{selectedElement.data.source_ref})</span>
                        )}
                      </p>
                    </div>
                  )}

                  {/* If officer-created link, permit deletion */}
                  {selectedElement.data.method === 'officer' && !isViewer && (
                    <div className="pt-2 border-t border-[#1e293b]">
                      <button
                        onClick={() => handleDeleteLink(selectedElement.data.source_ref)}
                        className="w-full px-2.5 py-1.5 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 text-xs font-semibold rounded transition-colors"
                      >
                        Delete Officer Annotation
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Compliance Footer in Drawer */}
            <div className="pt-4 border-t border-[#1e293b] text-[10px] text-slate-500 font-mono">
              Legally Admissible Under Section 63 BSA 2023. Unalterable Cryptographic Audit Logged.
            </div>
          </div>
        )}
      </div>

      {/* 4. Officer Link Creation Modal */}
      {linkModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#0b1120] border border-[#1e293b] rounded-lg max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] mb-4">
              <div>
                <h3 className="text-sm font-bold text-white">Create Officer Link Annotation</h3>
                <p className="text-xs text-slate-400">Explicit relationship binding between entities</p>
              </div>
              <button
                onClick={() => setLinkModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs font-mono"
              >
                [X]
              </button>
            </div>

            <form onSubmit={handleCreateLink} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Source Person / Subject Entity
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Ramesh Kumar"
                  value={linkSource}
                  onChange={(e) => setLinkSource(e.target.value)}
                  className="w-full bg-[#030712] border border-[#334155] focus:border-[#0284c7] px-3 py-2 rounded text-xs text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Relationship Type
                </label>
                <select
                  value={linkType}
                  onChange={(e) => setLinkType(e.target.value)}
                  className="w-full bg-[#030712] border border-[#334155] px-3 py-2 rounded text-xs text-white focus:outline-none"
                >
                  <option value="USES">USES (Phone / Mobile)</option>
                  <option value="OWNS">OWNS (Bank Account / Asset)</option>
                  <option value="DRIVES">DRIVES (Vehicle / Registration)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Target Identifier
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 9876543210 or 123456789012"
                  value={linkTarget}
                  onChange={(e) => setLinkTarget(e.target.value)}
                  className="w-full bg-[#030712] border border-[#334155] focus:border-[#0284c7] px-3 py-2 rounded text-xs text-white focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-[#1e293b]">
                <button
                  type="button"
                  onClick={() => setLinkModalOpen(false)}
                  className="px-3 py-1.5 bg-[#1e293b] hover:bg-[#334155] text-slate-300 text-xs rounded transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={linkSubmitting}
                  className="px-4 py-1.5 bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-semibold rounded disabled:opacity-50 transition-colors"
                >
                  {linkSubmitting ? 'Recording...' : 'Commit Link'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
