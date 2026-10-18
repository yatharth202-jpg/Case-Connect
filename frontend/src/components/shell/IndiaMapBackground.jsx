import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useScroll } from './ScrollProvider';

export const IndiaMapBackground = () => {
  const canvasRef = useRef(null);
  const scanLineRef = useRef(null);
  const { scrollProgress } = useScroll();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const isMobile = window.innerWidth < 768;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 1. Three.js Renderer Setup
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2));
    renderer.setSize(window.innerWidth, window.innerHeight);

    // 2. Scene & Camera Setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, -4.5, 27);
    camera.lookAt(0, 0, 0);

    const indiaGroup = new THREE.Group();
    scene.add(indiaGroup);

    const geometriesToDispose = [];
    const materialsToDispose = [];

    // Coordinate Projection Center: Lon ~81.5°E, Lat ~22.5°N
    const latLonToMap = (lon, lat) => {
      const x = (lon - 81.5) * 0.96;
      const y = (lat - 22.5) * 0.96;
      return { x, y };
    };

    // =========================================================================
    // 3. Official Survey of India National Outer Boundary Coordinates
    // =========================================================================
    const boundaryCoords = [
      // Northern Crown (Kashmir, Siachen, Ladakh)
      [74.5, 37.1], [75.5, 36.9], [76.8, 36.8], [77.8, 35.8], [78.8, 35.2], [79.3, 34.2], [79.2, 32.8],
      // Himachal & Uttarakhand Frontier
      [78.5, 31.8], [79.2, 31.0], [80.3, 30.2], [81.0, 29.8],
      // Nepal Border / Sikkim Apex
      [81.5, 29.2], [83.5, 27.5], [85.5, 26.8], [88.1, 27.8], [88.6, 28.0], [88.8, 27.4],
      // Siliguri Corridor & Bhutan Border
      [89.0, 26.8], [90.2, 26.8], [91.8, 27.0],
      // Arunachal Pradesh Northern Frontier
      [92.5, 27.8], [94.0, 28.6], [96.0, 28.5], [97.3, 28.2],
      // Eastern Frontier (Nagaland, Manipur, Mizoram)
      [96.8, 26.8], [95.5, 25.5], [94.5, 24.2], [93.2, 23.8], [92.8, 22.0],
      // Tripura, Meghalaya, Bangladesh Ingress Line
      [91.8, 23.5], [91.2, 24.2], [91.5, 25.1], [89.8, 25.2], [89.8, 26.0],
      // Bengal Delta & Sundarbans
      [88.8, 22.8], [89.0, 21.8], [88.2, 21.6],
      // Odisha Coast
      [86.8, 20.8], [85.5, 19.8], [84.5, 18.8],
      // Andhra Pradesh Coast
      [83.3, 17.8], [82.0, 16.5], [80.5, 15.5], [80.1, 13.5],
      // Tamil Nadu Coast
      [79.8, 11.5], [79.8, 10.2], [79.0, 9.3],
      // Southern Apex (Kanyakumari)
      [77.5, 8.1],
      // Kerala & Malabar Coast
      [76.5, 8.8], [76.0, 9.8], [75.3, 11.8],
      // Karnataka & Goa
      [74.8, 13.0], [74.0, 14.8], [73.8, 15.6],
      // Maharashtra Coast (Konkan & Mumbai)
      [73.0, 17.5], [72.8, 18.9], [72.8, 19.8],
      // Gujarat Coast (Gulf of Khambhat & Surat)
      [72.6, 21.1], [72.2, 21.8], [71.5, 20.8],
      // Kathiawar Peninsula & Dwarka
      [70.0, 21.0], [69.0, 22.3],
      // Gulf of Kutch & Rann of Kutch
      [68.4, 23.5], [70.0, 24.2], [71.2, 24.6],
      // Rajasthan Western Frontier
      [70.5, 26.0], [70.2, 27.2], [71.5, 28.5], [72.5, 29.8],
      // Punjab & Jammu Frontier
      [74.0, 31.5], [74.5, 32.5], [74.2, 34.0], [74.5, 35.5], [74.5, 37.1]
    ];

    // Polygon In-Fill Test
    const pointInPoly = (x, y, poly) => {
      let inside = false;
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const xi = poly[i][0], yi = poly[i][1];
        const xj = poly[j][0], yj = poly[j][1];
        const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
      }
      return inside;
    };

    // =========================================================================
    // 4. Render National Boundary Lines (Crisp Luminous Double-Stroke)
    // =========================================================================
    const boundaryPoints3D = boundaryCoords.map(([lon, lat]) => {
      const p = latLonToMap(lon, lat);
      return new THREE.Vector3(p.x, p.y, 0.08);
    });

    // Core bright white/cyan national line
    const boundaryGeo = new THREE.BufferGeometry().setFromPoints(boundaryPoints3D);
    const boundaryMat = new THREE.LineBasicMaterial({
      color: 0xE8F8FF,
      linewidth: 3,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending
    });
    const boundaryLine = new THREE.LineLoop(boundaryGeo, boundaryMat);
    indiaGroup.add(boundaryLine);
    geometriesToDispose.push(boundaryGeo);
    materialsToDispose.push(boundaryMat);

    // Glowing Neon Cyan Halo Line
    const haloPoints3D = boundaryCoords.map(([lon, lat]) => {
      const p = latLonToMap(lon, lat);
      return new THREE.Vector3(p.x * 1.012, p.y * 1.012, 0.02);
    });
    const haloGeo = new THREE.BufferGeometry().setFromPoints(haloPoints3D);
    const haloMat = new THREE.LineBasicMaterial({
      color: 0x00E5FF,
      linewidth: 2,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending
    });
    const haloLine = new THREE.LineLoop(haloGeo, haloMat);
    indiaGroup.add(haloLine);
    geometriesToDispose.push(haloGeo);
    materialsToDispose.push(haloMat);

    // =========================================================================
    // 5. Internal State Boundaries Line Network (Exactly as in Reference Photo)
    // =========================================================================
    const stateLines = [
      // 1. Kashmir & Ladakh Division
      [[74.2, 34.0], [75.5, 33.5], [76.5, 33.2], [77.5, 33.8]],
      // 2. Himachal Northern Border
      [[74.5, 32.5], [75.8, 32.2], [77.0, 32.0], [78.5, 31.8]],
      // 3. Punjab & Haryana
      [[74.0, 31.5], [75.5, 31.0], [76.8, 30.8], [77.2, 30.5]],
      [[75.0, 30.0], [76.0, 29.8], [77.0, 29.5], [77.3, 28.8]],
      // 4. Rajasthan & Gujarat
      [[71.0, 24.5], [72.5, 24.2], [73.8, 24.0], [74.5, 23.8]],
      // 5. Rajasthan & Madhya Pradesh
      [[74.5, 23.8], [75.5, 24.8], [76.8, 25.5], [77.8, 26.2], [78.5, 26.8]],
      // 6. Gujarat & Maharashtra
      [[72.8, 20.2], [73.5, 20.5], [74.8, 21.0], [75.5, 21.2]],
      // 7. Maharashtra & Madhya Pradesh
      [[75.5, 21.2], [77.0, 21.5], [79.0, 21.8], [80.5, 21.5]],
      // 8. Uttar Pradesh & Madhya Pradesh
      [[78.5, 26.8], [80.0, 25.5], [81.5, 25.0], [82.8, 24.5]],
      // 9. Uttar Pradesh & Bihar
      [[82.8, 24.5], [83.5, 24.8], [84.5, 25.0], [84.2, 27.0]],
      // 10. Madhya Pradesh & Chhattisgarh
      [[80.5, 21.5], [81.5, 22.8], [82.5, 23.5], [82.8, 24.5]],
      // 11. Chhattisgarh & Jharkhand
      [[82.5, 23.5], [83.8, 23.2], [84.5, 22.8], [85.5, 22.2]],
      // 12. Bihar & Jharkhand
      [[84.5, 25.0], [86.0, 24.5], [87.5, 24.8], [88.0, 24.2]],
      // 13. Jharkhand & West Bengal
      [[88.0, 24.2], [87.5, 23.2], [86.8, 22.2], [86.8, 21.5]],
      // 14. Chhattisgarh & Odisha
      [[85.5, 22.2], [85.0, 21.5], [84.0, 20.5], [83.5, 19.0], [82.0, 18.2]],
      // 15. Maharashtra & Karnataka
      [[73.8, 15.6], [74.5, 15.8], [75.5, 16.5], [76.5, 17.2], [77.5, 17.8]],
      // 16. Maharashtra & Telangana
      [[77.5, 17.8], [78.5, 18.5], [79.5, 19.2], [80.5, 18.8]],
      // 17. Karnataka & Telangana / Andhra
      [[77.5, 17.8], [77.5, 16.0], [77.2, 14.8], [77.5, 13.8]],
      // 18. Telangana & Andhra Pradesh
      [[77.5, 16.0], [79.0, 16.5], [80.5, 16.8], [81.0, 17.5], [81.5, 18.0]],
      // 19. Andhra Pradesh & Odisha
      [[81.5, 18.0], [82.5, 18.5], [83.5, 19.0]],
      // 20. Karnataka & Kerala
      [[75.0, 12.5], [75.8, 12.0], [76.5, 11.8]],
      // 21. Kerala & Tamil Nadu
      [[76.5, 11.8], [77.0, 10.5], [77.2, 9.5], [77.5, 8.8]],
      // 22. Karnataka & Tamil Nadu
      [[76.5, 11.8], [77.5, 12.2], [78.2, 12.8], [79.0, 13.0]],
      // 23. Tamil Nadu & Andhra Pradesh
      [[79.0, 13.0], [79.8, 13.5], [80.1, 13.5]],
      // 24. Northeast: Meghalaya & Assam
      [[90.0, 25.2], [91.5, 25.1], [92.5, 25.2]],
      // 25. Northeast: Arunachal & Assam
      [[92.5, 27.0], [93.8, 27.2], [95.0, 27.5], [96.0, 27.8]],
      // 26. Northeast: Nagaland / Manipur / Mizoram
      [[94.0, 26.5], [94.5, 25.5], [94.0, 24.5]],
      [[92.8, 24.2], [93.0, 23.5], [92.8, 22.5]]
    ];

    stateLines.forEach((linePts) => {
      const pts3D = linePts.map(([lon, lat]) => {
        const p = latLonToMap(lon, lat);
        return new THREE.Vector3(p.x, p.y, 0.04);
      });
      const stGeo = new THREE.BufferGeometry().setFromPoints(pts3D);
      const stMat = new THREE.LineBasicMaterial({
        color: 0x5EEAD4, // Crisp mint-cyan state line
        transparent: true,
        opacity: 0.65,
        linewidth: 1.5,
        blending: THREE.AdditiveBlending
      });
      const stLine = new THREE.Line(stGeo, stMat);
      indiaGroup.add(stLine);
      geometriesToDispose.push(stGeo);
      materialsToDispose.push(stMat);
    });

    // =========================================================================
    // 6. Glowing Yellow / Lime City & Tactical Hub Nodes (Exactly like Reference)
    // =========================================================================
    const cityHubs = [
      // Northern Hubs
      { name: "Delhi", lon: 77.2, lat: 28.6, prime: true },
      { name: "Srinagar", lon: 74.8, lat: 34.0 },
      { name: "Leh", lon: 77.5, lat: 34.1 },
      { name: "Jammu", lon: 74.8, lat: 32.7 },
      { name: "Shimla", lon: 77.1, lat: 31.1 },
      { name: "Chandigarh", lon: 76.7, lat: 30.7 },
      { name: "Amritsar", lon: 74.8, lat: 31.6 },
      { name: "Dehradun", lon: 78.0, lat: 30.3 },
      { name: "Meerut", lon: 77.7, lat: 28.9 },
      // Western Hubs
      { name: "Jaipur", lon: 75.8, lat: 26.9, prime: true },
      { name: "Jodhpur", lon: 73.0, lat: 26.2 },
      { name: "Udaipur", lon: 73.6, lat: 24.5 },
      { name: "Ahmedabad", lon: 72.5, lat: 23.0, prime: true },
      { name: "Gandhinagar", lon: 72.6, lat: 23.2 },
      { name: "Surat", lon: 72.8, lat: 21.1, prime: true },
      { name: "Vadodara", lon: 73.1, lat: 22.3 },
      { name: "Rajkot", lon: 70.8, lat: 22.3 },
      // Central Hubs
      { name: "Bhopal", lon: 77.4, lat: 23.2, prime: true },
      { name: "Indore", lon: 75.8, lat: 22.7 },
      { name: "Gwalior", lon: 78.1, lat: 26.2 },
      { name: "Jabalpur", lon: 79.9, lat: 23.1 },
      { name: "Nagpur", lon: 79.0, lat: 21.1, prime: true },
      { name: "Raipur", lon: 81.6, lat: 21.2 },
      // Maharashtra & Western Coast
      { name: "Mumbai", lon: 72.8, lat: 19.0, prime: true },
      { name: "Pune", lon: 73.8, lat: 18.5, prime: true },
      { name: "Nashik", lon: 73.7, lat: 19.9 },
      { name: "Panaji", lon: 73.8, lat: 15.4 },
      // Gangetic Plains & East
      { name: "Lucknow", lon: 80.9, lat: 26.8, prime: true },
      { name: "Kanpur", lon: 80.3, lat: 26.4 },
      { name: "Varanasi", lon: 82.9, lat: 25.3 },
      { name: "Prayagraj", lon: 81.8, lat: 25.4 },
      { name: "Patna", lon: 85.1, lat: 25.6, prime: true },
      { name: "Gaya", lon: 84.9, lat: 24.7 },
      { name: "Ranchi", lon: 85.3, lat: 23.3 },
      { name: "Kolkata", lon: 88.3, lat: 22.5, prime: true },
      { name: "Siliguri", lon: 88.4, lat: 26.7 },
      { name: "Bhubaneswar", lon: 85.8, lat: 20.3, prime: true },
      { name: "Cuttack", lon: 85.8, lat: 20.5 },
      // Southern Hubs
      { name: "Hyderabad", lon: 78.4, lat: 17.4, prime: true },
      { name: "Visakhapatnam", lon: 83.3, lat: 17.7 },
      { name: "Vijayawada", lon: 80.6, lat: 16.5 },
      { name: "Bengaluru", lon: 77.6, lat: 12.9, prime: true },
      { name: "Mysuru", lon: 76.6, lat: 12.3 },
      { name: "Chennai", lon: 80.2, lat: 13.0, prime: true },
      { name: "Coimbatore", lon: 76.9, lat: 11.0 },
      { name: "Madurai", lon: 78.1, lat: 9.9 },
      { name: "Kochi", lon: 76.2, lat: 9.9, prime: true },
      { name: "Thiruvananthapuram", lon: 76.9, lat: 8.5 },
      // Northeast Hubs
      { name: "Guwahati", lon: 91.7, lat: 26.1, prime: true },
      { name: "Shillong", lon: 91.8, lat: 25.5 },
      { name: "Agartala", lon: 91.2, lat: 23.8 },
      { name: "Imphal", lon: 93.9, lat: 24.8 }
    ];

    const yellowNodes = [];
    const verticalLaserRays = [];

    cityHubs.forEach((hub) => {
      const pos = latLonToMap(hub.lon, hub.lat);

      // 1. Bright Yellow Core Pip (Sphere)
      const dotRadius = hub.prime ? 0.28 : 0.18;
      const dotGeo = new THREE.SphereGeometry(dotRadius, 14, 14);
      const dotMat = new THREE.MeshBasicMaterial({
        color: 0xFFEA00, // Vibrant glowing yellow
        blending: THREE.AdditiveBlending
      });
      const dotMesh = new THREE.Mesh(dotGeo, dotMat);
      dotMesh.position.set(pos.x, pos.y, 0.15);
      indiaGroup.add(dotMesh);
      geometriesToDispose.push(dotGeo);
      materialsToDispose.push(dotMat);

      // 2. Translucent Glowing Yellow/Lime Aura Ring
      const ringOuter = hub.prime ? 0.65 : 0.42;
      const ringInner = hub.prime ? 0.38 : 0.24;
      const ringGeo = new THREE.RingGeometry(ringInner, ringOuter, 24);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0xCCFF00, // Lime-yellow halo
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.75,
        blending: THREE.AdditiveBlending
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.position.set(pos.x, pos.y, 0.16);
      indiaGroup.add(ringMesh);
      geometriesToDispose.push(ringGeo);
      materialsToDispose.push(ringMat);

      yellowNodes.push({ mesh: dotMesh, ring: ringMesh, isPrime: hub.prime, offset: Math.random() * Math.PI });

      // 3. Vertical Laser Scanner Lines (as seen in reference photo)
      if (hub.prime) {
        const rayLen = 5.0 + Math.random() * 4.0;
        const rayGeo = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(pos.x, pos.y, -0.5),
          new THREE.Vector3(pos.x, pos.y, rayLen)
        ]);
        const rayMat = new THREE.LineBasicMaterial({
          color: 0xFFEA00,
          transparent: true,
          opacity: 0.55,
          linewidth: 1.5,
          blending: THREE.AdditiveBlending
        });
        const rayLine = new THREE.Line(rayGeo, rayMat);
        indiaGroup.add(rayLine);
        verticalLaserRays.push(rayLine);
        geometriesToDispose.push(rayGeo);
        materialsToDispose.push(rayMat);
      }
    });

    // =========================================================================
    // 7. Internal Dense Cyan Point Cloud Matrix (The Digital Substrate)
    // =========================================================================
    const pointPositions = [];
    const pointColors = [];
    const colCyan = new THREE.Color('#00E5FF');
    const colDeepBlue = new THREE.Color('#0F3860');
    const colDim = new THREE.Color('#091B30');

    const step = isMobile ? 0.65 : 0.38;
    for (let lon = 68.4; lon <= 97.4; lon += step) {
      for (let lat = 8.1; lat <= 37.1; lat += step) {
        if (pointInPoly(lon, lat, boundaryCoords)) {
          const pt = latLonToMap(lon, lat);
          const zElevation = Math.sin(lon * 3.0) * Math.cos(lat * 3.0) * 0.25;
          pointPositions.push(pt.x, pt.y, zElevation);

          const r = Math.random();
          if (r > 0.65) {
            pointColors.push(colCyan.r, colCyan.g, colCyan.b);
          } else if (r > 0.3) {
            pointColors.push(colDeepBlue.r, colDeepBlue.g, colDeepBlue.b);
          } else {
            pointColors.push(colDim.r, colDim.g, colDim.b);
          }
        }
      }
    }

    const cloudGeo = new THREE.BufferGeometry();
    cloudGeo.setAttribute('position', new THREE.Float32BufferAttribute(pointPositions, 3));
    cloudGeo.setAttribute('color', new THREE.Float32BufferAttribute(pointColors, 3));

    const cloudMat = new THREE.PointsMaterial({
      size: isMobile ? 0.24 : 0.20,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending
    });

    const indiaPointCloud = new THREE.Points(cloudGeo, cloudMat);
    indiaGroup.add(indiaPointCloud);
    geometriesToDispose.push(cloudGeo);
    materialsToDispose.push(cloudMat);

    // =========================================================================
    // 8. Horizontal & Vertical Cyber Wireframe HUD Grid (From Reference Photo)
    // =========================================================================
    const hudLinesGroup = new THREE.Group();
    indiaGroup.add(hudLinesGroup);

    // Horizontal cyber grid lines
    const yGridLevels = [-12, -9, -6, -3, 0, 3, 6, 9, 12];
    yGridLevels.forEach((yVal) => {
      const hGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-18, yVal, 0.01),
        new THREE.Vector3(18, yVal, 0.01)
      ]);
      const hMat = new THREE.LineBasicMaterial({
        color: 0xA855F7, // Lavender / neon purple as in reference image
        transparent: true,
        opacity: 0.28,
        blending: THREE.AdditiveBlending
      });
      const hLine = new THREE.Line(hGeo, hMat);
      hudLinesGroup.add(hLine);
      geometriesToDispose.push(hGeo);
      materialsToDispose.push(hMat);
    });

    // Vertical cyber grid lines
    const xGridLevels = [-15, -10, -5, 0, 5, 10, 15];
    xGridLevels.forEach((xVal) => {
      const vGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(xVal, -15, 0.01),
        new THREE.Vector3(xVal, 15, 0.01)
      ]);
      const vMat = new THREE.LineBasicMaterial({
        color: 0x00E5FF, // Cyan wireframe vertical line
        transparent: true,
        opacity: 0.24,
        blending: THREE.AdditiveBlending
      });
      const vLine = new THREE.Line(vGeo, vMat);
      hudLinesGroup.add(vLine);
      geometriesToDispose.push(vGeo);
      materialsToDispose.push(vMat);
    });

    // Crosshair intersection tick marks (+)
    const crosshairGeo = new THREE.BufferGeometry();
    const crosshairPts = [];
    xGridLevels.forEach(x => {
      yGridLevels.forEach(y => {
        crosshairPts.push(x - 0.2, y, 0.02, x + 0.2, y, 0.02);
        crosshairPts.push(x, y - 0.2, 0.02, x, y + 0.2, 0.02);
      });
    });
    crosshairGeo.setAttribute('position', new THREE.Float32BufferAttribute(crosshairPts, 3));
    const crosshairMat = new THREE.LineBasicMaterial({
      color: 0x00E5FF,
      transparent: true,
      opacity: 0.55
    });
    const crosshairLines = new THREE.LineSegments(crosshairGeo, crosshairMat);
    hudLinesGroup.add(crosshairLines);
    geometriesToDispose.push(crosshairGeo);
    materialsToDispose.push(crosshairMat);

    // Initial 3D Orientation
    indiaGroup.rotation.x = -0.28;
    indiaGroup.rotation.y = 0.12;

    // Mouse Parallax listener
    let mouseX = 0;
    let mouseY = 0;
    const handleMouseMove = (e) => {
      mouseX = (e.clientX / window.innerWidth - 0.5) * 0.25;
      mouseY = (e.clientY / window.innerHeight - 0.5) * 0.2;
    };
    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    // =========================================================================
    // 9. Continuous Animation Loop
    // =========================================================================
    let animId;
    const clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Scroll progress
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? Math.min(Math.max(window.scrollY / docHeight, 0), 1) : 0;

      if (!prefersReducedMotion) {
        // Dynamic continuous 3D tilt and smooth responsiveness
        const targetRotY = 0.12 + Math.sin(progress * Math.PI) * 0.35 + mouseX;
        const targetRotX = -0.28 + (progress * 0.22) - mouseY;
        const targetCamZ = 27 - (progress * 4.0);
        const targetCamY = -4.5 + (progress * 2.5);

        // Smooth damping
        indiaGroup.rotation.y += (targetRotY - indiaGroup.rotation.y) * 0.05;
        indiaGroup.rotation.x += (targetRotX - indiaGroup.rotation.x) * 0.05;
        camera.position.z += (targetCamZ - camera.position.z) * 0.05;
        camera.position.y += (targetCamY - camera.position.y) * 0.05;

        // 1. Animate Glowing Yellow City Nodes & Halos
        yellowNodes.forEach((node) => {
          const s = 1.0 + Math.sin(elapsed * 3.5 + node.offset) * 0.35;
          node.ring.scale.set(s, s, s);
          node.ring.material.opacity = Math.max(0.2, 0.85 - (s * 0.4));
        });

        // 2. Pulse National Outer Border Glow
        boundaryMat.opacity = 0.85 + Math.sin(elapsed * 2.5) * 0.12;
        haloMat.opacity = 0.45 + Math.sin(elapsed * 3.0) * 0.2;

        // 3. Subtle drift for vertical laser scanner beams
        verticalLaserRays.forEach((ray, i) => {
          ray.material.opacity = 0.35 + Math.sin(elapsed * 4.0 + i) * 0.25;
        });

        // Sync Scan Line
        if (scanLineRef.current) {
          const scanPos = (window.scrollY * 1.35) % window.innerHeight;
          scanLineRef.current.style.transform = `translateY(${scanPos}px)`;
        }
      }

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);

      geometriesToDispose.forEach(geo => geo?.dispose());
      materialsToDispose.forEach(mat => mat?.dispose());
      renderer.dispose();
    };
  }, []);

  return (
    <div className="fixed inset-0 w-screen h-screen z-0 pointer-events-none overflow-hidden">
      {/* 3D WebGL Canvas */}
      <canvas ref={canvasRef} className="w-full h-full block" />

      {/* Atmospheric Cyber Vignette Overlay (Matches dark purple-navy night palette from photo) */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(6,8,24,0.35)_0%,rgba(6,8,24,0.88)_100%)] pointer-events-none" />

      {/* Subtle Horizontal Telemetry Scan Line */}
      <div
        ref={scanLineRef}
        className="absolute left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#00E5FF]/40 to-transparent pointer-events-none"
        style={{ top: 0, transition: 'transform 0.1s linear' }}
      />
    </div>
  );
};

export default IndiaMapBackground;
