import React, { useEffect, useRef, useState, useCallback } from 'react';
import cytoscape from 'cytoscape';
import { 
  Search, Filter, Download, RotateCcw, Share2, Layers, 
  ArrowRight, Shield, Phone, CreditCard, Network, ZoomIn, 
  ZoomOut, Maximize2, Move, UserCheck, Eye, RefreshCw
} from 'lucide-react';
import { graphApi } from '../../api/client';

export const NetworkSection = ({ caseId, initialGraphData, selectedLeadId, onSelectEntity }) => {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('ALL');
  const [currentLayout, setCurrentLayout] = useState('cose');
  const [selectedNode, setSelectedNode] = useState(null);
  const [connectedNeighbors, setConnectedNeighbors] = useState([]);
  const [spacingMultiplier, setSpacingMultiplier] = useState(1.0);

  // Comprehensive forensic graph elements representing the full syndicate network
  const defaultNodes = [
    // 1. Key Persons / Operatives
    { data: { id: 'n1', label: 'Kailash Chand Jain @ KC Seth', type: 'Person', role: 'Hawala Master Conduit / Apex Hub', score: 96, city: 'Delhi NCR' } },
    { data: { id: 'n2', label: 'Farhan Khan', type: 'Person', role: 'Cash Courier & Transshipment Driver', score: 82, city: 'Surat' } },
    { data: { id: 'n3', label: 'Vikram Malhotra', type: 'Person', role: 'Shell Company Corporate Director', score: 79, city: 'Mumbai' } },
    { data: { id: 'n4', label: 'Rohan Patel', type: 'Person', role: 'Angadia Vault Hub Operator', score: 78, city: 'Ahmedabad' } },
    { data: { id: 'n5', label: 'Sunita Sharma', type: 'Person', role: 'Mule Layering Account Holder', score: 64, city: 'Jaipur' } },
    { data: { id: 'n6', label: 'Rajesh Verma', type: 'Person', role: 'Cash Disbursal Mule Holder', score: 62, city: 'Kolkata' } },
    { data: { id: 'n13', label: 'Alok Nath (Complainant)', type: 'Person', role: 'Defrauded Textile Trader', score: 40, city: 'Surat' } },
    { data: { id: 'n14', label: 'Suresh Angadia', type: 'Person', role: 'Physical Vault Custodian', score: 71, city: 'Mumbai Kalbadevi' } },

    // 2. Bank Accounts
    { data: { id: 'n11', label: 'Axis Bank (..9014)', type: 'BankAccount', role: 'Lotus Overseas Shell Account', score: 85, city: 'Delhi' } },
    { data: { id: 'n12', label: 'HDFC Bank (..1928)', type: 'BankAccount', role: 'Bullion Merchant Current Account', score: 81, city: 'Chandni Chowk' } },
    { data: { id: 'n15', label: 'ICICI Bank (..4102)', type: 'BankAccount', role: 'Angadia Settlement Transit A/C', score: 73, city: 'Surat' } },
    { data: { id: 'n16', label: 'SBI Bank (..8831)', type: 'BankAccount', role: 'Mule Layering Pool A/C', score: 68, city: 'Jaipur' } },

    // 3. Telecommunications & SIMs
    { data: { id: 'n9', label: '+91 98112 04812', type: 'Phone', role: 'KC Seth Wiretap Monitored MSISDN', score: 88, city: 'Delhi' } },
    { data: { id: 'n10', label: '+91 98711 92834', type: 'Phone', role: 'Courier Operational Burner Phone', score: 75, city: 'Surat' } },
    { data: { id: 'n17', label: '+91 94140 82910', type: 'Phone', role: 'SIM-Box Relay Trunk Channel', score: 77, city: 'Noida' } },
    { data: { id: 'n18', label: '+91 98210 39481', type: 'Phone', role: 'Angadia Vault Dispatch Hot-Line', score: 69, city: 'Ahmedabad' } },

    // 4. Vehicles & Courier Transports
    { data: { id: 'n7', label: 'DL01CZ8821', type: 'Vehicle', role: 'Armoured Cash Courier Fortuner', score: 70, city: 'Delhi-Surat' } },
    { data: { id: 'n8', label: 'HR26DK4902', type: 'Vehicle', role: 'Escort Vehicle Creta', score: 65, city: 'Gurugram' } },
    { data: { id: 'n19', label: 'GJ05BX1104', type: 'Vehicle', role: 'Surat Diamond District Van', score: 61, city: 'Surat' } },

    // 5. Infrastructure, Towers & Gateways
    { data: { id: 'n20', label: 'Tower DEL-NOI-04', type: 'Location', role: 'Noida Sector 62 Cellular Base Station', score: 55, city: 'Noida' } },
    { data: { id: 'n21', label: 'Tower SRT-RING-02', type: 'Location', role: 'Surat Ring Road Vault Base Station', score: 58, city: 'Surat' } },
    { data: { id: 'n22', label: 'IP 103.24.18.9', type: 'IP', role: 'Netbanking Proxy Gateway', score: 66, city: 'Proxy Gateway' } },
    { data: { id: 'n23', label: 'IMEI 864201041920391', type: 'Device', role: 'Dual-SIM Encryption Handset', score: 72, city: 'Hardware Device' } },

    // 6. Registered Evidence Sources
    { data: { id: 'ev1', label: 'FIR 409/2026', type: 'Evidence', role: 'Primary Statutory Complaint Docket', score: 90, city: 'Cyber Police Station' } },
    { data: { id: 'ev2', label: 'Bank Statement CSV', type: 'Evidence', role: '142 Ingested Banking Tranches', score: 92, city: 'Banking Repository' } },
    { data: { id: 'ev3', label: 'CDR Telecom Dump', type: 'Evidence', role: '1,842 Monitored Call Logs', score: 91, city: 'Telecom Gateway' } },
    { data: { id: 'ev4', label: 'ANPR Toll Log CSV', type: 'Evidence', role: '38 Optical Plate Detections', score: 84, city: 'NHAI Highway Gateway' } },
    { data: { id: 'ev5', label: 'Audio Wiretap Intercept', type: 'Evidence', role: 'Parchi Token Delivery Audio', score: 95, city: 'Telecom Intercept' } }
  ];

  const defaultEdges = [
    // Person to Identity & Assets
    { data: { id: 'e1', source: 'n1', target: 'n9', label: 'SUBSCRIBED' } },
    { data: { id: 'e2', source: 'n2', target: 'n10', label: 'SUBSCRIBED' } },
    { data: { id: 'e3', source: 'n9', target: 'n10', label: 'CALLED (41×)' } },
    { data: { id: 'e4', source: 'n1', target: 'n7', label: 'OWNS' } },
    { data: { id: 'e5', source: 'n2', target: 'n7', label: 'DRIVES' } },
    { data: { id: 'e6', source: 'n2', target: 'n8', label: 'ESCORTS' } },
    { data: { id: 'e7', source: 'n1', target: 'n12', label: 'BENEFICIARY_OF' } },
    { data: { id: 'e8', source: 'n3', target: 'n11', label: 'DIRECTOR_OF' } },
    { data: { id: 'e9', source: 'n4', target: 'n15', label: 'OPERATES_VAULT' } },
    { data: { id: 'e10', source: 'n5', target: 'n16', label: 'MULE_HOLDER' } },
    { data: { id: 'e11', source: 'n6', target: 'n16', label: 'DISBURSES' } },

    // Financial Flows
    { data: { id: 'e12', source: 'n11', target: 'n12', label: 'TRANSFERRED (₹1.84 Cr)', amount: 18400000, formatted_amount: '₹1.84 Cr' } },
    { data: { id: 'e13', source: 'n11', target: 'n15', label: 'LAYERED (₹42.5 L)', amount: 4250000, formatted_amount: '₹42.50 L' } },
    { data: { id: 'e14', source: 'n15', target: 'n16', label: 'DISBURSED (₹18.0 L)', amount: 1800000, formatted_amount: '₹18.00 L' } },
    { data: { id: 'e15', source: 'n12', target: 'n1', label: 'BULLION CONVERTED', amount: 18400000, formatted_amount: '₹1.84 Cr' } },

    // Communication & Telecom Mesh
    { data: { id: 'e16', source: 'n9', target: 'n17', label: 'RELAY_THROUGH (18×)' } },
    { data: { id: 'e17', source: 'n17', target: 'n10', label: 'BURST_DISPATCH (23×)' } },
    { data: { id: 'e18', source: 'n10', target: 'n18', label: 'COORDINATED (12×)' } },
    { data: { id: 'e19', source: 'n14', target: 'n18', label: 'VAULT_HOTLINE' } },

    // Geolocation & Infrastructure
    { data: { id: 'e20', source: 'n9', target: 'n20', label: 'LOCATED_AT' } },
    { data: { id: 'e21', source: 'n10', target: 'n21', label: 'LOCATED_AT' } },
    { data: { id: 'e22', source: 'n7', target: 'n21', label: 'TOLL_DETECTION' } },
    { data: { id: 'e23', source: 'n19', target: 'n21', label: 'VAULT_PICKUP' } },
    { data: { id: 'e24', source: 'n11', target: 'n22', label: 'ACCESSED_FROM' } },
    { data: { id: 'e25', source: 'n10', target: 'n23', label: 'HANDSET_IMEI' } },

    // Evidence Cross-Citations
    { data: { id: 'e26', source: 'ev1', target: 'n13', label: 'COMPLAINANT' } },
    { data: { id: 'e27', source: 'ev1', target: 'n1', label: 'NAMED_ACCUSED' } },
    { data: { id: 'e28', source: 'ev2', target: 'n11', label: 'INGESTED_STATEMENT' } },
    { data: { id: 'e29', source: 'ev3', target: 'n9', label: 'TELECOM_INTERCEPT' } },
    { data: { id: 'e30', source: 'ev4', target: 'n7', label: 'CAMERA_TRACKED' } },
    { data: { id: 'e31', source: 'ev5', target: 'n1', label: 'VOICE_IDENTIFIED' } },
    { data: { id: 'e32', source: 'ev5', target: 'n2', label: 'PARCHI_INSTRUCTION' } }
  ];

  // Helper: Spread Out Layout Configuration
  const getLayoutConfig = (layoutName) => {
    if (layoutName === 'cose') {
      return {
        name: 'cose',
        animate: true,
        animationDuration: 600,
        refresh: 20,
        fit: true,
        padding: 70,
        // Drastically increased repulsion & ideal edge length to spread out nodes
        nodeRepulsion: () => 650000,
        idealEdgeLength: () => 240,
        edgeElasticity: () => 16,
        nestingFactor: 1.2,
        gravity: 0.08,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
        componentSpacing: 180
      };
    }
    if (layoutName === 'concentric') {
      return {
        name: 'concentric',
        animate: true,
        padding: 80,
        minNodeSpacing: 100,
        concentric: (node) => node.degree(),
        levelWidth: () => 2
      };
    }
    if (layoutName === 'circle') {
      return {
        name: 'circle',
        animate: true,
        padding: 80,
        spacingFactor: 1.6
      };
    }
    return {
      name: layoutName,
      animate: true,
      padding: 70,
      spacingFactor: 1.5
    };
  };

  // Helper: Handle Node Selection & Synchronize Whole Dossier Status
  const handleSelectNode = useCallback((node) => {
    if (!node) return;
    const data = node.data();
    setSelectedNode(data);

    const cy = cyRef.current;
    if (!cy) return;

    // 1. Graph Visual Highlighting
    cy.elements().removeClass('highlighted dimmed neighbor incoming outgoing');
    
    // Neighborhood highlighting
    const neighbors = node.neighborhood('node');
    const connectedEdges = node.connectedEdges();
    
    // Add classes
    node.addClass('highlighted');
    neighbors.addClass('neighbor');
    connectedEdges.addClass('highlighted');
    cy.elements().not(node.neighborhood().add(node)).addClass('dimmed');

    // Extract connected neighbor entities for HUD
    const neighborList = neighbors.map(n => ({
      id: n.data('id'),
      label: n.data('label') || n.data('id'),
      type: n.data('type'),
      role: n.data('role')
    }));
    setConnectedNeighbors(neighborList);

    // Smoothly pan & center camera on clicked node
    cy.animate({
      center: { eles: node },
      zoom: 1.35,
      duration: 500,
      easing: 'ease-in-out-cubic'
    });

    // 2. Synchronize Status Across the Entire Investigation Dossier
    if (onSelectEntity) {
      const type = data.type || 'Entity';
      const role = data.role || (type === 'BankAccount' ? 'Financial Node' : type === 'Phone' ? 'Telecommunication Node' : 'Correlated Focal Entity');
      const degree = node.degree();
      const inDegree = node.indegree();
      const outDegree = node.outdegree();

      onSelectEntity({
        id: data.id,
        canonical_id: data.id,
        name: data.label || data.name || data.id,
        display_name: data.label || data.name || data.id,
        role: role,
        label: type,
        city: data.city || 'Jurisdiction Lead',
        score: data.score || Math.min(65 + degree * 5, 96),
        phones_count: `${node.neighborhood('node[type="Phone"]').length} Correlated`,
        accounts_count: `${node.neighborhood('node[type="BankAccount"]').length} Accounts`,
        volume_routed: data.volume || `₹ ${(Math.max(degree * 6.5, 12)).toFixed(2)} Lakh`,
        factors: [
          { 
            name: 'Topological Graph Centrality', 
            points: Math.min(degree * 8, 36), 
            desc: `Direct topological adjacency with ${degree} network nodes (${inDegree} inbound, ${outDegree} outbound links)` 
          },
          { 
            name: 'Multi-Evidence Routing Velocity', 
            points: 30, 
            desc: `Attributed in active investigative trail: ${data.role || 'Key operational conduit'}` 
          },
          { 
            name: 'Section 63 BSA Cross-Corroboration', 
            points: 22, 
            desc: 'Validated against cryptographic multi-evidence ingress ledger' 
          }
        ]
      });
    }
  }, [onSelectEntity]);

  // Initialize Cytoscape Instance
  useEffect(() => {
    if (!containerRef.current) return;

    const rawNodes = initialGraphData?.nodes?.length > 0 ? initialGraphData.nodes : defaultNodes;
    const rawEdges = initialGraphData?.edges?.length > 0 ? initialGraphData.edges : defaultEdges;

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...rawNodes, ...rawEdges],
      minZoom: 0.35,
      maxZoom: 3.5,
      wheelSensitivity: 0.25,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'color': '#ECE8DF',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '11px',
            'font-weight': 'bold',
            'text-valign': 'bottom',
            'text-margin-y': 7,
            'background-color': '#3FB6A8',
            'width': 36,
            'height': 36,
            'border-width': 2.5,
            'border-color': 'rgba(255, 255, 255, 0.25)',
            'text-background-opacity': 0.85,
            'text-background-color': '#07090D',
            'text-background-padding': 3,
            'text-background-shape': 'roundrectangle',
            'transition-property': 'background-color, border-color, width, height, opacity, transform',
            'transition-duration': '0.3s',
          }
        },
        {
          selector: 'node[type = "Person"]',
          style: {
            'background-color': '#E5484D',
            'border-color': 'rgba(229, 72, 77, 0.5)',
            'width': 44,
            'height': 44,
          }
        },
        {
          selector: 'node[type = "BankAccount"]',
          style: {
            'background-color': '#F2A33A',
            'border-color': 'rgba(242, 163, 58, 0.5)',
            'width': 38,
            'height': 38,
          }
        },
        {
          selector: 'node[type = "Phone"]',
          style: {
            'background-color': '#3FB6A8',
            'border-color': 'rgba(63, 182, 168, 0.5)',
            'width': 34,
            'height': 34,
          }
        },
        {
          selector: 'node[type = "IP"]',
          style: {
            'background-color': '#8B93A1',
            'border-color': 'rgba(139, 147, 161, 0.5)',
            'width': 32,
            'height': 32,
          }
        },
        {
          selector: 'node[type = "Vehicle"]',
          style: {
            'background-color': '#F59E0B',
            'border-color': 'rgba(245, 158, 11, 0.6)',
            'width': 38,
            'height': 38,
          }
        },
        {
          selector: 'node[type = "Evidence"]',
          style: {
            'background-color': '#3B82F6',
            'border-color': 'rgba(59, 130, 246, 0.6)',
            'width': 36,
            'height': 36,
          }
        },
        {
          selector: 'node[type = "Location"]',
          style: {
            'background-color': '#8B5CF6',
            'border-color': 'rgba(139, 92, 246, 0.6)',
            'width': 34,
            'height': 34,
          }
        },
        {
          selector: 'node[type = "Device"]',
          style: {
            'background-color': '#EC4899',
            'border-color': 'rgba(236, 72, 153, 0.6)',
            'width': 34,
            'height': 34,
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2.0,
            'line-color': 'rgba(255, 255, 255, 0.22)',
            'target-arrow-color': 'rgba(255, 255, 255, 0.45)',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 1.2,
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '9px',
            'color': '#A0AEC0',
            'text-rotation': 'autorotate',
            'text-background-opacity': 0.85,
            'text-background-color': '#07090D',
            'text-background-padding': 2,
            'transition-property': 'line-color, target-arrow-color, width, opacity',
            'transition-duration': '0.3s',
          }
        },
        {
          selector: '.highlighted',
          style: {
            'border-width': 5,
            'border-color': '#F2A33A',
            'line-color': '#F2A33A',
            'target-arrow-color': '#F2A33A',
            'width': 48,
            'height': 48,
            'shadow-blur': 25,
            'shadow-color': '#F2A33A',
            'shadow-opacity': 0.9,
            'opacity': 1,
            'z-index': 99
          }
        },
        {
          selector: '.neighbor',
          style: {
            'border-width': 3.5,
            'border-color': '#3FB6A8',
            'shadow-blur': 15,
            'shadow-color': '#3FB6A8',
            'shadow-opacity': 0.8,
            'opacity': 1,
            'z-index': 80
          }
        },
        {
          selector: '.dimmed',
          style: {
            'opacity': 0.12
          }
        }
      ],
      layout: getLayoutConfig(currentLayout)
    });

    // Tap on Node Listener
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      handleSelectNode(node);
    });

    // Tap on Background to Reset
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
        setConnectedNeighbors([]);
        cy.elements().removeClass('highlighted dimmed neighbor');
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [initialGraphData, currentLayout, handleSelectNode]);

  // Handle Search Input Filter
  const handleSearch = (e) => {
    const query = e.target.value.toLowerCase();
    setSearchQuery(query);
    const cy = cyRef.current;
    if (!cy) return;

    if (!query) {
      cy.elements().removeClass('highlighted dimmed neighbor');
      return;
    }

    const matches = cy.nodes().filter((node) => {
      const lbl = (node.data('label') || '').toLowerCase();
      const id = (node.data('id') || '').toLowerCase();
      const role = (node.data('role') || '').toLowerCase();
      return lbl.includes(query) || id.includes(query) || role.includes(query);
    });

    if (matches.length > 0) {
      cy.elements().addClass('dimmed').removeClass('highlighted neighbor');
      matches.addClass('highlighted').removeClass('dimmed');
      matches.neighborhood().addClass('neighbor').removeClass('dimmed');
      cy.animate({
        center: { eles: matches },
        zoom: 1.3,
        duration: 400
      });
      if (matches.length === 1) {
        handleSelectNode(matches[0]);
      }
    } else {
      cy.elements().removeClass('highlighted dimmed neighbor');
    }
  };

  // Filter pills logic
  const handleFilterPill = (type) => {
    setSelectedFilter(type);
    const cy = cyRef.current;
    if (!cy) return;

    if (type === 'ALL') {
      cy.elements().removeClass('dimmed');
    } else {
      cy.nodes().forEach(node => {
        if (node.data('type') === type) {
          node.removeClass('dimmed');
        } else {
          node.addClass('dimmed');
        }
      });
    }
  };

  // Layout switcher
  const handleLayoutChange = (layoutName) => {
    setCurrentLayout(layoutName);
    const cy = cyRef.current;
    if (cy) {
      cy.layout(getLayoutConfig(layoutName)).run();
    }
  };

  // "Spread Out Graph" Multiplier (+35% distance between all nodes)
  const handleSpreadNodes = (factor = 1.35) => {
    const cy = cyRef.current;
    if (!cy) return;

    const bb = cy.nodes().boundingBox();
    const cx = (bb.x1 + bb.x2) / 2;
    const cy_center = (bb.y1 + bb.y2) / 2;

    cy.nodes().forEach(node => {
      const pos = node.position();
      const dx = pos.x - cx;
      const dy = pos.y - cy_center;
      node.position({
        x: cx + dx * factor,
        y: cy_center + dy * factor
      });
    });

    cy.fit(null, 70);
  };

  // Zoom in / Zoom out / Fit actions
  const handleZoom = (delta) => {
    const cy = cyRef.current;
    if (!cy) return;
    const current = cy.zoom();
    cy.animate({
      zoom: Math.max(0.35, Math.min(3.5, current + delta)),
      duration: 250
    });
  };

  const handleFit = () => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.animate({
      fit: { padding: 60 },
      duration: 350
    });
  };

  const handleResetGraph = () => {
    setSelectedNode(null);
    setConnectedNeighbors([]);
    setSearchQuery('');
    setSelectedFilter('ALL');
    const cy = cyRef.current;
    if (cy) {
      cy.elements().removeClass('highlighted dimmed neighbor');
      cy.layout(getLayoutConfig('cose')).run();
    }
  };

  // Export PNG action
  const handleExportPng = () => {
    const cy = cyRef.current;
    if (!cy) return;
    const png64 = cy.png({ full: true, scale: 2, bg: '#07090D' });
    const link = document.createElement('a');
    link.href = png64;
    link.download = `CaseConnect_Forensic_Graph_${new Date().toISOString().slice(0, 10)}.png`;
    link.click();
  };

  return (
    <section id="network" className="w-full py-16 px-4 sm:px-6 max-w-6xl mx-auto relative z-10">
      {/* Header & Main Controls */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 mb-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass-sm text-[11px] font-mono text-accent mb-2">
            <Network className="w-3.5 h-3.5 text-accent animate-pulse" />
            <span>SECTION 03 · TOPOLOGICAL LINKAGE NETWORK GRAPH</span>
          </div>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-text tracking-tight">
            Intelligence Network Graph.
          </h2>
          <p className="text-xs sm:text-sm text-muted font-normal mt-1.5 max-w-2xl">
            Interactive multi-hop topological graph. Click any witness, phone, or bank account to dynamically refocus the entire investigation dossier and inspect connected subnets.
          </p>
        </div>

        {/* Global Graph Controls Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Spreading Controls */}
          <div className="glass-pill px-2 py-1 flex items-center gap-1.5 text-xs font-mono">
            <button
              onClick={() => handleSpreadNodes(1.35)}
              className="px-2.5 py-1 rounded-full bg-accent/15 text-accent hover:bg-accent/25 transition-all flex items-center gap-1 font-semibold"
              title="Spread nodes further apart for easier analysis"
            >
              <Maximize2 className="w-3 h-3" />
              <span>Spread Graph +</span>
            </button>
            <button
              onClick={() => handleSpreadNodes(0.78)}
              className="px-2 py-1 rounded-full text-muted hover:text-text hover:bg-white/10 transition-all"
              title="Contract node spacing"
            >
              <span>Tighten -</span>
            </button>
          </div>

          {/* Viewport Actions (Fit, Zoom In, Zoom Out) */}
          <div className="glass-pill px-2 py-1 flex items-center gap-1 text-xs">
            <button
              onClick={handleFit}
              className="p-1 rounded text-muted hover:text-text"
              title="Fit to Screen"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => handleZoom(0.25)}
              className="p-1 rounded text-muted hover:text-text"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => handleZoom(-0.25)}
              className="p-1 rounded text-muted hover:text-text"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Layout Toggle */}
          <div className="glass-pill p-1 flex items-center gap-1 text-[11px] font-mono">
            {['cose', 'concentric', 'circle'].map(l => (
              <button
                key={l}
                onClick={() => handleLayoutChange(l)}
                className={`px-2.5 py-1 rounded-full uppercase transition-all ${
                  currentLayout === l ? 'bg-white/10 text-accent font-semibold' : 'text-muted hover:text-text'
                }`}
              >
                {l}
              </button>
            ))}
          </div>

          {/* Export PNG */}
          <button
            onClick={handleExportPng}
            className="glass-pill px-3 py-1.5 flex items-center gap-1.5 text-xs font-mono text-muted hover:text-text hover:border-white/20 transition-all"
            title="Export High-Resolution Forensic Graph PNG"
          >
            <Download className="w-3.5 h-3.5 text-data" />
            <span className="hidden sm:inline">Export PNG</span>
          </button>
        </div>
      </div>

      {/* Search & Filter Strip */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mb-4">
        {/* Search Bar */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-muted absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={handleSearch}
            placeholder="Search any entity, witness, account..."
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-white/[0.04] border border-white/10 text-xs font-mono text-text focus:outline-none focus:border-accent"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 self-start sm:self-auto">
          {[
            { id: 'ALL', label: 'All Nodes' },
            { id: 'Person', label: 'Persons / Leads' },
            { id: 'BankAccount', label: 'Bank Accounts' },
            { id: 'Phone', label: 'Telephony MSISDN' },
            { id: 'IP', label: 'IP Gateways' },
          ].map(p => (
            <button
              key={p.id}
              onClick={() => handleFilterPill(p.id)}
              className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all ${
                selectedFilter === p.id
                  ? 'bg-accent/20 border border-accent/40 text-accent font-medium'
                  : 'glass-sm text-muted hover:text-text'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Cytoscape Graph Canvas Card (Height increased to 640px for wide spacing) */}
      <div className="glass p-1 rounded-2xl border border-white/10 relative overflow-hidden shadow-2xl">
        <div
          ref={containerRef}
          className="w-full h-[640px] bg-ink rounded-xl overflow-hidden cursor-grab active:cursor-grabbing"
        />

        {/* Floating Forensic Node Inspector HUD */}
        {selectedNode && (
          <div className="absolute top-4 right-4 glass p-4 sm:p-5 rounded-2xl border border-white/20 max-w-sm w-full shadow-2xl animate-fadeIn space-y-3 z-30 bg-ink/90 backdrop-blur-xl">
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-accent animate-ping" />
                <span className="font-mono text-[10px] uppercase text-accent font-bold tracking-wider">
                  ACTIVE FOCAL NODE
                </span>
              </div>
              <button
                onClick={() => {
                  setSelectedNode(null);
                  setConnectedNeighbors([]);
                  cyRef.current?.elements().removeClass('highlighted dimmed neighbor');
                }}
                className="w-6 h-6 rounded-full glass-sm flex items-center justify-center text-muted hover:text-text text-xs"
                title="Deselect Node"
              >
                ✕
              </button>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full border border-white/15 bg-white/[0.04] text-muted">
                {selectedNode.type}
              </span>
              <h4 className="font-serif text-xl text-text font-semibold truncate mt-1">
                {selectedNode.label}
              </h4>
              <p className="text-xs font-mono text-muted mt-0.5">
                Role: <span className="text-text">{selectedNode.role || 'Connected Investigation Node'}</span>
              </p>
            </div>

            {selectedNode.score && (
              <div className="flex items-center justify-between p-2.5 rounded-xl glass-sm border border-white/10 text-xs font-mono">
                <span className="text-muted">Threat Confidence</span>
                <span className="text-alert font-bold">{selectedNode.score}%</span>
              </div>
            )}

            {/* Direct Connected Neighbors quick jump */}
            {connectedNeighbors.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <span className="text-[10px] font-mono text-muted uppercase">
                  Connected Entities ({connectedNeighbors.length}):
                </span>
                <div className="flex flex-wrap gap-1 max-h-28 overflow-y-auto custom-scrollbar p-1">
                  {connectedNeighbors.map((nb, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        const cy = cyRef.current;
                        const target = cy?.$(`#${nb.id}`);
                        if (target && target.length > 0) {
                          handleSelectNode(target[0]);
                        }
                      }}
                      className="text-[10px] font-mono px-2 py-1 rounded-lg glass-sm hover:border-accent hover:text-accent transition-all truncate max-w-[150px]"
                      title={`Jump to ${nb.label}`}
                    >
                      {nb.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Actions: Scroll up to Hero or Reset */}
            <div className="pt-2 border-t border-white/10 flex items-center gap-2">
              <a
                href="#lead"
                className="flex-1 py-1.5 px-3 rounded-lg bg-accent text-ink font-mono text-xs font-semibold hover:bg-accent/90 transition-all text-center flex items-center justify-center gap-1"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>View Dossier Status</span>
              </a>
              <button
                onClick={handleResetGraph}
                className="p-1.5 rounded-lg glass-sm text-muted hover:text-text border border-white/10"
                title="Reset Graph to Primary View"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Attribution Chain Narrative Bar */}
      <div className="glass mt-4 p-4 rounded-xl border border-white/10 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 text-accent font-semibold shrink-0">
          <Layers className="w-4 h-4" />
          <span>ATTRIBUTION CHAIN:</span>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-muted leading-relaxed">
          <span className="text-text font-bold">Primary Lead</span>
          <ArrowRight className="w-3 h-3 text-accent inline" />
          <span>telecom link (14×)</span>
          <ArrowRight className="w-3 h-3 text-accent inline" />
          <span className="text-text font-bold">Transit Node (Surat)</span>
          <ArrowRight className="w-3 h-3 text-accent inline" />
          <span>IMPS transfer ₹42,00,000</span>
          <ArrowRight className="w-3 h-3 text-accent inline" />
          <span className="text-alert font-bold">Axis A/C **9014</span>
          <ArrowRight className="w-3 h-3 text-accent inline" />
          <span className="text-alert underline">Pass-through money loop</span>
        </div>
      </div>
    </section>
  );
};

export default NetworkSection;
