import React, { useEffect, useRef, useState, useCallback } from 'react';
import cytoscape from 'cytoscape';
import {
  Search,
  Filter,
  Maximize2,
  ZoomIn,
  ZoomOut,
  RefreshCw,
  Layers,
  ArrowRightLeft,
  Loader2,
  ShieldAlert,
} from 'lucide-react';
import { graphApi } from '../api/client';
import NodeDetailPanel from './NodeDetailPanel';

export default function GraphExplorer({ caseId, onSwitchToLegacy }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  const [loading, setLoading] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState(null);

  // Filters & Controls
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('ALL');
  const [minWeight, setMinWeight] = useState(0);

  // Data & Styles
  const [config, setConfig] = useState({ node_types: [], edge_types: [] });
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [stats, setStats] = useState({ nodes: 0, edges: 0, total_case_nodes: 0 });

  // 1. Fetch Dynamic Type Configuration (Color, Shape, Legend)
  const loadConfig = useCallback(async () => {
    if (!caseId) return;
    try {
      const cfg = await graphApi.getConfig(caseId);
      setConfig(cfg);
    } catch (err) {
      console.warn('Failed to fetch graph config:', err);
    }
  }, [caseId]);

  // 2. Fetch Graph Topology & Initialize Cytoscape
  const loadGraph = useCallback(
    async (q = searchQuery, typeFilter = selectedType, weight = minWeight) => {
      if (!caseId || !containerRef.current) return;
      setLoading(true);
      setError(null);

      try {
        const res = await graphApi.getNodes(caseId, {
          limit: 300,
          q: q.trim() || undefined,
          node_type: typeFilter !== 'ALL' ? typeFilter : undefined,
          min_weight: weight > 0 ? weight : undefined,
        });

        setStats({
          nodes: res.nodes_count || 0,
          edges: res.edges_count || 0,
          total_case_nodes: res.total_case_nodes || 0,
        });

        // Initialize or update Cytoscape
        if (cyRef.current) {
          cyRef.current.destroy();
        }

        const cy = cytoscape({
          container: containerRef.current,
          elements: res.elements || [],
          style: [
            {
              selector: 'node',
              style: {
                label: 'data(label)',
                'background-color': 'data(color)',
                shape: 'data(shape)',
                color: '#f8fafc',
                'font-size': '11px',
                'font-family': 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                'text-valign': 'bottom',
                'text-margin-y': 5,
                'text-outline-color': '#020617',
                'text-outline-width': 2,
                width: 32,
                height: 32,
                'border-width': 2,
                'border-color': '#334155',
                'transition-property': 'background-color, border-color, width, height',
                'transition-duration': '0.2s',
              },
            },
            {
              selector: 'node:selected',
              style: {
                'border-color': '#38bdf8',
                'border-width': 4,
                width: 40,
                height: 40,
              },
            },
            {
              selector: 'edge',
              style: {
                width: 2,
                'line-color': 'data(color)',
                'line-style': 'data(line_style)',
                'target-arrow-color': 'data(color)',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                opacity: 0.8,
                'arrow-scale': 1.1,
              },
            },
            {
              selector: 'edge:selected',
              style: {
                width: 4,
                opacity: 1,
                'line-color': '#38bdf8',
                'target-arrow-color': '#38bdf8',
              },
            },
          ],
          layout: {
            name: 'cose',
            animate: false,
            randomize: false,
            componentSpacing: 100,
            nodeRepulsion: 400000,
            nodeOverlap: 20,
            idealEdgeLength: 100,
            edgeElasticity: 100,
            nestingFactor: 5,
            gravity: 80,
            numIter: 1000,
            initialTemp: 200,
            coolingFactor: 0.95,
            minTemp: 1.0,
          },
          minZoom: 0.2,
          maxZoom: 3.5,
          wheelSensitivity: 0.3,
        });

        // Click Event: Open Node Details
        cy.on('tap', 'node', (evt) => {
          const nId = evt.target.id();
          setSelectedNodeId(nId);
        });

        // Double Click Event: Expand 1-Hop Neighbours
        cy.on('dbltap', 'node', async (evt) => {
          const targetNode = evt.target;
          const targetNodeId = targetNode.id();
          handleExpandNode(targetNodeId);
        });

        // Tap on Background: Clear Selection
        cy.on('tap', (evt) => {
          if (evt.target === cy) {
            setSelectedNodeId(null);
          }
        });

        cyRef.current = cy;
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'Failed to load graph nodes');
      } finally {
        setLoading(false);
      }
    },
    [caseId, searchQuery, selectedType, minWeight]
  );

  useEffect(() => {
    loadConfig();
    loadGraph();
  }, [caseId]);

  // Expand Node Neighbours On-Demand (1-Hop)
  const handleExpandNode = async (nodeId) => {
    if (!cyRef.current || !caseId || !nodeId) return;
    try {
      const res = await graphApi.getNodeNeighbours(caseId, nodeId, { page: 1, page_size: 100 });
      const cy = cyRef.current;
      const originNode = cy.getElementById(nodeId);
      const originPos = originNode.position();

      // Collect new elements to add
      const newElements = [];
      const nodeConfigs = Object.fromEntries(
        (config.node_types || []).map((nt) => [nt.type_name, nt])
      );
      const edgeConfigs = Object.fromEntries(
        (config.edge_types || []).map((et) => [et.type_name, et])
      );

      Object.values(res.grouped_neighbours || {}).forEach((group) => {
        group.forEach((nbr) => {
          if (cy.getElementById(nbr.node_id).length === 0) {
            const style = nodeConfigs[nbr.node_type] || {};
            newElements.push({
              group: 'nodes',
              data: {
                id: nbr.node_id,
                label: nbr.label,
                node_type: nbr.node_type,
                color: style.color || '#64748B',
                shape: style.shape || 'ellipse',
                props: nbr.props || {},
              },
              position: {
                x: originPos.x + (Math.random() - 0.5) * 150,
                y: originPos.y + (Math.random() - 0.5) * 150,
              },
            });
          }

          // Edges
          nbr.connections?.forEach((conn) => {
            const edgeId = conn.edge_id;
            if (cy.getElementById(edgeId).length === 0) {
              const eStyle = edgeConfigs[conn.edge_type] || {};
              const isOutgoing = conn.direction === 'OUTGOING';
              newElements.push({
                group: 'edges',
                data: {
                  id: edgeId,
                  source: isOutgoing ? nodeId : nbr.node_id,
                  target: isOutgoing ? nbr.node_id : nodeId,
                  edge_type: conn.edge_type,
                  count: conn.count,
                  total_paise: conn.total_paise,
                  total_inr: conn.total_inr,
                  color: eStyle.color || '#64748B',
                  line_style: eStyle.line_style || 'solid',
                },
              });
            }
          });
        });
      });

      if (newElements.length > 0) {
        cy.add(newElements);
        cy.animate({
          fit: { eles: cy.elements(), padding: 50 },
          duration: 400,
        });
      }
    } catch (err) {
      console.warn('Expand node failed:', err);
    }
  };

  // Rebuild Graph Trigger
  const handleRebuild = async () => {
    if (!caseId) return;
    setRebuilding(true);
    try {
      await graphApi.rebuild(caseId);
      await loadConfig();
      await loadGraph();
    } catch (err) {
      setError(err.response?.data?.detail || 'Rebuild failed');
    } finally {
      setRebuilding(false);
    }
  };

  return (
    <div className="relative w-full h-[760px] bg-slate-950 border border-slate-800 rounded-lg overflow-hidden flex flex-col">
      {/* Top Controls Toolbar */}
      <div className="p-3 bg-slate-900 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 z-10">
        {/* Left: Search & Filter */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search entity or node..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadGraph(searchQuery, selectedType, minWeight)}
              className="pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-xs text-slate-200 placeholder-slate-500 w-48 sm:w-56 focus:outline-none focus:border-emerald-500 font-mono"
            />
          </div>

          {/* Node Type Filter */}
          <div className="flex items-center gap-1 bg-slate-950 border border-slate-700 rounded px-2 py-1">
            <Filter className="w-3 h-3 text-slate-400" />
            <select
              value={selectedType}
              onChange={(e) => {
                setSelectedType(e.target.value);
                loadGraph(searchQuery, e.target.value, minWeight);
              }}
              className="bg-transparent text-xs text-slate-200 focus:outline-none font-mono cursor-pointer"
            >
              <option value="ALL">All Types</option>
              {config.node_types?.map((nt) => (
                <option key={nt.type_name} value={nt.type_name}>
                  {nt.label}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => loadGraph(searchQuery, selectedType, minWeight)}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 rounded border border-slate-700 transition"
          >
            Apply
          </button>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Zoom & Fit */}
          <div className="flex items-center bg-slate-950 border border-slate-700 rounded overflow-hidden">
            <button
              onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.25)}
              className="p-1.5 hover:bg-slate-800 text-slate-300 transition"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
              className="p-1.5 hover:bg-slate-800 text-slate-300 transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => cyRef.current?.fit(undefined, 40)}
              className="p-1.5 hover:bg-slate-800 text-slate-300 transition border-l border-slate-800"
              title="Fit to Canvas"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Rebuild Graph Button */}
          <button
            onClick={handleRebuild}
            disabled={rebuilding}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded text-xs font-medium transition disabled:opacity-50"
            title="Idempotently rebuild SQLite graph topology"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin' : ''}`} />
            {rebuilding ? 'Rebuilding...' : 'Rebuild'}
          </button>

          {/* Fallback to Legacy Graph */}
          {onSwitchToLegacy && (
            <button
              onClick={onSwitchToLegacy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded border border-slate-700 text-xs transition"
              title="Switch to original graph view"
            >
              <ArrowRightLeft className="w-3.5 h-3.5" />
              Legacy View
            </button>
          )}
        </div>
      </div>

      {/* Main Graph Viewport with Side Inspection Panel */}
      <div className="flex-1 relative flex overflow-hidden">
        {/* Cytoscape Canvas */}
        <div ref={containerRef} className="flex-1 w-full h-full cursor-grab active:cursor-grabbing" />

        {/* Loading Overlay */}
        {loading && (
          <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm flex flex-col items-center justify-center gap-2 text-xs text-slate-300 z-10">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
            <span>Rendering authoritative graph topology...</span>
          </div>
        )}

        {/* Error Banner */}
        {error && (
          <div className="absolute top-4 left-4 right-4 p-3 bg-red-950/80 border border-red-800 rounded-md text-xs text-red-200 z-10">
            {error}
          </div>
        )}

        {/* Selected Node Inspector Drawer */}
        {selectedNodeId && (
          <NodeDetailPanel
            caseId={caseId}
            nodeId={selectedNodeId}
            onClose={() => setSelectedNodeId(null)}
            onExpandNode={handleExpandNode}
          />
        )}
      </div>

      {/* Bottom Status & Dynamic Legend Bar */}
      <div className="p-2.5 bg-slate-900 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400 z-10">
        {/* Left: Render stats */}
        <div className="flex items-center gap-3 font-mono text-[11px]">
          <span>
            Rendered: <strong className="text-white">{stats.nodes}</strong> nodes /{' '}
            <strong className="text-white">{stats.edges}</strong> edges
          </span>
          {stats.total_case_nodes > stats.nodes && (
            <span className="text-amber-400">
              (Capped at {stats.nodes} of {stats.total_case_nodes} total nodes; double-click node to expand)
            </span>
          )}
        </div>

        {/* Right: Dynamic Config Legend */}
        <div className="flex flex-wrap items-center gap-2.5">
          {config.node_types?.map((nt) => (
            <div key={nt.type_name} className="flex items-center gap-1.5 text-[11px]">
              <span
                className="w-2.5 h-2.5 rounded-full inline-block"
                style={{ backgroundColor: nt.color }}
              />
              <span className="text-slate-300">{nt.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
