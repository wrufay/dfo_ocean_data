#!/usr/bin/env python3
"""
Exploratory scripts for investigating satellite AIS data from exactEarth.

These are ad-hoc analysis tools — not part of the main pipeline.
Data source: /home/shared/aisdecode/testData/newSatAis/01/*.csv.zip

Each zip contains one CSV with ~100 columns of decoded AIS data.
We use DuckDB to filter and query without loading everything into memory.

Run any section by commenting/uncommenting at the bottom.
"""

import duckdb
import glob
import os
import tempfile
import zipfile

SAT_DIR = "/home/shared/aisdecode/testData/newSatAis/01"

# Scotian Shelf bounding box (same as pipeline)
XMIN, XMAX = -66.0, -57.0
YMIN, YMAX = 42.0, 47.0


def get_first_zip() -> str:
    """Return the path to the first satellite zip file found."""
    files = sorted(glob.glob(f"{SAT_DIR}/*.csv.zip"))
    if not files:
        raise FileNotFoundError(f"No zip files found in {SAT_DIR}")
    return files[0]


def extract_csv(zip_path: str, tmpdir: str) -> str:
    """Extract the single CSV inside a zip to tmpdir and return its path."""
    with zipfile.ZipFile(zip_path) as z:
        csv_name = z.namelist()[0]
        z.extract(csv_name, tmpdir)
        return os.path.join(tmpdir, csv_name)


def query(zip_path: str, sql_template: str) -> list:
    """
    Run a DuckDB query against a satellite zip file.
    Use {extracted} in your SQL as a placeholder for the CSV path.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        extracted = extract_csv(zip_path, tmpdir)
        sql = sql_template.format(extracted=extracted)
        con = duckdb.connect()
        rows = con.execute(sql).fetchall()
        con.close()
        return rows


# ---------------------------------------------------------------------------
# Script 1: Preview Scotian Shelf rows
# Shows the first 10 rows that pass the bounding box filter.
# ---------------------------------------------------------------------------
def preview_shelf_rows():
    zip_path = get_first_zip()
    print(f"\n--- Scotian Shelf rows from: {os.path.basename(zip_path)} ---")

    rows = query(zip_path, """
        SELECT
            TRY_CAST(MMSI AS BIGINT)     AS mmsi,
            Time                          AS time,
            TRY_CAST(Longitude AS DOUBLE) AS longitude,
            TRY_CAST(Latitude  AS DOUBLE) AS latitude,
            TRY_CAST(SOG AS DOUBLE)       AS sog,
            Vessel_Name                   AS vessel_name
        FROM read_csv('{extracted}', header=true, ignore_errors=true)
        WHERE
            TRY_CAST(Latitude  AS DOUBLE) BETWEEN {ymin} AND {ymax}
            AND TRY_CAST(Longitude AS DOUBLE) BETWEEN {xmin} AND {xmax}
            AND TRY_CAST(MMSI AS BIGINT) IS NOT NULL
        LIMIT 10
    """.format(extracted="{extracted}", ymin=YMIN, ymax=YMAX, xmin=XMIN, xmax=XMAX))

    print(f"{'MMSI':<15} {'Time':<20} {'Lon':>12} {'Lat':>10} {'SOG':>6}  Vessel")
    for row in rows:
        print(f"{str(row[0]):<15} {str(row[1]):<20} {row[2]:>12.4f} {row[3]:>10.4f} {str(row[4]):>6}  {row[5] or '—'}")


# ---------------------------------------------------------------------------
# Script 2: Count total rows vs Scotian Shelf rows
# Gives a sense of how much data gets filtered out.
# ---------------------------------------------------------------------------
def count_shelf_vs_total():
    zip_path = get_first_zip()
    print(f"\n--- Row counts from: {os.path.basename(zip_path)} ---")

    total = query(zip_path, """
        SELECT COUNT(*) FROM read_csv('{extracted}', header=true, ignore_errors=true)
    """)[0][0]

    shelf = query(zip_path, """
        SELECT COUNT(*) FROM read_csv('{extracted}', header=true, ignore_errors=true)
        WHERE
            TRY_CAST(Latitude  AS DOUBLE) BETWEEN {ymin} AND {ymax}
            AND TRY_CAST(Longitude AS DOUBLE) BETWEEN {xmin} AND {xmax}
            AND TRY_CAST(MMSI AS BIGINT) IS NOT NULL
    """.format(extracted="{extracted}", ymin=YMIN, ymax=YMAX, xmin=XMIN, xmax=XMAX))[0][0]

    print(f"Total rows in file : {total:,}")
    print(f"Scotian Shelf rows : {shelf:,}")
    print(f"Filtered out       : {total - shelf:,} ({(total - shelf) / total * 100:.1f}%)")


# ---------------------------------------------------------------------------
# Script 3: Find bad / malformed rows
# Rows where MMSI, lat, or lon couldn't be parsed or are physically impossible.
# These get silently dropped by TRY_CAST in the pipeline.
# ---------------------------------------------------------------------------
def find_bad_rows():
    zip_path = get_first_zip()
    print(f"\n--- Bad rows from: {os.path.basename(zip_path)} ---")

    rows = query(zip_path, """
        SELECT
            MMSI, Time, Longitude, Latitude
        FROM read_csv('{extracted}', header=true, ignore_errors=true)
        WHERE
            TRY_CAST(MMSI AS BIGINT) IS NULL
            OR TRY_CAST(Latitude  AS DOUBLE) IS NULL
            OR TRY_CAST(Longitude AS DOUBLE) IS NULL
            OR TRY_CAST(Latitude  AS DOUBLE) NOT BETWEEN -90  AND 90
            OR TRY_CAST(Longitude AS DOUBLE) NOT BETWEEN -180 AND 180
        LIMIT 10
    """)

    print(f"Bad rows found: {len(rows)}")
    for row in rows:
        print(row)


# ---------------------------------------------------------------------------
# Script 4: Speed distribution on the Scotian Shelf
# Breaks down how many vessels are stationary, slow, or fast.
# ---------------------------------------------------------------------------
def speed_distribution():
    zip_path = get_first_zip()
    print(f"\n--- Speed distribution from: {os.path.basename(zip_path)} ---")

    rows = query(zip_path, """
        SELECT
            CASE
                WHEN TRY_CAST(SOG AS DOUBLE) = 0                        THEN 'stationary (0 kt)'
                WHEN TRY_CAST(SOG AS DOUBLE) BETWEEN 0.01 AND 3         THEN 'slow (0-3 kt)'
                WHEN TRY_CAST(SOG AS DOUBLE) BETWEEN 3.01 AND 10        THEN 'medium (3-10 kt)'
                WHEN TRY_CAST(SOG AS DOUBLE) > 10                       THEN 'fast (>10 kt)'
                ELSE 'unknown'
            END AS speed_category,
            COUNT(*) AS count
        FROM read_csv('{extracted}', header=true, ignore_errors=true)
        WHERE
            TRY_CAST(Latitude  AS DOUBLE) BETWEEN {ymin} AND {ymax}
            AND TRY_CAST(Longitude AS DOUBLE) BETWEEN {xmin} AND {xmax}
            AND TRY_CAST(MMSI AS BIGINT) IS NOT NULL
        GROUP BY speed_category
        ORDER BY count DESC
    """.format(extracted="{extracted}", ymin=YMIN, ymax=YMAX, xmin=XMIN, xmax=XMAX))

    for row in rows:
        print(f"  {row[0]:<25} {row[1]:,}")


# ---------------------------------------------------------------------------
# Run all scripts
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    preview_shelf_rows()
    count_shelf_vs_total()
    find_bad_rows()
    speed_distribution()
