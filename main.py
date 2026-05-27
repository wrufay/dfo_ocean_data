import sqlite3
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# uvicorn main:app --reload

DB_PATH = Path(__file__).parent / "data" / "ais.db"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def root():
    return {"message": "app is running"}


@app.get("/api/vessels")
def get_vessels():
    """List all unique vessels across CCG and satellite data."""
    with get_db() as conn:
        # CCG dynamic + static joined on mmsi
        ccg = conn.execute("""
            SELECT DISTINCT
                d.mmsi,
                s.shipname   AS vessel_name,
                s.shiptype   AS ship_type,
                'CCG'        AS source
            FROM ais_202503_dynamic d
            LEFT JOIN ais_202503_static s ON d.mmsi = s.mmsi
            WHERE d.mmsi IS NOT NULL
        """).fetchall()

        # Satellite
        sat = conn.execute("""
            SELECT DISTINCT
                mmsi,
                vessel_name,
                ship_type,
                'satellite' AS source
            FROM ais_satellite
            WHERE mmsi IS NOT NULL
        """).fetchall()

    seen = set()
    vessels = []
    for row in list(ccg) + list(sat):
        if row["mmsi"] not in seen:
            seen.add(row["mmsi"])
            vessels.append({
                "mmsi":        row["mmsi"],
                "vessel_name": row["vessel_name"],
                "ship_type":   row["ship_type"],
                "source":      row["source"],
            })

    return {"vessels": vessels, "count": len(vessels)}


@app.get("/api/vessel/{mmsi}/route")
def get_vessel_route(
    mmsi: int,
    start: str = Query(None, description="Start time e.g. 2025-03-11T00:00:00"),
    end:   str = Query(None, description="End time e.g. 2025-03-13T23:59:59"),
):
    """
    Return ordered lat/lon track for a vessel in a time range.
    Queries both CCG and satellite tables and merges by time.
    """
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Database not ready yet.")

    points = []

    with get_db() as conn:
        # CCG data — time stored as unix epoch integer
        ccg_query = "SELECT time, longitude, latitude, NULL as sog, NULL as cog FROM ais_202503_dynamic WHERE mmsi = ?"
        params = [mmsi]
        if start:
            ccg_query += " AND time >= strftime('%s', ?)"
            params.append(start)
        if end:
            ccg_query += " AND time <= strftime('%s', ?)"
            params.append(end)
        ccg_query += " ORDER BY time"

        try:
            rows = conn.execute(ccg_query, params).fetchall()
            for r in rows:
                points.append({
                    "time":      r["time"],
                    "latitude":  r["latitude"],
                    "longitude": r["longitude"],
                    "sog":       r["sog"],
                    "cog":       r["cog"],
                    "source":    "CCG",
                })
        except sqlite3.OperationalError:
            pass  # CCG table may not exist yet

        # Satellite data — time stored as ISO string e.g. 20251201T035835Z
        sat_query = "SELECT time, longitude, latitude, sog, cog FROM ais_satellite WHERE mmsi = ?"
        sat_params = [mmsi]
        if start:
            sat_query += " AND time >= ?"
            sat_params.append(start.replace("-", "").replace(":", "").replace(" ", "T"))
        if end:
            sat_query += " AND time <= ?"
            sat_params.append(end.replace("-", "").replace(":", "").replace(" ", "T"))
        sat_query += " ORDER BY time"

        try:
            rows = conn.execute(sat_query, sat_params).fetchall()
            for r in rows:
                points.append({
                    "time":      r["time"],
                    "latitude":  r["latitude"],
                    "longitude": r["longitude"],
                    "sog":       r["sog"],
                    "cog":       r["cog"],
                    "source":    "satellite",
                })
        except sqlite3.OperationalError:
            pass  # satellite table may not exist yet

    # merge and sort by time
    points.sort(key=lambda p: str(p["time"]))

    return {"mmsi": mmsi, "points": points, "count": len(points)}
