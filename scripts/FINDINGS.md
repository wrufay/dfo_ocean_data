# Satellite AIS Data Quality Findings

Data source: exactEarth satellite feed, `/home/shared/aisdecode/testData/newSatAis/01/`  
Analysis date: 2026-05-29  
Files analysed: 24 zip files covering ~25 hours (Nov 30 – Dec 1 2025)

---

## Summary

| Metric | Value |
|---|---|
| Total global rows (all 24 files) | ~150.4M |
| Bad / malformed rows dropped | ~21.5M (14.3%) |
| Scotian Shelf rows kept | 62,673 (0.04%) |
| Unique vessels | 278 |
| Vessels with no name | 276 (99%) |
| Single-ping vessels | 49 |
| Duplicate (mmsi, time) pairs | 4,040 |

---

## Findings

### 1. Bad Rows (14% of global data)
~21.5M rows per file scan had null or unparseable MMSI, latitude, or longitude. These are silently dropped by `TRY_CAST` in the DuckDB query. No action needed — this is expected for a global satellite feed where many transmissions are corrupted.

### 2. No Vessel Names (99% of vessels)
276 of 278 vessels have no name. Satellite dynamic AIS messages (Type 1/2/3/18) don't carry vessel name — that comes from static messages (Type 5/24) which are not present in this feed. The UI correctly shows `—` for unnamed vessels.

**If vessel names are needed:** they'd have to be joined from the CCG static table by MMSI.

### 3. Permanently Stationary Vessels (15 vessels)
15 vessels had ≥10 pings with average SOG < 0.1 knots and position spread under ~100m. These are almost certainly moored vessels, fixed AIS transponders, or navigation buoys — not ships moving through the area.

Top examples:
- MMSI `316054148` — 1,247 pings, avg SOG 0.03 kt
- MMSI `316042994` — 1,099 pings, avg SOG 0.01 kt
- MMSI `316018260` — 831 pings, avg SOG 0.0 kt

**Recommendation:** filter these out for noise correlation analysis since they contribute no movement data and will skew any speed-based analysis.

### 4. Long Gaps Between Pings (satellite coverage gaps)
Some vessels have gaps up to ~20 hours between consecutive pings. This is a satellite orbital coverage issue — when no satellite passes overhead, the vessel goes silent.

Worst gaps:
- MMSI `316007110` — 19.7 hour max gap
- MMSI `316002862` — 16.5 hour max gap
- MMSI `316012015` — 16.2 hour max gap

**UX issue:** the app currently draws a straight line between all position points. A 20-hour gap will draw a misleading straight line across the map where the vessel could have gone anywhere. Consider breaking route lines at gaps > 2–3 hours.

### 5. Single-Ping Vessels (49 vessels)
49 vessels appear only once in the entire 25-hour dataset. No route can be shown for these — they show up in the vessel list but clicking "Show Route" returns nothing.

**Recommendation:** either hide them from the vessel list, or show a message like "only 1 position available" instead of an empty map.

### 6. Duplicate Pings (4,040 pairs)
4,040 (mmsi, time) combinations appear more than once — up to 5 copies of the same ping. Caused by the same AIS broadcast being picked up by multiple satellites simultaneously.

Currently these duplicates are all inserted into the database, which means:
- Slightly inflated ping counts in the UI
- Route lines drawn over themselves

**Recommendation:** deduplicate on `(mmsi, time)` either in `ingest.py` before inserting, or in Neon with `DISTINCT ON (mmsi, time)`.

### 7. Speed Distribution
| Category | Pings | % |
|---|---|---|
| Stationary (0 kt) | 34,653 | 55.3% |
| Fast (>10 kt) | 11,239 | 17.9% |
| Medium (3–10 kt) | 8,334 | 13.3% |
| Slow (0–3 kt) | 7,783 | 12.4% |
| No SOG data | 664 | 1.1% |

Over half of all shelf pings are stationary. Most of these come from the permanently moored vessels above.

---

## Recommended Next Steps

| Priority | Issue | Fix |
|---|---|---|
| High | Duplicate pings in DB | Deduplicate on `(mmsi, time)` in ingest |
| High | Route lines across long gaps | Break line at gaps > 2h in frontend |
| Medium | Single-ping vessels in list | Hide or label them in the UI |
| Medium | Stationary vessels skewing data | Filter by min SOG or min location spread |
| Low | No vessel names from satellite | Join with CCG static table by MMSI |

---

## How to Re-run

```bash
source venv/bin/activate
python3 scripts/data_quality.py
```
