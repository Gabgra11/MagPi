# MagPi - Bird Call Detection & Dashboard

A full-stack application that detects bird calls using audio analysis and displays them in a beautiful, responsive dashboard.

## Architecture

- **Listener** (Python): Runs on Raspberry Pi, continuously records audio and analyzes for bird calls using BirdNET-Lite
- **Dashboard** (Node.js/React): Web UI for visualizing detections, trends, and statistics

## Features

### Listener
- Continuous circular buffer audio recording
- Multi-worker architecture with queue-based communication
- BirdNET-Lite integration for species detection
- SQLite persistence with duplicate detection
- Configurable via environment variables

### Dashboard
- Real-time detection feed
- Hourly activity heatmap (weekly averages)
- Peak activity times by species
- Seasonal trends analysis
- Unique species leaderboard
- Milestone badges system
- Responsive, flat design UI

## Project Structure

```
MagPi/
├── listener/              # Python listener application
│   ├── src/
│   │   ├── main.py       # Entry point
│   │   ├── recorder.py   # Recording worker
│   │   ├── analyzer.py   # Analysis worker
│   │   ├── db_writer.py  # Database worker
│   │   └── config.py     # Configuration management
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard/             # Node.js/React dashboard
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API services
│   │   ├── styles/       # Styling
│   │   └── App.tsx
│   ├── server/           # Express backend
│   ├── package.json
│   └── Dockerfile
├── shared/               # Shared configs/types
├── docker-compose.yml
├── .env.example
└── README.md
```

## Getting Started

### Prerequisites
- Docker & Docker Compose (recommended)
- Python 3.9+ (for local listener development)
- Node.js 18+ (for local dashboard development)

### Local Development

1. Clone the repository
2. Copy `.env.example` to `.env` and customize settings
3. Start with Docker Compose:
   ```bash
   docker-compose up -d
   ```

Or run locally:
```bash
# Terminal 1: Listener
cd listener
pip install -r requirements.txt
python src/main.py

# Terminal 2: Dashboard
cd dashboard
npm install
npm run dev
```

### Environment Variables

See `.env.example` for all configurable options.

**Key Variables:**
- `LISTENER_DB_PATH`: Path to SQLite database
- `LISTENER_AUDIO_DEVICE`: Audio device ID
- `LISTENER_SAMPLE_RATE`: Audio sample rate
- `LISTENER_BUFFER_SIZE`: Circular buffer size
- `LISTENER_MIN_CONFIDENCE`: BirdNET confidence threshold
- `LISTENER_DUPLICATE_WINDOW`: Seconds to ignore duplicate detections
- `DASHBOARD_PORT`: Dashboard server port
- `DASHBOARD_API_URL`: Listener API URL
- `DASHBOARD_UPDATE_INTERVAL`: Real-time update interval (ms)

## Deployment

### Raspberry Pi (Listener)

1. Install Docker on Raspberry Pi OS
2. Use the provided `docker-compose.yml` with listener service
3. Configure environment variables in `.env`
4. Run:
   ```bash
   docker-compose up -d listener
   ```

### Server (Dashboard)

1. Deploy dashboard service to your server
2. Configure API URL to point to listener
3. Run:
   ```bash
   docker-compose up -d dashboard
   ```

## API Endpoints

The listener exposes these endpoints for the dashboard:

- `GET /api/detections` - Recent detections with filters
- `GET /api/stats` - Overall statistics
- `GET /api/species` - All detected species
- `GET /api/heatmap` - Activity data for heatmap visualization
- `GET /api/trends` - Seasonal trends by species
- `POST /api/config` - Update configuration

## Technology Stack

**Listener:**
- Python 3.9+
- BirdNET-Lite
- SQLite3
- Multiprocessing
- PyAudio

**Dashboard:**
- Node.js/Express
- React 18
- TypeScript
- Recharts (visualizations)
- Tailwind CSS
- Socket.io (real-time updates)

