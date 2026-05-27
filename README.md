# Scotian Shelf AIS Vessel Tracker

An interactive web app for visualizing vessel traffic on the Scotian Shelf using AIS (Automatic Identification System) data. Users can search for vessels, filter by area, select a date range, and see a vessel's route plotted on a map with speed-colored position points.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + OpenLayers + Tailwind CSS (Vite) |
| Backend | FastAPI (Python) |
| Database | SQLite (via Git LFS) |
| AIS Decoding | aisdb (Rust-core Python library) |
| Data Filtering | DuckDB |

## Running Locally

**Backend:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn aisdb duckdb
uvicorn main:app --reload --port 8001
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Set `VITE_API_URL` in `frontend/.env` to match your backend port.

## Data Ingestion

Raw AIS data lives on the lab machine at `/home/shared/aisdecode/`. To re-ingest:

```bash
source venv/bin/activate
python3 pipeline/ingest.py
```

This decodes CCG terrestrial NMEA files and filters exactEarth satellite CSVs to the Scotian Shelf bounding box (lat 42–47°N, lon -66–-57°W), producing `data/ais.db`.

See [DEVLOG.md](DEVLOG.md) for full technical documentation.

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/vessels` | All unique vessels (MMSI, name, ship type, source) |
| `GET /api/vessels/area?min_lat=&max_lat=&min_lon=&max_lon=` | Vessels within a bounding box |
| `GET /api/vessel/{mmsi}/route?start=&end=` | Ordered position track for a vessel |

## Data Sources

- **CCG Terrestrial**: Canadian Coast Guard AIS shore stations (raw NMEA format)
- **Satellite**: exactEarth satellite AIS (pre-decoded CSV, global coverage)
