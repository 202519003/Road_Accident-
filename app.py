"""
Road Accident Risk Navigation Dashboard
Uses Supabase for data + Leaflet.js for map visualization
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import struct
import math
import os
from supabase import create_client, Client
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# ─────────────────────────────────────────────
# 1. PAGE CONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Road Risk Navigator",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Dark theme accents */
    .main { background-color: #0e1117; }
    .block-container { padding-top: 1rem; }
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .alert-safe    { background:#1a3a1a; border-left:4px solid #00c853; padding:10px 14px; border-radius:6px; margin:6px 0; }
    .alert-warning { background:#3a2a00; border-left:4px solid #ffd600; padding:10px 14px; border-radius:6px; margin:6px 0; }
    .alert-danger  { background:#3a0000; border-left:4px solid #d50000; padding:10px 14px; border-radius:6px; margin:6px 0; }
    .metric-card   { background:#1c1f26; border-radius:10px; padding:14px; text-align:center; }
    .footer-bar    { background:#1c1f26; border-top:1px solid #333; padding:12px 0; text-align:center;
                     color:#888; font-size:0.8rem; margin-top:2rem; border-radius:0 0 8px 8px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. SUPABASE DATA CONNECTION (PostgreSQL Direct)
# ─────────────────────────────────────────────
import psycopg2
from psycopg2.extras import RealDictCursor

@st.cache_resource(show_spinner="Connecting to Supabase…")
def get_db_connection():
    conn = psycopg2.connect(
        host     = st.secrets.get("DB_HOST", "aws-1-ap-south-1.pooler.supabase.com"),
        port     = int(st.secrets.get("DB_PORT", 5432)),
        dbname   = st.secrets.get("DB_NAME", "postgres"),
        user     = st.secrets.get("DB_USER", "postgres.ourldbbwnndtymlznzlo"),
        password = st.secrets.get("DB_PASSWORD", ""),  # never hardcode
        sslmode  = "require"
    )
    return conn


@st.cache_data(ttl=300, show_spinner="Loading accident zones…")
def load_accident_data(_conn) -> pd.DataFrame:
    with _conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM export_123;")
        rows = cur.fetchall()
    df = pd.DataFrame(rows)
    df["latitude"]        = pd.to_numeric(df["latitude"],        errors="coerce")
    df["longitude"]       = pd.to_numeric(df["longitude"],       errors="coerce")
    df["total_accident"]  = pd.to_numeric(df["total_accident"],  errors="coerce").fillna(0)
    df["total_fatality"]  = pd.to_numeric(df["total_fatality"],  errors="coerce").fillna(0)
    df["severity_index"]  = pd.to_numeric(df["severity_index"],  errors="coerce").fillna(0)
    df.dropna(subset=["latitude", "longitude"], inplace=True)
    return df


@st.cache_data(ttl=300, show_spinner="Loading driver path…")
def load_driver_path(_conn) -> list[dict]:
    with _conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM export_Driver_path;")
        rows = cur.fetchall()
    all_paths = []
    for row in rows:
        coords = decode_wkb_linestring(row.get("geom", ""))
        if coords:
            all_paths.append({
                "id":         row.get("id"),
                "created_at": row.get("created_at"),
                "coordinates": coords
            })
    return all_paths

# ─────────────────────────────────────────────
# 3. WKB GEOMETRY DECODER
# ─────────────────────────────────────────────
def decode_wkb_linestring(hex_wkb: str) -> list[list[float]]:
    """Decode PostGIS hex WKB LineString → [[lat, lng], ...]"""
    try:
        raw = bytes.fromhex(hex_wkb)
        byte_order = raw[0]          # 1 = little-endian
        endian = "<" if byte_order == 1 else ">"
        # Skip: byte_order(1) + wkb_type(4) + srid(4) = 9 bytes
        offset = 9
        num_points = struct.unpack_from(endian + "I", raw, offset)[0]
        offset += 4
        coords = []
        for _ in range(num_points):
            x, y = struct.unpack_from(endian + "dd", raw, offset)
            offset += 16
            coords.append([y, x])   # [lat, lng]
        return coords
    except Exception:
        return []


# ─────────────────────────────────────────────
# 4. GEOCODER
# ─────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner="Geocoding location…")
def geocode_location(address: str) -> tuple[float, float] | None:
    """Return (lat, lon) for a free-text address."""
    try:
        geolocator = Nominatim(user_agent="road_risk_navigator_v1", timeout=10)
        result = geolocator.geocode(address)
        if result:
            return result.latitude, result.longitude
        return None
    except Exception as e:
        st.warning(f"Geocoding error: {e}")
        return None


# ─────────────────────────────────────────────
# 5. RISK CHECK FUNCTIONS
# ─────────────────────────────────────────────
RISK_RADIUS_M = 500   # metres around a point to flag as risky

def check_risk_at_point(lat: float, lon: float, accident_df: pd.DataFrame,
                         radius_m: int = RISK_RADIUS_M) -> dict:
    """Return risk info for a given coordinate."""
    nearby = []
    for _, row in accident_df.iterrows():
        dist = geodesic((lat, lon), (row["latitude"], row["longitude"])).meters
        if dist <= radius_m:
            nearby.append({**row.to_dict(), "distance_m": round(dist)})
    if not nearby:
        return {"level": "SAFE", "zones": [], "message": "No accident zones nearby."}
    nearby_df = pd.DataFrame(nearby)
    max_si = nearby_df["severity_index"].max()
    level = "HIGH" if max_si > 25 else ("MEDIUM" if max_si > 10 else "LOW")
    return {
        "level": level,
        "zones": nearby,
        "message": f"{len(nearby)} accident zone(s) within {radius_m}m — max severity {max_si:.1f}"
    }


def get_path_risk_alerts(path_coords: list[list[float]],
                          accident_df: pd.DataFrame) -> list[dict]:
    """Walk driver path and generate alerts for each risky point."""
    alerts = []
    seen_zones = set()
    step = max(1, len(path_coords) // 50)   # sample at most 50 points
    for i, (lat, lng) in enumerate(path_coords[::step]):
        risk = check_risk_at_point(lat, lng, accident_df)
        for zone in risk["zones"]:
            zid = zone["id"]
            if zid not in seen_zones:
                seen_zones.add(zid)
                alerts.append({
                    "path_idx": i * step,
                    "lat": lat,
                    "lng": lng,
                    "zone_id": zid,
                    "area": zone.get("area", ""),
                    "location": zone.get("location", ""),
                    "risk_level": zone.get("risk_level", risk["level"]),
                    "severity_index": zone.get("severity_index", 0),
                    "distance_m": zone["distance_m"],
                })
    return alerts


# ─────────────────────────────────────────────
# 6. LEAFLET MAP BUILDER
# ─────────────────────────────────────────────
def build_leaflet_map(accident_df: pd.DataFrame,
                       driver_paths: list[dict],
                       center_lat: float = 19.076,
                       center_lng: float = 72.877,
                       highlight_point: tuple = None,
                       alerts: list[dict] = None) -> str:
    """Return full HTML string with embedded Leaflet map."""

    # Serialize data to JS-safe JSON
    zones_js = json.dumps([
        {
            "id":   int(r["id"]),
            "lat":  float(r["latitude"]),
            "lng":  float(r["longitude"]),
            "area": str(r.get("area", "")),
            "loc":  str(r.get("location", "")),
            "si":   float(r.get("severity_index", 0)),
            "risk": str(r.get("risk_level", "Low")),
            "ta":   int(r.get("total_accident", 0)),
            "tf":   int(r.get("total_fatality", 0)),
            "color": str(r.get("buffer_color", "#FFFF00")),
        }
        for _, r in accident_df.iterrows()
    ])

    paths_js = json.dumps([
        {"id": p["id"], "coords": p["coordinates"]}
        for p in driver_paths
    ])

    highlight_js = json.dumps(list(highlight_point) if highlight_point else None)
    alerts_js = json.dumps(alerts or [])

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>Road Risk Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body, html {{ margin:0; padding:0; height:100%; background:#0e1117; }}
  #map {{ height:100vh; width:100%; }}
  .risk-popup b {{ font-size:1rem; }}
  .legend {{ background:rgba(20,20,30,0.92); color:#eee; padding:10px 14px;
             border-radius:8px; font-size:0.78rem; line-height:1.7; box-shadow:0 2px 10px #0005; }}
  .legend h4 {{ margin:0 0 6px 0; font-size:0.85rem; border-bottom:1px solid #444; padding-bottom:4px; }}
  .dot {{ width:12px; height:12px; border-radius:50%; display:inline-block; margin-right:6px; vertical-align:middle; }}
</style>
</head>
<body>
<div id="map"></div>
<script>
const ZONES  = {zones_js};
const PATHS  = {paths_js};
const HLIGHT = {highlight_js};
const ALERTS = {alerts_js};

// ── MAP INIT ──────────────────────────────
const map = L.map('map', {{ zoomControl:true, preferCanvas:true }})
              .setView([{center_lat}, {center_lng}], 12);

L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution:'&copy; OpenStreetMap &copy; CartoDB',
  subdomains:'abcd', maxZoom:19
}}).addTo(map);

// ── HELPER: severity → colour ─────────────
function siColor(si) {{
  if (si > 25) return '#d50000';
  if (si > 10) return '#ff6d00';
  return '#ffd600';
}}
function riskIcon(color) {{
  return L.divIcon({{
    className: '',
    html: `<div style="width:14px;height:14px;border-radius:50%;
                background:${{color}};border:2px solid #fff;
                box-shadow:0 0 6px ${{color}}88"></div>`,
    iconSize:[14,14], iconAnchor:[7,7]
  }});
}}

// ── ACCIDENT ZONES ────────────────────────
const zoneLayer = L.layerGroup().addTo(map);
ZONES.forEach(z => {{
  const col = siColor(z.si);
  const marker = L.marker([z.lat, z.lng], {{ icon: riskIcon(col) }});
  marker.bindPopup(`
    <b>🚨 ${{z.area}}</b><br>
    <small>${{z.loc}}</small><hr style="margin:4px 0">
    Severity Index : <b>${{z.si.toFixed(1)}}</b><br>
    Risk Level     : <b style="color:${{col}}">${{z.risk}}</b><br>
    Total Accidents: <b>${{z.ta}}</b><br>
    Fatalities     : <b>${{z.tf}}</b>
  `, {{ maxWidth:220 }});
  // Buffer circle (500m)
  L.circle([z.lat, z.lng], {{
    radius:500, color:col, fillColor:col,
    fillOpacity:0.12, weight:1.5, dashArray:'4 4'
  }}).addTo(map);
  marker.addTo(zoneLayer);
}});

// ── DRIVER PATHS ──────────────────────────
const pathLayer = L.layerGroup().addTo(map);
const PATH_COLORS = ['#00e5ff','#69ff47','#ff4081','#e040fb','#ffab40'];
PATHS.forEach((p, i) => {{
  if (!p.coords || p.coords.length < 2) return;
  const color = PATH_COLORS[i % PATH_COLORS.length];
  const poly = L.polyline(p.coords, {{ color, weight:4, opacity:0.85 }});
  poly.bindPopup(`<b>Driver Path #${{p.id}}</b><br>Points: ${{p.coords.length}}`);
  poly.addTo(pathLayer);
  // Start/End markers
  const startIcon = L.divIcon({{ className:'',
    html:`<div style="background:#00c853;width:12px;height:12px;border-radius:50%;border:2px solid #fff"></div>`,
    iconSize:[12,12], iconAnchor:[6,6] }});
  const endIcon = L.divIcon({{ className:'',
    html:`<div style="background:#d50000;width:12px;height:12px;border-radius:50%;border:2px solid #fff"></div>`,
    iconSize:[12,12], iconAnchor:[6,6] }});
  L.marker(p.coords[0], {{ icon:startIcon }}).bindTooltip('Start').addTo(pathLayer);
  L.marker(p.coords[p.coords.length-1], {{ icon:endIcon }}).bindTooltip('End').addTo(pathLayer);
}});

// ── ALERT MARKERS ON PATH ─────────────────
const alertLayer = L.layerGroup().addTo(map);
ALERTS.forEach(a => {{
  const col = a.risk_level === 'High' ? '#d50000' : (a.risk_level === 'Medium' ? '#ff6d00' : '#ffd600');
  L.circleMarker([a.lat, a.lng], {{
    radius:9, color:col, fillColor:col, fillOpacity:0.5, weight:2
  }}).bindPopup(`
    <b>⚠️ Alert: ${{a.area}}</b><br>
    ${{a.location}}<br>
    Risk: <b style="color:${{col}}">${{a.risk_level}}</b><br>
    Distance: ${{a.distance_m}} m
  `).addTo(alertLayer);
}});

// ── HIGHLIGHT / SEARCH POINT ──────────────
if (HLIGHT) {{
  const hl = L.marker(HLIGHT, {{
    icon: L.divIcon({{
      className:'',
      html:`<div style="background:#00e5ff;width:18px;height:18px;
                 border-radius:50%;border:3px solid #fff;
                 box-shadow:0 0 12px #00e5ff"></div>`,
      iconSize:[18,18], iconAnchor:[9,9]
    }})
  }}).addTo(map);
  hl.bindPopup('<b>📍 Your Location</b>').openPopup();
  map.setView(HLIGHT, 14);
}}

// ── LAYER CONTROL ─────────────────────────
L.control.layers(null, {{
  'Accident Zones': zoneLayer,
  'Driver Paths'  : pathLayer,
  'Path Alerts'   : alertLayer,
}}, {{ collapsed:false }}).addTo(map);

// ── LEGEND ───────────────────────────────
const legend = L.control({{ position:'bottomright' }});
legend.onAdd = () => {{
  const d = L.DomUtil.create('div','legend');
  d.innerHTML = `<h4>🗺 Risk Legend</h4>
    <span class="dot" style="background:#d50000"></span> High Risk<br>
    <span class="dot" style="background:#ff6d00"></span> Medium Risk<br>
    <span class="dot" style="background:#ffd600"></span> Low Risk<br>
    <span class="dot" style="background:#00e5ff"></span> Driver Path<br>
    <span class="dot" style="background:#00c853"></span> Path Start<br>
    <span class="dot" style="background:#d50000"></span> Path End`;
  return d;
}};
legend.addTo(map);
</script>
</body>
</html>"""
    return html


# ─────────────────────────────────────────────
# 7. ALERT DISPLAY HELPERS
# ─────────────────────────────────────────────
def alert_box(level: str, text: str):
    css = {"SAFE": "alert-safe", "LOW": "alert-safe",
           "MEDIUM": "alert-warning", "HIGH": "alert-danger"}.get(level.upper(), "alert-warning")
    icon = {"SAFE": "✅", "LOW": "🟡", "MEDIUM": "⚠️", "HIGH": "🚨"}.get(level.upper(), "ℹ️")
    st.markdown(f'<div class="{css}">{icon} <b>{level}</b> — {text}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 8. MAIN APPLICATION LOGIC
# ─────────────────────────────────────────────
def main():
    # ── Sidebar ──────────────────────────────
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/traffic-jam.png", width=56)
        st.title("Road Risk Navigator")
        st.caption("Powered by Supabase + Leaflet")
        st.divider()

        # Controls
        st.subheader("🎮 Session Controls")
        col1, col2 = st.columns(2)
        with col1:
            start_btn = st.button("▶ Start", use_container_width=True, type="primary")
        with col2:
            stop_btn  = st.button("⏹ Stop",  use_container_width=True)
        run_btn = st.button("🔄 Run / Refresh", use_container_width=True)

        if "running" not in st.session_state:
            st.session_state.running = False

        if start_btn:
            st.session_state.running = True
            st.success("Session started!")
        if stop_btn:
            st.session_state.running = False
            st.warning("Session stopped.")

        st.divider()

        # Location search
        st.subheader("📍 Location Search")
        address_input = st.text_input("Search address / place", placeholder="e.g. Andheri, Mumbai")
        search_btn    = st.button("🔍 Find & Check Risk", use_container_width=True)

        st.divider()

        # Filters
        st.subheader("🔧 Filters")
        risk_filter = st.multiselect("Risk Level", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
        radius_m    = st.slider("Alert Radius (m)", 100, 2000, 500, step=100)
        show_paths  = st.checkbox("Show Driver Paths", value=True)
        show_zones  = st.checkbox("Show Accident Zones", value=True)

    # ── Load Data ────────────────────────────
    conn         = get_db_connection()    # connects via psycopg2
    accident_df  = load_accident_data(conn)
    driver_paths = load_driver_path(conn)

    # Apply risk filter
    if risk_filter:
        filtered_df = accident_df[accident_df["risk_level"].isin(risk_filter)]
    else:
        filtered_df = accident_df

    if not show_zones:
        display_df = accident_df.iloc[0:0]   # empty
    else:
        display_df = filtered_df

    display_paths = driver_paths if show_paths else []

    # ── Header KPIs ──────────────────────────
    st.title("🚦 Road Accident Risk Dashboard")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Hotspots",   len(accident_df))
    k2.metric("High Risk Zones",  int((accident_df["risk_level"] == "High").sum()))
    k3.metric("Total Accidents",  int(accident_df["total_accident"].sum()))
    k4.metric("Total Fatalities", int(accident_df["total_fatality"].sum()))
    k5.metric("Driver Paths",     len(driver_paths))

    st.divider()

    # ── Geocode + Risk Check ──────────────────
    highlight_point = None
    search_alerts   = []

    if search_btn and address_input:
        coords = geocode_location(address_input)
        if coords:
            highlight_point = coords
            risk_info = check_risk_at_point(coords[0], coords[1], accident_df, radius_m)
            st.subheader("📊 Risk Assessment")
            alert_box(risk_info["level"], risk_info["message"])

            if risk_info["zones"]:
                near_df = pd.DataFrame(risk_info["zones"])[
                    ["area", "location", "risk_level", "severity_index",
                     "total_accident", "total_fatality", "distance_m"]
                ].sort_values("distance_m")
                st.dataframe(near_df, use_container_width=True, hide_index=True)
                search_alerts = [
                    {"lat": coords[0], "lng": coords[1],
                     "area": z.get("area",""), "location": z.get("location",""),
                     "risk_level": z.get("risk_level","Low"),
                     "severity_index": z.get("severity_index",0),
                     "distance_m": z.get("distance_m",0)}
                    for z in risk_info["zones"]
                ]
        else:
            st.error("Location not found. Try a more specific address.")

    # ── Path Alerts ───────────────────────────
    path_alerts: list[dict] = []
    if st.session_state.running and driver_paths:
        with st.spinner("Analysing driver path for risk zones…"):
            for p in driver_paths:
                path_alerts += get_path_risk_alerts(p["coordinates"], accident_df)

    combined_alerts = search_alerts + path_alerts

    # ── Alert Panel (while running) ───────────
    if st.session_state.running:
        st.subheader("🚨 Live Path Alerts")
        if path_alerts:
            for a in sorted(path_alerts, key=lambda x: x["severity_index"], reverse=True)[:10]:
                level = a.get("risk_level", "Low").upper()
                msg   = f"{a['area']} — {a['location']} | Severity: {a['severity_index']:.1f} | {a['distance_m']} m away"
                alert_box(level, msg)
        else:
            alert_box("SAFE", "Driver path is clear of high-risk zones within the current radius.")

        # Entry / Exit alerts
        for p in driver_paths:
            if p["coordinates"]:
                st.info(f"🟢 **Approaching** Driver Path #{p['id']} — Start point entered.")
                st.info(f"🔴 **Exiting**    Driver Path #{p['id']} — Destination reached safely.")

    # ── Map ───────────────────────────────────
    st.subheader("🗺️ Interactive Risk Map")

    # Compute center from data
    center_lat = float(display_df["latitude"].mean())  if not display_df.empty else 19.076
    center_lng = float(display_df["longitude"].mean()) if not display_df.empty else 72.877

    map_html = build_leaflet_map(
        accident_df   = display_df,
        driver_paths  = display_paths,
        center_lat    = center_lat,
        center_lng    = center_lng,
        highlight_point = highlight_point,
        alerts        = combined_alerts,
    )
    components.html(map_html, height=600, scrolling=False)

    # ── Data Table ────────────────────────────
    with st.expander("📋 Accident Zone Data Table", expanded=False):
        st.dataframe(
            filtered_df[[
                "id","city","area","location","risk_level",
                "severity_index","total_accident","total_fatality",
                "latitude","longitude"
            ]].sort_values("severity_index", ascending=False),
            use_container_width=True, hide_index=True
        )

    with st.expander("🛣️ Driver Path Raw Data", expanded=False):
        for p in driver_paths:
            st.write(f"**Path #{p['id']}** — {len(p['coordinates'])} coordinate points | Created: {p.get('created_at','')}")
            if p["coordinates"]:
                st.json(p["coordinates"][:5])

    # ── Footer ────────────────────────────────
    st.markdown("""
<div class="footer-bar">
    🚦 <strong>Road Risk Navigator</strong> &nbsp;|&nbsp;
    Data: Supabase PostgreSQL &nbsp;|&nbsp;
    Map: Leaflet.js + CartoDB Dark &nbsp;|&nbsp;
    Geocoding: Nominatim (OpenStreetMap) &nbsp;|&nbsp;
    <em>For road safety awareness only — not a substitute for official traffic guidance.</em>
</div>
""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()

