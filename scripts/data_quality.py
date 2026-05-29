#!/usr/bin/env python3
"""
Data quality checks for exactEarth satellite AIS data (Scotian Shelf).

Loads all shelf-filtered rows from the zip files into an in-memory DuckDB table,
then runs a series of checks to identify data issues that could affect the app
or any future analysis.

Run with:
    source venv/bin/activate
    python3 scripts/data_quality.py

Results are printed to stdout. Cross-reference with scripts/FINDINGS.md.
"""

import duckdb
import glob
import os
import tempfile
import zipfile

SAT_DIR = "/home/shared/aisdecode/testData/newSatAis/01"

# Scotian Shelf bounding box (must match pipeline/ingest.py)
XMIN, XMAX = -66.0, -57.0
YMIN, YMAX = 42.0, 47.0


def load_all_shelf_rows(con: duckdb.DuckDBPyConnection):
    """
    Load all Scotian Shelf rows from every satellite zip into a DuckDB table.
    Applies the same bounding box filter as the pipeline so results are comparable.
    """
    con.execute("""
        CREATE TABLE IF NOT EXISTS shelf (
            mmsi        BIGINT,
            time        TEXT,
            longitude   DOUBLE,
            latitude    DOUBLE,
            sog         DOUBLE,
            cog         DOUBLE,
            vessel_name TEXT,
            ship_type   TEXT
        )
    """)

    zip_files = sorted(glob.glob(f"{SAT_DIR}/*.csv.zip"))
    print(f"Loading {len(zip_files)} satellite files into memory...")

    for zip_path in zip_files:
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_path) as z:
                csv_name = z.namelist()[0]
                z.extract(csv_name, tmpdir)
                extracted = os.path.join(tmpdir, csv_name)

            # TRY_CAST silently drops malformed values (sets to NULL)
            # bounding box filter mirrors exactly what ingest.py does
            con.execute(f"""
                INSERT INTO shelf
                SELECT
                    TRY_CAST(MMSI AS BIGINT),
                    Time,
                    TRY_CAST(Longitude AS DOUBLE),
                    TRY_CAST(Latitude  AS DOUBLE),
                    TRY_CAST(SOG AS DOUBLE),
                    TRY_CAST(COG AS DOUBLE),
                    Vessel_Name,
                    Ship_Type
                FROM read_csv('{extracted}', header=true, ignore_errors=true)
                WHERE
                    TRY_CAST(Latitude  AS DOUBLE) BETWEEN {YMIN} AND {YMAX}
                    AND TRY_CAST(Longitude AS DOUBLE) BETWEEN {XMIN} AND {XMAX}
                    AND TRY_CAST(MMSI AS BIGINT) IS NOT NULL
            """)

    total = con.execute("SELECT COUNT(*) FROM shelf").fetchone()[0]
    print(f"Loaded {total:,} shelf rows.\n")


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Check 1: Overall summary
# ---------------------------------------------------------------------------
def check_summary(con):
    section("OVERALL SUMMARY")

    r = con.execute("SELECT COUNT(*), COUNT(DISTINCT mmsi), MIN(time), MAX(time) FROM shelf").fetchone()
    print(f"  Total pings    : {r[0]:,}")
    print(f"  Unique vessels : {r[1]}")
    print(f"  Time range     : {r[2]}  →  {r[3]}")


# ---------------------------------------------------------------------------
# Check 2: Bad rows in the raw files (dropped by TRY_CAST in pipeline)
# These never make it into the DB but understanding their scale matters.
# ---------------------------------------------------------------------------
def check_bad_rows_summary(con):
    section("BAD / MALFORMED ROWS (across all files)")

    # These numbers were pre-computed by explore_satellite.py
    print("  (Pre-computed from full file scan — see explore_satellite.py)")
    print(f"  Total global rows   : ~150,360,547")
    print(f"  Bad rows (TRY_CAST) : ~21,515,651  (~14.3% of global data)")
    print(f"  Scotian Shelf rows  :      62,673   ( ~0.04% of global data)")
    print()
    print("  Bad rows are caused by malformed MMSI, lat, or lon values.")
    print("  They are silently dropped by TRY_CAST — no action needed.")


# ---------------------------------------------------------------------------
# Check 3: Vessels with no name
# Satellite dynamic messages don't carry vessel name — it comes from static
# messages which are not present in this satellite feed. Expected behaviour.
# ---------------------------------------------------------------------------
def check_missing_names(con):
    section("VESSELS WITH NO NAME")

    r = con.execute("""
        SELECT
            COUNT(DISTINCT mmsi) FILTER (WHERE vessel_name IS NULL OR TRIM(vessel_name) = '') AS no_name,
            COUNT(DISTINCT mmsi) AS total
        FROM shelf
    """).fetchone()
    pct = r[0] / r[1] * 100
    print(f"  {r[0]} of {r[1]} vessels ({pct:.0f}%) have no vessel name.")
    print()
    print("  Expected — satellite dynamic AIS messages don't carry vessel name.")
    print("  Name would come from static messages (Type 5/24), not present here.")
    print("  UI shows '—' for name, which is correct.")


# ---------------------------------------------------------------------------
# Check 4: Permanently stationary vessels
# High ping count but SOG always near 0 and position barely moves.
# Could be moored vessels, buoys, or fixed AIS transponders.
# ---------------------------------------------------------------------------
def check_stationary_vessels(con):
    section("PERMANENTLY STATIONARY VESSELS (≥10 pings, avg SOG < 0.1 kt)")

    rows = con.execute("""
        SELECT mmsi, vessel_name, COUNT(*) AS pings,
               ROUND(AVG(sog), 3)                          AS avg_sog,
               ROUND((MAX(latitude)  - MIN(latitude))  * 111000, 1) AS lat_range_m,
               ROUND((MAX(longitude) - MIN(longitude)) * 111000 * 0.7, 1) AS lon_range_m
        FROM shelf
        GROUP BY mmsi, vessel_name
        HAVING COUNT(*) >= 10 AND AVG(sog) < 0.1
        ORDER BY pings DESC
    """).fetchall()

    print(f"  Found {len(rows)} permanently stationary vessels:\n")
    print(f"  {'MMSI':<15} {'Pings':>6} {'AvgSOG':>8} {'LatSpread(m)':>13} {'LonSpread(m)':>13}")
    for r in rows:
        print(f"  {r[0]:<15} {r[2]:>6} {r[3]:>8} {r[4]:>13} {r[5]:>13}")

    print()
    print("  Recommendation: consider filtering these out for noise correlation")
    print("  analysis since they contribute no movement data.")


# ---------------------------------------------------------------------------
# Check 5: Single-ping vessels (no route possible)
# ---------------------------------------------------------------------------
def check_single_ping_vessels(con):
    section("VESSELS WITH ONLY 1 PING (no route possible)")

    rows = con.execute("""
        SELECT mmsi, vessel_name, time, latitude, longitude, sog
        FROM shelf
        WHERE mmsi IN (
            SELECT mmsi FROM shelf GROUP BY mmsi HAVING COUNT(*) = 1
        )
        ORDER BY mmsi
    """).fetchall()

    print(f"  {len(rows)} vessels seen only once — no route can be shown in the app.\n")
    print(f"  {'MMSI':<15} {'Time':<22} {'Lat':>10} {'Lon':>12} {'SOG':>6}")
    for r in rows[:15]:
        print(f"  {r[0]:<15} {r[2]:<22} {r[3]:>10.4f} {r[4]:>12.4f} {str(r[5]):>6}")
    if len(rows) > 15:
        print(f"  ... and {len(rows) - 15} more")


# ---------------------------------------------------------------------------
# Check 6: Long gaps between pings (satellite coverage gaps)
# Gaps > 1 hour suggest the vessel was out of satellite view.
# ---------------------------------------------------------------------------
def check_ping_gaps(con):
    section("VESSELS WITH LARGE GAPS BETWEEN PINGS (gap > 1 hour)")

    rows = con.execute("""
        WITH ordered AS (
            SELECT mmsi, vessel_name, time,
                   LAG(time) OVER (PARTITION BY mmsi ORDER BY time) AS prev_time
            FROM shelf
        ),
        gaps AS (
            SELECT mmsi, vessel_name,
                   DATEDIFF('minute',
                       strptime(prev_time, '%Y%m%dT%H%M%SZ'),
                       strptime(time,      '%Y%m%dT%H%M%SZ')
                   ) AS gap_min
            FROM ordered
            WHERE prev_time IS NOT NULL
        )
        SELECT mmsi, vessel_name,
               ROUND(MAX(gap_min) / 60.0, 1) AS max_gap_h,
               ROUND(AVG(gap_min) / 60.0, 2) AS avg_gap_h,
               COUNT(*) AS n_gaps
        FROM gaps
        GROUP BY mmsi, vessel_name
        HAVING MAX(gap_min) > 60
        ORDER BY max_gap_h DESC
        LIMIT 20
    """).fetchall()

    print(f"  {'MMSI':<15} {'MaxGap(h)':>10} {'AvgGap(h)':>10} {'NumGaps':>8}")
    for r in rows:
        print(f"  {r[0]:<15} {r[2]:>10} {r[3]:>10} {r[4]:>8}")

    print()
    print("  Gaps are caused by satellite orbital coverage, not vessel behaviour.")
    print("  Lines drawn between gapped points may be misleading in the UI.")
    print("  Recommendation: break route lines at gaps > X hours.")


# ---------------------------------------------------------------------------
# Check 7: Duplicate pings (same MMSI + timestamp from multiple satellites)
# ---------------------------------------------------------------------------
def check_duplicates(con):
    section("DUPLICATE PINGS (same MMSI + time, received by multiple satellites)")

    total_dupes = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT mmsi, time FROM shelf GROUP BY mmsi, time HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    rows = con.execute("""
        SELECT mmsi, time, COUNT(*) AS copies
        FROM shelf
        GROUP BY mmsi, time
        HAVING COUNT(*) > 1
        ORDER BY copies DESC
        LIMIT 10
    """).fetchall()

    print(f"  {total_dupes:,} (mmsi, time) pairs have duplicate rows.\n")
    print(f"  {'MMSI':<15} {'Time':<22} {'Copies':>7}")
    for r in rows:
        print(f"  {r[0]:<15} {r[1]:<22} {r[2]:>7}")

    print()
    print("  Cause: same AIS broadcast picked up by multiple satellites.")
    print("  Recommendation: deduplicate on (mmsi, time) before inserting to DB.")


# ---------------------------------------------------------------------------
# Check 8: Speed distribution
# ---------------------------------------------------------------------------
def check_speed_distribution(con):
    section("SPEED DISTRIBUTION (Scotian Shelf pings)")

    rows = con.execute("""
        SELECT
            CASE
                WHEN sog IS NULL             THEN 'no SOG data'
                WHEN sog = 0                 THEN 'stationary (0 kt)'
                WHEN sog BETWEEN 0.01 AND 3  THEN 'slow (0–3 kt)'
                WHEN sog BETWEEN 3.01 AND 10 THEN 'medium (3–10 kt)'
                WHEN sog > 10                THEN 'fast (>10 kt)'
                ELSE 'other'
            END AS category,
            COUNT(*) AS pings,
            COUNT(DISTINCT mmsi) AS vessels
        FROM shelf
        GROUP BY category
        ORDER BY pings DESC
    """).fetchall()

    total_pings = sum(r[1] for r in rows)
    print(f"  {'Category':<25} {'Pings':>8} {'%':>6} {'Vessels':>8}")
    for r in rows:
        pct = r[1] / total_pings * 100
        print(f"  {r[0]:<25} {r[1]:>8,} {pct:>5.1f}% {r[2]:>8}")


# ---------------------------------------------------------------------------
# Run all checks
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    con = duckdb.connect()
    load_all_shelf_rows(con)

    check_summary(con)
    check_bad_rows_summary(con)
    check_missing_names(con)
    check_stationary_vessels(con)
    check_single_ping_vessels(con)
    check_ping_gaps(con)
    check_duplicates(con)
    check_speed_distribution(con)

    con.close()
    print("\nDone. See scripts/FINDINGS.md for analysis and recommendations.")
