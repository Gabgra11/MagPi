import express from 'express';
import cors from 'cors';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = process.env.DASHBOARD_PORT || 3000;
const API_URL = process.env.DASHBOARD_API_URL || 'http://localhost:8000';

// Middleware
app.use(cors());
app.use(express.json());

// Serve static files from build directory
app.use(express.static(join(__dirname, '../dist')));

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    api: API_URL,
  });
});

// Proxy API requests to listener
app.use('/api', async (req, res) => {
  try {
    const url = new URL(API_URL + req.path);
    // Pass query parameters
    Object.entries(req.query).forEach(([key, value]) => {
      url.searchParams.append(key, value);
    });

    const response = await fetch(url, {
      method: req.method,
      headers: req.headers,
      body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined,
    });

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    console.error('API Error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch from API server',
    });
  }
});

// SPA fallback - serve index.html for all other routes
app.get('*', (req, res) => {
  res.sendFile(join(__dirname, '../dist/index.html'));
});

app.listen(PORT, () => {
  console.log(`MagPi Dashboard Server running on http://localhost:${PORT}`);
  console.log(`API Server: ${API_URL}`);
});
