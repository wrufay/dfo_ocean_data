# Scotian Shelf AIS Vessel Tracker

A tool for visualizing vessel traffic on the Scotian Shelf using AIS (Automatic Identification System) data from Canadian Coast Guard shore stations.

Researchers can explore vessel movement patterns, transit routes, and speeds across the shelf — useful for correlating vessel activity with underwater noise levels, marine mammal presence, or other oceanographic observations collected in the region.

## What it does

- Browse all vessels detected on the Scotian Shelf during a given period
- Filter vessels by geographic area — draw a bounding box to isolate traffic near a study site
- Plot a vessel's full track for a selected date range, with position points colored by speed
- Inspect individual AIS pings: timestamp, coordinates, speed over ground, course

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + OpenLayers + Tailwind CSS (Vite) |
| Backend | FastAPI (Python) |
| Database | SQLite (demo) / Postgres (production) |
| AIS Decoding | aisdb (Dalhousie University) |

## Running with Docker

```bash
docker-compose up
```

Open `http://localhost`. The demo database (`data/ais.db`) is included with a sample of CCG vessels.

## Running Locally

**Backend:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Data Ingestion

Raw CCG data lives on the lab machine at `/home/shared/aisdecode/`. To re-ingest:

```bash
source venv/bin/activate
python3 pipeline/ingest.py
```

Decodes raw NMEA files, filters to the Scotian Shelf bounding box (lat 42–47°N, lon -66–-57°W), and samples down to `DEMO_SAMPLE` vessels for the committed demo DB. Set `DEMO_SAMPLE = None` to keep all data for local analysis (do not commit the full DB).

## API

| Endpoint | Description |
|---|---|
| `GET /api/vessels` | All vessels (MMSI, name, ship type) |
| `GET /api/vessels/area?min_lat&max_lat&min_lon&max_lon` | Vessels with pings inside a bounding box |
| `GET /api/vessel/{mmsi}/route?start&end` | Ordered position track for a vessel |

## Data Source

Canadian Coast Guard terrestrial AIS — shore stations along the Scotian Shelf coastline record AIS broadcasts from nearby vessels. Coverage is dense close to shore and drops off in offshore areas.
