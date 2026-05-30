# Scotian Shelf AIS Vessel Tracker

A web tool for visualizing vessel traffic on the Scotian Shelf using AIS (Automatic Identification System) data from Canadian Coast Guard shore stations.

Researchers can explore vessel movement patterns, transit routes, and speeds across the shelf — useful for correlating vessel activity with underwater noise levels, marine mammal presence, or other oceanographic observations.

## What's in the demo

The committed `data/ais.db` contains a small cherry-picked sample of vessels (tugs, ferries, fishing boats, fire boats) operating around Halifax — enough to demonstrate the tool without publishing the full CCG dataset.

## Features

- Browse vessels detected on the Scotian Shelf
- Search by name, MMSI, or ship type
- Plot a vessel's full track for a selected date range, with position points colored by speed
- Click any track point to inspect timestamp, coordinates, speed over ground, and course

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + OpenLayers + Tailwind CSS (Vite) |
| Backend | FastAPI (Python) |
| Database | SQLite (demo) / Neon Postgres (optional scale-up) |
| AIS decoding | [aisdb](https://aisviz.cs.dal.ca/) (Dalhousie University) |

## Running locally

**Backend:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend** (in a separate terminal):
```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

By default Vite proxies `/api` requests to `http://localhost:8000`. To point at a deployed backend, set `VITE_API_URL` in `frontend/.env`.

## Running with Docker

```bash
docker-compose up --build
```

Open <http://localhost>. The frontend container serves the built React app on port 80 and proxies `/api/` to the backend container.

## Loading your own data

The pipeline (`pipeline/ingest.py`) decodes raw CCG NMEA files into a SQLite database.

0. **Install pipeline dependencies** (in addition to the backend ones):
   ```bash
   pip install -r pipeline/requirements.txt
   ```

1. **Point the pipeline at your CCG files.** Open `pipeline/ingest.py` and set:
   ```python
   CCG_DIR = "/path/to/your/ccg/data"  # contains CCG_AIS_UTC_Log_*.csv files
   ```

2. **Adjust the bounding box** if you are working outside the Scotian Shelf:
   ```python
   XMIN, XMAX = -66.0, -57.0  # longitude
   YMIN, YMAX =  42.0,  47.0  # latitude
   ```

3. **Choose how to sample the output:**
   - `DEMO_SAMPLE = 18` keeps only the hand-picked MMSIs in `DEMO_MMSIS` (current demo behavior — safe to commit).
   - `DEMO_SAMPLE = None` keeps every vessel in the bounding box (for local analysis — do **not** commit the resulting DB).

4. **Run the pipeline:**
   ```bash
   source venv/bin/activate
   python3 pipeline/ingest.py
   ```
   The script wipes any existing `data/ais.db`, decodes the first matching CCG file, trims to the bounding box, samples (if configured), and VACUUMs the result.

5. **Start the app** — the backend reads `data/ais.db` automatically.

## Scaling up to Postgres

For multi-user deployments or datasets too large for SQLite, migrate to Neon (serverless Postgres over HTTPS, works through restrictive firewalls):

```bash
export NEON_CONNECTION_STRING="postgresql://user:pass@host/db"
python3 pipeline/migrate_to_neon.py
```

Set the same `NEON_CONNECTION_STRING` in the backend's environment and `main.py` will route queries to Neon instead of SQLite.

## API

| Endpoint | Description |
|---|---|
| `GET /api/vessels` | All vessels in the allowed set (MMSI, name, ship type) |
| `GET /api/vessel/{mmsi}/route?start&end` | Ordered position track for a vessel |

## Data source

Canadian Coast Guard terrestrial AIS — shore stations along the Scotian Shelf coastline record AIS broadcasts from nearby vessels. Coverage is dense close to shore and drops off in offshore areas.

CCG files arrive as raw NMEA with a `.csv` extension. `pipeline/ingest.py` symlinks them as `.nm4` before handing them to `aisdb`, which detects file type by extension.
