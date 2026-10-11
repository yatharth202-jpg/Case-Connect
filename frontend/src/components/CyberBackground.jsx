import React, { useEffect, useRef } from 'react';

/**
 * CyberBackground Component
 * Renders an ambient, holographic background featuring:
 * 1. Stylized tactical SVG contour of the Indian Subcontinent with animated cyber hubs
 * 2. Holographic Cybersecurity Shield & Ashoka Command Emblem with rotating radar sweep
 * 3. Subtle interactive particle mesh that responds gently to mouse movement
 * 
 * Styled with subtle ambient opacity (0.08 - 0.14) so foreground text visibility is 100% crystal clear.
 */
export default function CyberBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    const nodeCount = 45;
    const nodes = [];

    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        radius: Math.random() * 1.8 + 0.8,
        color: i % 3 === 0 ? '#00F0FF' : (i % 2 === 0 ? '#8B5CF6' : '#10B981')
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      // Connect nodes within distance threshold
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(0, 240, 255, ${0.12 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
      }

      // Step and render nodes
      nodes.forEach((node) => {
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.shadowColor = node.color;
        ctx.shadowBlur = 4;
        ctx.fill();
        ctx.shadowBlur = 0;

        node.x += node.vx;
        node.y += node.vy;

        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;
      });

      animId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animId);
    };
  }, []);

  // Strategic Cyber Command Hubs across India
  const commandHubs = [
    { name: 'DELHI HQ', x: 390, y: 270, isHQ: true },
    { name: 'MUMBAI', x: 330, y: 490 },
    { name: 'BENGALURU', x: 400, y: 680 },
    { name: 'HYDERABAD', x: 430, y: 550 },
    { name: 'KOLKATA', x: 580, y: 430 },
    { name: 'CHENNAI', x: 460, y: 700 },
    { name: 'JAIPUR', x: 340, y: 290 },
    { name: 'AHMEDABAD', x: 300, y: 380 },
    { name: 'CHANDIGARH', x: 370, y: 210 },
    { name: 'GUWAHATI', x: 680, y: 340 }
  ];

  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden select-none">
      {/* 1. Base Dark Cyber Vignette Overlay */}
      <div className="absolute inset-0 bg-[#040711]" />

      {/* 2. Interactive Particle Mesh Canvas */}
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full opacity-40" />

      {/* 3. Subtle Cyber Grid Floor Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(0,240,255,0.015)_1px,transparent_1px),linear-gradient(90deg,rgba(0,240,255,0.015)_1px,transparent_1px)] bg-[size:48px_48px] [mask-image:radial-gradient(ellipse_70%_60%_at_50%_50%,#000_60%,transparent_100%)]" />

      {/* 4. Ambient India Map & Cybersecurity Shield Hologram Layer */}
      <div className="absolute inset-0 flex items-center justify-center opacity-10 lg:opacity-12 transition-opacity duration-1000">
        <svg
          viewBox="0 0 1000 950"
          className="w-full h-full max-w-[1200px] max-h-[920px] object-contain drop-shadow-[0_0_35px_rgba(0,240,255,0.25)]"
          fill="none"
        >
          <defs>
            {/* Linear and Radial Gradients */}
            <linearGradient id="indiaMapGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.75" />
              <stop offset="50%" stopColor="#8B5CF6" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0.65" />
            </linearGradient>

            <linearGradient id="shieldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.8" />
              <stop offset="50%" stopColor="#3B82F6" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0.8" />
            </linearGradient>

            <radialGradient id="radarSweepGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.4" />
              <stop offset="60%" stopColor="#00F0FF" stopOpacity="0.08" />
              <stop offset="100%" stopColor="#00F0FF" stopOpacity="0" />
            </radialGradient>

            {/* Glowing filter */}
            <filter id="cyberGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* BACKGROUND CONCENTRIC RADAR RINGS AROUND INDIA */}
          <g transform="translate(100, 0)">
            <circle cx="430" cy="460" r="420" stroke="#00F0FF" strokeWidth="0.8" strokeDasharray="6 6" opacity="0.35" />
            <circle cx="430" cy="460" r="320" stroke="#8B5CF6" strokeWidth="0.8" strokeDasharray="4 8" opacity="0.4" />
            <circle cx="430" cy="460" r="220" stroke="#00F0FF" strokeWidth="1" opacity="0.3" />
            <circle cx="430" cy="460" r="120" stroke="#10B981" strokeWidth="1" strokeDasharray="3 3" opacity="0.4" />

            {/* Rotating Radar Crosshairs */}
            <line x1="430" y1="40" x2="430" y2="880" stroke="#00F0FF" strokeWidth="0.6" strokeDasharray="8 8" opacity="0.25" />
            <line x1="10" y1="460" x2="850" y2="460" stroke="#00F0FF" strokeWidth="0.6" strokeDasharray="8 8" opacity="0.25" />
            <line x1="130" y1="160" x2="730" y2="760" stroke="#8B5CF6" strokeWidth="0.5" strokeDasharray="4 6" opacity="0.2" />
            <line x1="130" y1="760" x2="730" y2="160" stroke="#8B5CF6" strokeWidth="0.5" strokeDasharray="4 6" opacity="0.2" />
          </g>

          {/* STYLIZED TACTICAL INDIA MAP CONTOUR */}
          <g transform="translate(100, 0)">
            {/* India Subcontinent Boundary Path */}
            <path
              d="M 350,60 
                 L 390,45 L 430,48 L 475,80 L 495,125 L 465,165 L 435,195 
                 L 448,212 L 475,238 L 460,260 
                 L 485,268 L 540,280 L 580,288 
                 L 592,278 L 602,295 
                 L 615,296 L 642,305 
                 L 660,285 L 710,278 L 748,305 L 755,335 L 730,360 L 695,372 L 672,410 L 645,405 
                 L 628,382 L 608,358 L 590,405 L 575,455 
                 L 555,490 L 528,552 L 495,622 L 468,700 
                 L 445,762 L 428,822 L 418,852 L 408,822 
                 L 398,778 L 388,718 L 378,648 
                 L 368,598 L 358,538 
                 L 348,478 L 332,428 
                 L 305,422 L 268,432 L 255,398 L 285,378 L 235,368 L 218,338 L 255,318 
                 L 278,298 L 298,248 L 328,198 L 348,158 L 338,118 Z"
              stroke="url(#indiaMapGrad)"
              strokeWidth="2.4"
              fill="rgba(0, 240, 255, 0.03)"
              filter="url(#cyberGlow)"
              className="transition-all duration-1000"
            />

            {/* Inner Topographic Grid Mesh Lines of India */}
            <path
              d="M 350,150 L 450,150 M 320,250 L 550,250 M 270,350 L 680,350 M 320,450 L 570,450 M 350,550 L 510,550 M 370,650 L 480,650 M 400,750 L 450,750"
              stroke="#00F0FF"
              strokeWidth="0.6"
              strokeDasharray="4 6"
              opacity="0.25"
            />
            <path
              d="M 330,200 L 330,450 M 390,100 L 390,750 M 450,100 L 450,720 M 520,280 L 520,550 M 600,300 L 600,420"
              stroke="#8B5CF6"
              strokeWidth="0.6"
              strokeDasharray="4 6"
              opacity="0.2"
            />

            {/* Connecting Telemetry Tracers from Delhi HQ to Other Zonal Command Hubs */}
            {commandHubs.map((hub, idx) => {
              if (hub.isHQ) return null;
              return (
                <g key={`tracer-${idx}`}>
                  <line
                    x1={390}
                    y1={270}
                    x2={hub.x}
                    y2={hub.y}
                    stroke="#00F0FF"
                    strokeWidth="1"
                    strokeDasharray="3 4"
                    opacity="0.35"
                  />
                </g>
              );
            })}

            {/* Command Hub Node Markers */}
            {commandHubs.map((hub, idx) => (
              <g key={`hub-${idx}`} transform={`translate(${hub.x}, ${hub.y})`}>
                {/* Glowing Outer Beacon Ping */}
                <circle
                  cx="0"
                  cy="0"
                  r={hub.isHQ ? "14" : "9"}
                  fill="none"
                  stroke={hub.isHQ ? "#00F0FF" : "#10B981"}
                  strokeWidth="1.2"
                  opacity="0.6"
                  className="animate-ping"
                  style={{ animationDuration: hub.isHQ ? '2.5s' : '4s' }}
                />
                {/* Fixed Border Ring */}
                <circle
                  cx="0"
                  cy="0"
                  r={hub.isHQ ? "7" : "4.5"}
                  fill={hub.isHQ ? "#00F0FF" : "#10B981"}
                  fillOpacity="0.8"
                  stroke="#ffffff"
                  strokeWidth="1"
                />
                {/* Tactical Node Label */}
                <text
                  x={hub.isHQ ? "16" : "10"}
                  y="4"
                  fill={hub.isHQ ? "#00F0FF" : "#94A3B8"}
                  fontSize={hub.isHQ ? "11" : "8"}
                  fontWeight="bold"
                  fontFamily="'Share Tech Mono', monospace"
                  letterSpacing="1"
                >
                  {hub.name}
                </text>
              </g>
            ))}
          </g>

          {/* CENTRAL HOLOGRAPHIC CYBERSECURITY SHIELD & ASHOKA COMMAND EMBLEM */}
          <g transform="translate(480, 440) scale(0.85)">
            {/* Outer Hexagonal Cyber Ring */}
            <polygon
              points="0,-160 138,-80 138,80 0,160 -138,80 -138,-80"
              stroke="#00F0FF"
              strokeWidth="1.5"
              strokeDasharray="8 6"
              fill="none"
              opacity="0.5"
            />

            {/* Inner Rotating Tactical Ring */}
            <circle cx="0" cy="0" r="130" stroke="#8B5CF6" strokeWidth="1" strokeDasharray="4 6" opacity="0.6" />
            <circle cx="0" cy="0" r="110" stroke="#00F0FF" strokeWidth="1.2" opacity="0.4" />

            {/* High-Tech Shield Outline */}
            <path
              d="M 0,-95 
                 C 55,-95 85,-85 95,-70 
                 C 95,10 65,75 0,110 
                 C -65,75 -95,10 -95,-70 
                 C -85,-85 -55,-95 0,-95 Z"
              stroke="url(#shieldGrad)"
              strokeWidth="2.8"
              fill="rgba(8, 14, 30, 0.4)"
              filter="url(#cyberGlow)"
            />

            {/* Inner Secondary Shield Rim */}
            <path
              d="M 0,-80 
                 C 45,-80 70,-72 78,-60 
                 C 78,5 52,60 0,90 
                 C -52,60 -78,5 -78,-60 
                 C -70,-72 -45,-80 0,-80 Z"
              stroke="#00F0FF"
              strokeWidth="1.2"
              strokeDasharray="5 3"
              fill="none"
              opacity="0.6"
            />

            {/* Ashoka Chakra 24-Spoke Radial Motif at Shield Core */}
            <circle cx="0" cy="0" r="32" stroke="#00F0FF" strokeWidth="1.8" fill="rgba(0, 240, 255, 0.08)" />
            <circle cx="0" cy="0" r="6" fill="#00F0FF" />
            {[...Array(24)].map((_, i) => (
              <line
                key={`spoke-${i}`}
                x1="0"
                y1="0"
                x2={Math.cos((i * 15 * Math.PI) / 180) * 32}
                y2={Math.sin((i * 15 * Math.PI) / 180) * 32}
                stroke="#00F0FF"
                strokeWidth="1"
                opacity="0.8"
              />
            ))}

            {/* Top and Bottom Command Telemetry Text */}
            <text
              x="0"
              y="-115"
              textAnchor="middle"
              fill="#00F0FF"
              fontSize="10"
              fontFamily="'Share Tech Mono', monospace"
              letterSpacing="3"
              fontWeight="bold"
            >
              BHARAT CYBER SHIELD
            </text>
            <text
              x="0"
              y="135"
              textAnchor="middle"
              fill="#8B5CF6"
              fontSize="9"
              fontFamily="'Share Tech Mono', monospace"
              letterSpacing="2"
            >
              SEC. 63 BSA • LAW ENFORCEMENT
            </text>
          </g>
        </svg>
      </div>

      {/* 5. Radial Ambient Glow Lights */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] bg-cyan-600/5 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[500px] h-[400px] bg-violet-600/5 rounded-full blur-[120px] pointer-events-none" />
    </div>
  );
}
