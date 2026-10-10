import React, { useEffect, useRef, useState, useCallback } from 'react';
import cytoscape from 'cytoscape';

const NODE_COLORS = {
  Person: '#3b82f6',       // Electric Blue
  Phone: '#06b6d4',        // Cyan
  BankAccount: '#10b981',  // Emerald Green
  Vehicle: '#f59e0b',      // Amber
  FIR: '#a855f7',          // Purple
  Organization: '#6366f1', // Indigo
  Default: '#64748b'       // Slate
};

const LAYOUT_CONFIGS = {
  cose: {
    name: 'cose',
    animate: true,
    animationDuration: 800,
    fit: true,
    padding: 90,
    nodeDimensionsIncludeLabels: true,
    idealEdgeLength: 160,
    nodeRepulsion: 7500000,
    nodeOverlap: 25,
    componentSpacing: 180,
    gravity: 0.25,
    numIter: 1000,
    coolingFactor: 0.95
  },
  concentric: {
    name: 'concentric',
    animate: true,
    animationDuration: 700,
    fit: true,
    padding: 80,
    spacingFactor: 1.8,
    concentric: (node) => (node.data('is_prime') ? 10 : node.degree()),
    levelWidth: () => 2
  },
  circle: {
    name: 'circle',
    animate: true,
    animationDuration: 600,
    fit: true,
    padding: 90,
    spacingFactor: 1.6
  },
  breadthfirst: {
    name: 'breadthfirst',
    animate: true,
    animationDuration: 700,
    fit: true,
    padding: 90,
    spacingFactor: 1.8,
    directed: true
  }
};

export default function DynamicInvestigationGraph({
  nodes = [],
  edges = [],
  primeSuspectId = null,
  highlightTargetId = null
}) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [currentLayout, setCurrentLayout] = useState('cose');
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Initialize and update Cytoscape graph
  useEffect(() => {
    if (!containerRef.current || !nodes || nodes.length === 0) return;

    const elements = [
      ...nodes.map((n) => {
        const isPrime = n.data?.id === primeSuspectId || n.data?.is_prime;
        return {
          group: 'nodes',
          data: {
            id: n.data.id,
            label: n.data.label || n.data.id,
            type: n.data.type || 'Entity',
            is_prime: isPrime,
            degree: n.data.degree || 1,
            role: n.data.role || (isPrime ? 'Prime Suspect' : `${n.data.type || 'Entity'}`),
            risk_score: n.data.risk_score || (isPrime ? 95 : 50),
            threat_level: n.data.threat_level || (isPrime ? 'CRITICAL' : 'NORMAL'),
            rationale: n.data.rationale || [
              `Correlated evidentiary node linked across active investigation records.`
            ]
          }
        };
      }),
      ...edges.map((e, idx) => ({
        group: 'edges',
        data: {
          id: e.data.id || `edge_${idx}`,
          source: e.data.source,
          target: e.data.target,
          label: e.data.amount ? `${e.data.label} (${e.data.amount})` : e.data.label || '',
          raw_label: e.data.label || '',
          amount: e.data.amount || ''
        }
      }))
    ];

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      wheelSensitivity: 0.25,
      minZoom: 0.1,
      maxZoom: 4.5,
      boxSelectionEnabled: false,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            color: '#f8fafc',
            'font-size': '11px',
            'font-weight': 'bold',
            'font-family': 'monospace',
            'text-valign': 'bottom',
            'text-margin-y': 7,
            'text-background-opacity': 0.85,
            'text-background-color': '#030712',
            'text-background-padding': '3px',
            'text-background-shape': 'roundrectangle',
            width: (ele) => (ele.data('is_prime') ? 52 : 36),
            height: (ele) => (ele.data('is_prime') ? 52 : 36),
            'background-color': (ele) => {
              if (ele.data('is_prime')) return '#f43f5e';
              return NODE_COLORS[ele.data('type')] || NODE_COLORS.Default;
            },
            'border-width': (ele) => (ele.data('is_prime') ? 4 : 2.5),
            'border-color': (ele) => (ele.data('is_prime') ? '#ffe4e6' : '#1e293b'),
            'shadow-blur': (ele) => (ele.data('is_prime') ? 22 : 8),
            'shadow-color': (ele) => (ele.data('is_prime') ? '#f43f5e' : '#0284c7'),
            'shadow-opacity': 0.65,
            'transition-property': 'background-color, border-color, width, height, opacity',
            'transition-duration': '0.3s'
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-color': '#38bdf8',
            'border-width': 4.5,
            'shadow-blur': 26,
            'shadow-color': '#38bdf8',
            'shadow-opacity': 0.95
          }
        },
        {
          selector: 'edge',
          style: {
            width: 2.2,
            'line-color': '#334155',
            'target-arrow-color': '#38bdf8',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '9.5px',
            'font-family': 'monospace',
            color: '#cbd5e1',
            'text-rotation': 'autorotate',
            'text-background-opacity': 0.9,
            'text-background-color': '#070d1d',
            'text-background-padding': '3px',
            'text-background-shape': 'roundrectangle',
            'arrow-scale': 1.15,
            'transition-property': 'line-color, target-arrow-color, width, opacity',
            'transition-duration': '0.3s'
          }
        },
        {
          selector: 'edge:selected',
          style: {
            width: 3.8,
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            color: '#38bdf8'
          }
        },
        {
          selector: '.faded',
          style: {
            opacity: 0.18
          }
        },
        {
          selector: '.highlighted',
          style: {
            opacity: 1,
            'border-color': '#38bdf8',
            'border-width': 3.5
          }
        }
      ],
      layout: LAYOUT_CONFIGS[currentLayout] || LAYOUT_CONFIGS.cose
    });

    // Node Click Listener: Highlighting & Inspector Details
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      highlightNodeNeighborhood(cy, node);

      const connectedEdges = node.connectedEdges();
      const connectedNodes = node.neighborhood('node');

      const connectedList = connectedNodes.map((nbr) => {
        const edge = connectedEdges.filter((e) => e.connectedNodes().contains(nbr))[0];
        return {
          id: nbr.data('id'),
          label: nbr.data('label'),
          type: nbr.data('type'),
          is_prime: nbr.data('is_prime'),
          relationship: edge ? edge.data('label') : 'CONNECTED'
        };
      });

      setSelectedNode({
        id: node.data('id'),
        label: node.data('label'),
        type: node.data('type'),
        is_prime: node.data('is_prime'),
        degree: connectedEdges.length,
        role: node.data('role'),
        risk_score: node.data('risk_score'),
        threat_level: node.data('threat_level'),
        rationale: node.data('rationale'),
        connected: connectedList
      });

      // Smooth camera focus
      cy.animate({
        center: { eles: node },
        duration: 400
      });
    });

    // Canvas Background Click Listener: Reset selection
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        resetHighlights(cy);
        setSelectedNode(null);
      }
    });

    cyRef.current = cy;

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [nodes, edges, primeSuspectId]);

  // Highlight specific target if requested externally
  useEffect(() => {
    if (!cyRef.current || !highlightTargetId) return;
    const cy = cyRef.current;
    const targetNode = cy.getElementById(highlightTargetId);
    if (targetNode && targetNode.length > 0) {
      targetNode.trigger('tap');
    }
  }, [highlightTargetId]);

  // Neighborhood highlight helper
  const highlightNodeNeighborhood = (cy, node) => {
    cy.batch(() => {
      cy.elements().removeClass('highlighted').addClass('faded');
      node.removeClass('faded').addClass('highlighted');
      node.neighborhood().removeClass('faded').addClass('highlighted');
    });
  };

  // Reset highlight helper
  const resetHighlights = (cy) => {
    cy.batch(() => {
      cy.elements().removeClass('faded').removeClass('highlighted');
    });
  };

  // Navigation & Zoom Handlers
  const handleZoomIn = () => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    cy.animate({
      zoom: cy.zoom() * 1.35,
      duration: 250
    });
  };

  const handleZoomOut = () => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    cy.animate({
      zoom: cy.zoom() * 0.75,
      duration: 250
    });
  };

  const handleFit = () => {
    if (!cyRef.current) return;
    cyRef.current.animate({
      fit: { padding: 80 },
      duration: 400
    });
  };

  const handleCenter = () => {
    if (!cyRef.current) return;
    cyRef.current.animate({
      center: { eles: cyRef.current.elements() },
      duration: 350
    });
  };

  const handleLayoutSwitch = (layoutName) => {
    if (!cyRef.current) return;
    setCurrentLayout(layoutName);
    const config = LAYOUT_CONFIGS[layoutName] || LAYOUT_CONFIGS.cose;
    cyRef.current.layout(config).run();
  };

  const handleSelectConnectedNode = (nodeId) => {
    if (!cyRef.current) return;
    const node = cyRef.current.getElementById(nodeId);
    if (node && node.length > 0) {
      node.trigger('tap');
    }
  };

  return (
    <div
      className={`relative w-full bg-[#050914] rounded-2xl border border-[#162238] overflow-hidden shadow-2xl flex flex-col select-none transition-all duration-300 ${
        isFullscreen ? 'fixed inset-4 z-50 h-[calc(100vh-32px)]' : 'h-[620px]'
      }`}
    >
      {/* Top Header Control Strip */}
      <div className="absolute top-3 left-3 right-3 z-10 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        {/* Left: Legend Pills */}
        <div className="flex flex-wrap items-center gap-1.5 bg-[#080d1d]/90 backdrop-blur-md px-2.5 py-1.5 rounded-xl border border-[#1b2b48] shadow-lg pointer-events-auto">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono text-rose-300 bg-rose-950/70 border border-rose-800 font-semibold shadow-sm">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
            Prime Suspect
          </div>
          <div className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono text-blue-300 bg-blue-950/50 border border-blue-900/40">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
            Person
          </div>
          <div className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono text-cyan-300 bg-cyan-950/50 border border-cyan-900/40">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
            Phone
          </div>
          <div className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono text-emerald-300 bg-emerald-950/50 border border-emerald-900/40">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Account
          </div>
          <div className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono text-amber-300 bg-amber-950/50 border border-amber-900/40">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            Vehicle
          </div>
          <div className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono text-purple-300 bg-purple-950/50 border border-purple-900/40">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
            FIR
          </div>
        </div>

        {/* Right: Interactive Navigation Bar */}
        <div className="flex items-center gap-1.5 bg-[#080d1d]/90 backdrop-blur-md p-1.5 rounded-xl border border-[#1b2b48] shadow-lg pointer-events-auto">
          {/* Layout Selector */}
          <select
            value={currentLayout}
            onChange={(e) => handleLayoutSwitch(e.target.value)}
            className="bg-[#0b1326] text-[11px] font-mono text-slate-200 px-2.5 py-1 rounded-lg border border-[#1e2f50] focus:outline-none cursor-pointer hover:border-blue-500 transition-colors"
          >
            <option value="cose">Physics (Cose Spacious)</option>
            <option value="concentric">Concentric (Hubs)</option>
            <option value="circle">Circular Ring</option>
            <option value="breadthfirst">Hierarchical Flow</option>
          </select>

          {/* Zoom In */}
          <button
            onClick={handleZoomIn}
            title="Zoom In (+)"
            className="w-7 h-7 flex items-center justify-center rounded-lg bg-[#0b1326] hover:bg-blue-600/30 text-slate-200 hover:text-white border border-[#1e2f50] font-bold text-sm transition-colors"
          >
            +
          </button>

          {/* Zoom Out */}
          <button
            onClick={handleZoomOut}
            title="Zoom Out (-)"
            className="w-7 h-7 flex items-center justify-center rounded-lg bg-[#0b1326] hover:bg-blue-600/30 text-slate-200 hover:text-white border border-[#1e2f50] font-bold text-sm transition-colors"
          >
            -
          </button>

          {/* Fit to Screen */}
          <button
            onClick={handleFit}
            title="Fit Entire Graph"
            className="px-2.5 py-1 rounded-lg bg-[#0b1326] hover:bg-blue-600/30 text-[10px] font-mono text-slate-200 hover:text-white border border-[#1e2f50] transition-colors"
          >
            Fit
          </button>

          {/* Center */}
          <button
            onClick={handleCenter}
            title="Center View"
            className="px-2 py-1 rounded-lg bg-[#0b1326] hover:bg-blue-600/30 text-[10px] font-mono text-slate-200 hover:text-white border border-[#1e2f50] transition-colors"
          >
            Center
          </button>

          {/* Fullscreen Toggle */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? 'Exit Fullscreen' : 'Expand Fullscreen'}
            className="px-2.5 py-1 rounded-lg bg-[#142240] hover:bg-blue-600 text-[10px] font-mono text-cyan-300 hover:text-white border border-blue-500/40 transition-colors"
          >
            {isFullscreen ? 'Exit [X]' : 'Expand ⛶'}
          </button>
        </div>
      </div>

      {/* Main Cytoscape Canvas */}
      <div
        ref={containerRef}
        className="w-full h-full cursor-grab active:cursor-grabbing"
        style={{
          backgroundImage:
            'radial-gradient(circle at 1px 1px, rgba(30, 41, 59, 0.45) 1px, transparent 0)',
          backgroundSize: '26px 26px'
        }}
      />

      {/* Forensic Intelligence Node Inspector Drawer */}
      {selectedNode && (
        <div className="absolute bottom-4 left-4 max-w-md w-full bg-[#080d1d]/95 backdrop-blur-xl border border-[#223558] rounded-2xl p-5 shadow-2xl z-20 animate-fadeIn space-y-3.5">
          {/* Header */}
          <div className="flex items-start justify-between gap-3 border-b border-[#182642] pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded font-bold tracking-wider inline-block ${
                    selectedNode.is_prime
                      ? 'bg-rose-950 text-rose-300 border border-rose-800'
                      : 'bg-blue-950 text-blue-300 border border-blue-800'
                  }`}
                >
                  {selectedNode.is_prime ? 'PRIME CRIMINAL TARGET' : selectedNode.type}
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  {selectedNode.role}
                </span>
              </div>
              <h4 className="text-base font-bold text-white mt-1 truncate">
                {selectedNode.label}
              </h4>
            </div>

            <button
              onClick={() => {
                setSelectedNode(null);
                if (cyRef.current) resetHighlights(cyRef.current);
              }}
              className="text-slate-400 hover:text-white text-xs font-mono p-1 rounded-md hover:bg-[#152340]"
            >
              ✕
            </button>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 gap-2 bg-[#060a17] p-2.5 rounded-xl border border-[#142038] text-[11px] font-mono">
            <div>
              <span className="text-slate-500">Threat Rating:</span>
              <div className="text-rose-400 font-bold mt-0.5">
                {selectedNode.risk_score}% ({selectedNode.threat_level})
              </div>
            </div>
            <div>
              <span className="text-slate-500">Network Connections:</span>
              <div className="text-cyan-400 font-bold mt-0.5">
                {selectedNode.degree} Direct Link(s)
              </div>
            </div>
          </div>

          {/* Forensic Reasons & Evidence Justification */}
          <div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-amber-400 mb-1.5 font-bold flex items-center gap-1.5">
              <span>⚠️</span>
              <span>Forensic Attribution Rationale:</span>
            </div>
            <ul className="space-y-1 text-xs text-slate-300 bg-[#060a17] p-3 rounded-xl border border-[#142038]">
              {(selectedNode.rationale || []).map((reason, i) => (
                <li key={i} className="flex items-start gap-1.5 leading-relaxed">
                  <span className="text-rose-400 mt-0.5">▸</span>
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Connected Entities Chips */}
          {selectedNode.connected?.length > 0 && (
            <div>
              <div className="text-slate-400 mb-1.5 text-[10px] font-mono uppercase tracking-wider">
                Direct Linked Entities ({selectedNode.connected.length}):
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto pr-1">
                {selectedNode.connected.map((c, i) => (
                  <button
                    key={i}
                    onClick={() => handleSelectConnectedNode(c.id)}
                    className="px-2 py-1 rounded-lg text-[10px] font-mono bg-[#0f172a] hover:bg-blue-600/30 border border-[#1e293b] hover:border-blue-400 text-slate-300 hover:text-white transition-all text-left flex items-center gap-1.5"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    <span className="truncate max-w-[120px] font-semibold">{c.label}</span>
                    <span className="text-[9px] text-slate-500">({c.relationship})</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
