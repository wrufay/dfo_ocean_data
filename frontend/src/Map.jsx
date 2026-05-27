import React, { useEffect, useRef, useState } from 'react';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import OSM from 'ol/source/OSM';
import { fromLonLat } from 'ol/proj';
import Feature from 'ol/Feature';
import LineString from 'ol/geom/LineString';
import Point from 'ol/geom/Point';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import { Style, Stroke, Circle as CircleStyle, Fill } from 'ol/style';
import 'ol/ol.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function ShipMap() {
  const mapRef      = useRef(null);
  const mapObj      = useRef(null);
  const sourceRef   = useRef(new VectorSource());

  const [vessels, setVessels]         = useState([]);
  const [search, setSearch]           = useState('');
  const [selected, setSelected]       = useState(null);
  const [start, setStart]             = useState('2025-03-11');
  const [end, setEnd]                 = useState('2025-03-13');
  const [loading, setLoading]         = useState(false);
  const [pointCount, setPointCount]   = useState(null);

  // initialise map once
  useEffect(() => {
    const map = new Map({
      target: mapRef.current,
      layers: [
        new TileLayer({ source: new OSM() }),
        new VectorLayer({
          source: sourceRef.current,
          style: featureStyle,
        }),
      ],
      view: new View({
        center: fromLonLat([-63.5, 44.5]),
        zoom: 6,
      }),
    });
    mapObj.current = map;
    return () => map.setTarget(null);
  }, []);

  // fetch vessel list on mount
  useEffect(() => {
    fetch(`${API}/api/vessels`)
      .then(r => r.json())
      .then(d => setVessels(d.vessels || []))
      .catch(console.error);
  }, []);

  function featureStyle(feature) {
    const type = feature.getGeometry().getType();
    if (type === 'LineString') {
      return new Style({
        stroke: new Stroke({ color: '#127475', width: 2 }),
      });
    }
    // Point — color by speed
    const sog = feature.get('sog') || 0;
    const color = sog > 10 ? '#e63946' : sog > 3 ? '#f4a261' : '#2a9d8f';
    return new Style({
      image: new CircleStyle({
        radius: 4,
        fill: new Fill({ color }),
        stroke: new Stroke({ color: '#fff', width: 1 }),
      }),
    });
  }

  function loadRoute() {
    if (!selected) return;
    setLoading(true);
    setPointCount(null);
    sourceRef.current.clear();

    const params = new URLSearchParams({
      start: `${start}T00:00:00`,
      end:   `${end}T23:59:59`,
    });

    fetch(`${API}/api/vessel/${selected.mmsi}/route?${params}`)
      .then(r => r.json())
      .then(data => {
        const pts = data.points || [];
        setPointCount(pts.length);

        if (pts.length === 0) return;

        const coords = pts.map(p => fromLonLat([p.longitude, p.latitude]));

        // route line
        sourceRef.current.addFeature(
          new Feature({ geometry: new LineString(coords) })
        );

        // individual ping points
        pts.forEach(p => {
          const f = new Feature({
            geometry: new Point(fromLonLat([p.longitude, p.latitude])),
            sog: p.sog,
            time: p.time,
            source: p.source,
          });
          sourceRef.current.addFeature(f);
        });

        // zoom to route
        const extent = sourceRef.current.getExtent();
        mapObj.current.getView().fit(extent, { padding: [60, 60, 60, 60], maxZoom: 12 });
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }

  const filtered = vessels.filter(v => {
    const q = search.toLowerCase();
    return (
      String(v.mmsi).includes(q) ||
      (v.vessel_name || '').toLowerCase().includes(q) ||
      (v.ship_type  || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="relative w-full h-screen">

      {/* Sidebar */}
      <div className="absolute top-0 left-0 h-full w-72 bg-white shadow-lg z-10 flex flex-col overflow-hidden">

        <div className="p-4 border-b">
          <h2 className="font-semibold text-[#127475] text-lg mb-3">Vessel Tracker</h2>

          <input
            className="w-full border rounded px-2 py-1 text-sm mb-3"
            placeholder="Search vessel name or MMSI..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />

          <div className="flex flex-col gap-2 text-sm">
            <label className="flex flex-col gap-0.5">
              <span className="text-gray-500 text-xs">Start date</span>
              <input type="date" className="border rounded px-2 py-1"
                value={start} onChange={e => setStart(e.target.value)} />
            </label>
            <label className="flex flex-col gap-0.5">
              <span className="text-gray-500 text-xs">End date</span>
              <input type="date" className="border rounded px-2 py-1"
                value={end} onChange={e => setEnd(e.target.value)} />
            </label>
          </div>

          <button
            onClick={loadRoute}
            disabled={!selected || loading}
            className="mt-3 w-full bg-[#127475] text-white rounded py-1.5 text-sm disabled:opacity-40"
          >
            {loading ? 'Loading...' : 'Show Route'}
          </button>

          {pointCount !== null && (
            <p className="text-xs text-gray-400 mt-1 text-center">
              {pointCount === 0 ? 'No data for this period.' : `${pointCount} position points`}
            </p>
          )}
        </div>

        {/* Vessel list */}
        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 && (
            <p className="text-xs text-gray-400 p-4 text-center">
              {vessels.length === 0 ? 'Loading vessels...' : 'No vessels match.'}
            </p>
          )}
          {filtered.map(v => (
            <button
              key={v.mmsi}
              onClick={() => { setSelected(v); sourceRef.current.clear(); setPointCount(null); }}
              className={`w-full text-left px-4 py-2 border-b text-sm hover:bg-gray-50 ${
                selected?.mmsi === v.mmsi ? 'bg-teal-50 border-l-4 border-l-[#127475]' : ''
              }`}
            >
              <div className="font-medium truncate">{v.vessel_name || 'Unknown'}</div>
              <div className="text-xs text-gray-400">{v.mmsi} · {v.ship_type || '—'} · {v.source}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Map */}
      <div ref={mapRef} className="w-full h-full pl-72" />

      {/* Speed legend */}
      <div className="absolute bottom-4 right-4 bg-white rounded shadow px-3 py-2 text-xs z-10">
        <div className="font-medium mb-1 text-gray-600">Speed (knots)</div>
        <div className="flex items-center gap-1.5 mb-0.5"><span className="w-3 h-3 rounded-full bg-[#2a9d8f] inline-block"/>&lt; 3</div>
        <div className="flex items-center gap-1.5 mb-0.5"><span className="w-3 h-3 rounded-full bg-[#f4a261] inline-block"/>3 – 10</div>
        <div className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#e63946] inline-block"/>&gt; 10</div>
      </div>

    </div>
  );
}

export default ShipMap;
