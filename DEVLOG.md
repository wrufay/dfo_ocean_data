# AIS Vessel Tracker — Dev Log (2026-05-26)

## What We Built

A vessel tracking web app for the Scotian Shelf. Users can select a vessel from a sidebar, pick a date range, and see its route plotted on an interactive map. Data comes from two AIS (Automatic Identification System) sources decoded and stored in a local database.

**Stack:**
- Frontend: React + OpenLayers + Tailwind CSS (Vite)
- Backend: FastAPI (Python)
- Database: SQLite (local dev / deployed)
- Ingestion: aisdb + DuckDB

---

## The Data

### What is AIS?
AIS (Automatic Identification System) is a tracking system used by ships. Vessels broadcast their position, speed, heading, MMSI (unique vessel ID), and vessel name at regular intervals. There are two types of receivers:

- **Terrestrial (CCG)**: Coast guard stations on land pick up signals from nearby ships. High density near shore, limited offshore coverage.
- **Satellite (exactEarth)**: Satellites pick up AIS signals globally. Better offshore coverage.

### Data Sources

**1. CCG Terrestrial Data**
- Location: `/home/shared/aisdecode/testData/CCG_AIS_UTC_Log_*.csv`
- 2 files, ~26 million raw NMEA sentences each
- Format: raw NMEA-encoded messages, one per line, e.g.:
  ```
  \s:Harrington,c:1741649400*0C\!AIVDO,1,1,,A,4030pI1vTmGMssgckdLqH7G00D00,0*24
  ```
  Despite having a `.csv` extension, these are NOT tabular CSV files. They contain binary-packed NMEA messages that need to be decoded.

**2. Satellite Data (exactEarth)**
- Location: `/home/shared/aisdecode/testData/newSatAis/01/`
- 24 zip files, ~6.4 million rows each (160M rows total globally)
- Already decoded tabular CSV inside each zip, with 119 columns including MMSI, Latitude, Longitude, SOG, COG, Vessel_Name, Ship_Type, etc.

---

## The Ingestion Pipeline (`pipeline/ingest.py`)

### Why We Wrote This

The raw data is massive and global. We only care about the **Scotian Shelf** (lat 42–47°N, lon -66–-57°W). The pipeline's job is to:
1. Decode the raw CCG NMEA messages
2. Filter satellite data to Scotian Shelf only
3. Store everything in a queryable database

### Tool 1: aisdb

**What it is:** A Python library developed at Dalhousie University (Halifax) specifically for working with AIS data. It has a compiled Rust core that makes it extremely fast.

**What it does here:** Decodes the raw CCG NMEA messages and stores them in SQLite. It handles all the binary unpacking of AIS messages, checksum validation, and database schema creation automatically.

**The tricky part:** aisdb detects file format by extension:
- `.csv` → expects a decoded tabular CSV with a `Time` column
- `.nm4` → expects raw NMEA sentences (what we actually have)

The CCG files are raw NMEA saved with a `.csv` extension, so aisdb misidentifies them. **Fix:** We symlink each `.csv` file to a `.nm4` filename in a temp directory before passing to aisdb. We also pass `type_preference='nmea'` explicitly.

**Output tables (created by aisdb):**
- `ais_202503_dynamic` — position pings (MMSI, time, lat, lon, SOG, COG, heading). Millions of rows.
- `ais_202503_static` — vessel metadata (MMSI, vessel_name, ship_type, call_sign, IMO, etc.). One row per vessel broadcast.

**Performance:** ~68,000 messages/second using 4 parallel workers. Each 4.2GB CCG file takes ~4 minutes.

### Tool 2: DuckDB

**What it is:** An in-process analytical database that can query CSV files directly using SQL, without loading them into memory first.

**Why not pandas?**
- The satellite files are 6.4 million rows each, 160 million rows total
- pandas loads the entire file into RAM before filtering — too slow and memory-intensive
- DuckDB streams through the file and only keeps rows matching the WHERE clause
- DuckDB is columnar: when filtering by Latitude/Longitude it skips the other 117 columns entirely
- Result: much faster, much less RAM usage

**The tricky part:** DuckDB 1.5 doesn't support reading `.zip` files natively (it supports gzip but not zip). **Fix:** We use Python's built-in `zipfile` module to extract each zip to a temp directory, run DuckDB on the extracted CSV, then delete it before moving to the next file.

**Output table:** `ais_satellite` — filtered Scotian Shelf records with columns: mmsi, time, longitude, latitude, sog, cog, vessel_name, ship_type.

**Result:** 62,673 records in the Scotian Shelf bounding box from 24 satellite files (vs 160M globally).

### Running the Pipeline

```bash
cd /path/to/project
python3 pipeline/ingest.py
```

No `DATABASE_URL` set → uses SQLite at `data/ais.db` (default).
With `DATABASE_URL` set → uses Postgres.

---

## The Backend (`main.py`)

FastAPI with two endpoints:

### `GET /api/vessels`
Returns all unique vessels from both CCG and satellite data, merged and deduplicated by MMSI.

**Performance note:** Originally queried `ais_202503_dynamic` (17M rows) with `SELECT DISTINCT` — this caused a full table scan and timed out. Fixed by querying `ais_202503_static` instead, which is much smaller and already contains one row per vessel.

### `GET /api/vessel/{mmsi}/route?start=...&end=...`
Returns ordered position points for a vessel in a time range, from both CCG and satellite tables merged and sorted by time.

---

## The Frontend (`frontend/src/Map.jsx`)

React + OpenLayers map centered on the Scotian Shelf (-63.5, 44.5).

**Sidebar:**
- Search vessels by name or MMSI
- Date range picker (start/end)
- "Show Route" button

**Map:**
- Route rendered as a LineString (teal line)
- Individual AIS ping points colored by speed:
  - Green: < 3 knots (anchored/slow)
  - Orange: 3–10 knots (moderate)
  - Red: > 10 knots (fast)
- Auto-zooms to the route extent on load

---

## Why SQLite (and the Postgres/Neon story)

### The Goal
The ideal setup is Railway (cloud hosting) for the FastAPI backend + a cloud Postgres database, so the data lives in the cloud and isn't tied to a single machine.

### Why Not Railway Postgres
Railway Postgres is accessible via a custom port (e.g. 17765). The DFO/university lab network blocks all outbound connections on non-standard ports — only ports 80 and 443 are open. We confirmed this with `nc` (netcat) tests. This means the ingestion script running on the lab machine cannot write to Railway Postgres.

### Why Not Neon
Neon is a serverless Postgres provider that connects over port 443 (WebSockets/HTTPS), which IS open on the lab network. However, adding Neon means splitting infrastructure across Railway (app) and Neon (DB) for a reason that's purely a network workaround, not a technical requirement. For a research tool with a small number of users, this added complexity wasn't justified.

### Why SQLite Works Fine
- The app is read-heavy (ingest once, query many times)
- Small number of concurrent users
- SQLite file (`data/ais.db`) can be committed to the repo and deployed to Railway alongside FastAPI
- 2.3GB DB file, fast enough for the use case

### The Tradeoff
SQLite is tied to the lab machine for data updates — if the machine is wiped, the raw data and the DB are gone. The right long-term solution is Postgres on a cloud provider accessible from the lab network (either get IT to open a port, or install Postgres locally on the lab machine and expose it via a tunnel).

---

## What Was Removed

The project was originally called "Ocean Noise Data Visualizer" and had:
- `explore.py` — explored ocean noise NetCDF files
- `data/noise_data.py` — empty placeholder for noise data
- `/api/noise` endpoint — returned fake noise data
- `Map.jsx` fetching from the noise endpoint

All of this was removed. The project is now purely AIS vessel tracking.

---

## Database Schema

```
ais_202503_dynamic    — CCG position pings
  mmsi INTEGER
  time INTEGER        — unix epoch
  longitude REAL
  latitude REAL
  rot REAL            — rate of turn
  sog REAL            — speed over ground (knots)
  cog REAL            — course over ground (degrees)
  heading REAL
  maneuver INTEGER
  source TEXT

ais_202503_static     — CCG vessel metadata
  mmsi INTEGER
  vessel_name TEXT
  ship_type INTEGER
  call_sign TEXT
  imo TEXT
  ...

ais_satellite         — exactEarth filtered to Scotian Shelf
  mmsi INTEGER
  time TEXT           — ISO format e.g. 20251201T035835Z
  longitude REAL
  latitude REAL
  sog REAL
  cog REAL
  vessel_name TEXT
  ship_type TEXT
```

---

## Next Steps

- [ ] Set up Neon or resolve firewall issue to move to cloud Postgres
- [ ] Add more satellite data files as they come in
- [ ] Add popup on map click showing vessel details (name, MMSI, speed, time)
- [ ] Add vessel type filtering in the sidebar
- [ ] Deploy to Railway with SQLite bundled
- [ ] Integrate real CCG data when full dataset is available (currently only 2 test files)
