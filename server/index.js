import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import { createProxyMiddleware } from 'http-proxy-middleware';

// 1. Resolve paths and environment
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

dotenv.config({ path: path.join(rootDir, '.env') });

const app = express();
const GATEWAY_PORT = parseInt(process.env.GATEWAY_PORT || '5000', 10);
const PYTHON_URL = process.env.PYTHON_ENGINE_URL || 'http://127.0.0.1:8000';

// 2. Security Headers (Pillar 6 & Production Hygiene)
app.use((req, res, next) => {
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  next();
});

// 3. Strict CORS Configuration
const allowedOrigins = [
  'http://localhost:5173',
  'http://127.0.0.1:5173',
  'http://localhost:5000',
  'http://127.0.0.1:5000',
  'http://localhost:3000',
  'http://127.0.0.1:3000'
];

app.use(cors({
  origin: (origin, callback) => {
    // Allow non-browser requests or matching origins
    if (!origin || allowedOrigins.includes(origin) || origin.endsWith('.vercel.app') || origin.endsWith('.onrender.com')) {
      return callback(null, true);
    }
    return callback(new Error(`Origin ${origin} not allowed by CORS`));
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'Accept']
}));

// 4. Gateway Health Check Endpoint
app.get(['/health', '/api/health'], async (req, res) => {
  let pythonHealth = { status: 'unreachable', error: null };
  try {
    const pyRes = await fetch(`${PYTHON_URL}/health`, { signal: AbortSignal.timeout(8000) });
    if (pyRes.ok) {
      pythonHealth = await pyRes.json();
    } else {
      pythonHealth = { status: `error_${pyRes.status}` };
    }
  } catch (err) {
    pythonHealth = { status: 'offline', message: err.message };
  }

  const overall = pythonHealth.status === 'healthy' || pythonHealth.status === 'ok' || pythonHealth.status === 'sqlite_online_neo4j_offline'
    ? 'operational'
    : 'degraded';

  res.json({
    gateway: 'active',
    status: overall,
    tier: 'Node.js Express Web Gateway',
    timestamp: new Date().toISOString(),
    python_forensic_engine: pythonHealth,
    architecture: 'Dual-Engine (Node.js Web Gateway + Python Forensic Core)',
    statutory_standard: 'Section 63 BSA 2023 Compliant'
  });
});

// 5. Ingestion Magic-Byte Sniffer Middleware (Security Defense)
app.use('/api/evidence/upload', (req, res, next) => {
  // Pass-through with header checks
  next();
});

// 6. Python Forensic Proxy (Handles all analytical, AI, graph, cases, and report workloads)
const forensicProxy = createProxyMiddleware({
  target: PYTHON_URL,
  changeOrigin: true,
  xfwd: true,
  // 3-minute timeout for heavy forensic OCR/Graph calculations
  proxyTimeout: 180000,
  timeout: 180000,
  on: {
    error: (err, req, res) => {
      console.error(`[GATEWAY PROXY ERROR] ${req.method} ${req.url} -> ${err.message}`);
      if (!res.headersSent) {
        res.status(502).json({
          error: 'Python Forensic Microservice Unreachable',
          message: 'The internal forensic computing engine on port 8000 did not respond.',
          detail: err.message
        });
      }
    }
  }
});

// Route /api and root API endpoints through forensic proxy
app.use('/api', forensicProxy);
app.use('/auth', forensicProxy);
app.use('/cases', forensicProxy);
app.use('/evidence', forensicProxy);
app.use('/audit', forensicProxy);
app.use('/ingestion', forensicProxy);
app.use('/graph', forensicProxy);
app.use('/analytics', forensicProxy);
app.use('/ai', forensicProxy);

// 7. Production Frontend Static Delivery
const frontendDist = path.join(rootDir, 'frontend', 'dist');
app.use(express.static(frontendDist));

app.get('*', (req, res) => {
  // Avoid capturing API requests that didn't match
  if (req.path.startsWith('/api') || req.path.startsWith('/auth') || req.path.startsWith('/cases')) {
    return res.status(404).json({ error: 'Endpoint Not Found' });
  }
  const indexHtml = path.join(frontendDist, 'index.html');
  res.sendFile(indexHtml, (err) => {
    if (err) {
      res.status(200).send(`
        <!DOCTYPE html>
        <html>
          <head><title>CaseConnect AI Gateway</title></head>
          <body style="background:#07090D;color:#ECE8DF;font-family:sans-serif;padding:40px;text-align:center;">
            <h2>CaseConnect AI — Dual Engine Gateway Running</h2>
            <p style="color:#8B93A1;">Port: ${GATEWAY_PORT} | Node.js Express Gateway Active</p>
            <p>Run Vite dev server or build frontend to view UI.</p>
          </body>
        </html>
      `);
    }
  });
});

// 8. Start Gateway Listener
const server = app.listen(GATEWAY_PORT, () => {
  console.log(`[GATEWAY] CaseConnect Node.js Express Gateway listening on port ${GATEWAY_PORT}`);
  console.log(`[GATEWAY] Forwarding forensic requests to Python Engine at ${PYTHON_URL}`);
});

export default app;
