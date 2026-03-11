import streamlit as st
import pandas as pd
import psycopg2
import folium
import time

from shapely import wkt
from shapely.geometry import Point
from folium.plugins import HeatMap
from streamlit_folium import st_folium


# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(layout="wide")

st.title("🚦 Road Accident Risk Intelligence System")


# ---------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------

@st.cache_resource
def get_connection():

    conn = psycopg2.connect(
        host="localhost",
        database="postgres",
        user="postgres",
        password="mehul123",
        port="5432"
    )

    
    return conn


conn = get_connection()


# ---------------------------------------------------
# LOAD ACCIDENT DATA
# ---------------------------------------------------

accident_query = """
SELECT
id,
area,
severity_index,
risk_level,
buffer_color,
ST_AsText(geom) AS geom,
ST_AsText(buffer_geom) AS buffer_geom
FROM accident_data1
WHERE risk_level='High'
"""

accidents = pd.read_sql(accident_query, conn)

accidents["geom"] = accidents["geom"].apply(wkt.loads)
accidents["buffer_geom"] = accidents["buffer_geom"].apply(wkt.loads)


# ---------------------------------------------------
# LOAD DRIVER PATH
# ---------------------------------------------------

driver_query = """
SELECT ST_AsText(geom) AS geom
FROM driver_path
LIMIT 1
"""

driver_df = pd.read_sql(driver_query, conn)

driver_line = wkt.loads(driver_df.iloc[0]["geom"])

driver_points = list(driver_line.coords)


# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------

if "step" not in st.session_state:
    st.session_state.step = 0

if "previous_state" not in st.session_state:
    st.session_state.previous_state = "SAFE"


# ---------------------------------------------------
# DRIVER CURRENT LOCATION
# ---------------------------------------------------

driver_location = driver_points[st.session_state.step]

driver_point = Point(driver_location)


# ---------------------------------------------------
# ALERT ENGINE
# ---------------------------------------------------

current_state = "SAFE"

for _, row in accidents.iterrows():

    buffer_polygon = row["buffer_geom"]

    if buffer_polygon.contains(driver_point):
        current_state = "INSIDE"
        break

    elif buffer_polygon.distance(driver_point) < 0.004:
        current_state = "APPROACHING"


# ---------------------------------------------------
# ALERT MESSAGE LOGIC
# ---------------------------------------------------

alert_message = ""

if current_state == "APPROACHING" and st.session_state.previous_state == "SAFE":
    alert_message = "⚠️ Entering High Risk Area"

elif current_state == "INSIDE" and st.session_state.previous_state != "INSIDE":
    alert_message = "🚨 Entered Accident Prone Area"

elif current_state == "SAFE" and st.session_state.previous_state == "INSIDE":
    alert_message = "✅ Left Accident Prone Area"

st.session_state.previous_state = current_state


# ---------------------------------------------------
# ALERT DISPLAY
# ---------------------------------------------------

if "Entered" in alert_message:
    st.error(alert_message)

elif "Entering" in alert_message:
    st.warning(alert_message)

elif "Left" in alert_message:
    st.success(alert_message)


# ---------------------------------------------------
# MAP CENTER (AUTO)
# ---------------------------------------------------

center_lat = accidents["geom"].apply(lambda g: g.y).mean()
center_lon = accidents["geom"].apply(lambda g: g.x).mean()


# ---------------------------------------------------
# MAP INITIALIZATION
# ---------------------------------------------------

m = folium.Map(location=[center_lat, center_lon], zoom_start=13)


# ---------------------------------------------------
# ACCIDENT POINTS
# ---------------------------------------------------

for _, row in accidents.iterrows():

    lat = row["geom"].y
    lon = row["geom"].x

    popup_text = f"""
    <b>Accident Area:</b> {row['area']}<br>
    <b>Severity Index:</b> {row['severity_index']}
    """

    folium.CircleMarker(
        location=[lat, lon],
        radius=6,
        color="red",
        fill=True,
        popup=popup_text
    ).add_to(m)


# ---------------------------------------------------
# BUFFER ZONES
# ---------------------------------------------------

for _, row in accidents.iterrows():

    folium.GeoJson(
        row["buffer_geom"].__geo_interface__,
        style_function=lambda x, color=row["buffer_color"]: {
            "fillColor": color,
            "color": color,
            "fillOpacity": 0.35
        }
    ).add_to(m)


# ---------------------------------------------------
# HEATMAP (OPTIONAL ANALYSIS)
# ---------------------------------------------------

heat_data = [[row["geom"].y, row["geom"].x] for _, row in accidents.iterrows()]

HeatMap(heat_data).add_to(m)


# ---------------------------------------------------
# DRIVER ROUTE LINE
# ---------------------------------------------------

path_latlon = [(y, x) for x, y in driver_points]

folium.PolyLine(
    path_latlon,
    color="blue",
    weight=4,
    opacity=0.7,
    tooltip="Driver Route"
).add_to(m)


# ---------------------------------------------------
# DRIVER MARKER
# ---------------------------------------------------

folium.Marker(
    [driver_location[1], driver_location[0]],
    icon=folium.Icon(color="blue", icon="car"),
    popup="Driver Location"
).add_to(m)


# ---------------------------------------------------
# MAP DISPLAY
# ---------------------------------------------------

st_folium(m, width=1200, height=650)


# ---------------------------------------------------
# SIDEBAR DASHBOARD
# ---------------------------------------------------

st.sidebar.header("📊 System Dashboard")

st.sidebar.metric(
    "High Risk Locations",
    len(accidents)
)

st.sidebar.metric(
    "Driver Step",
    st.session_state.step
)

st.sidebar.metric(
    "Driver Status",
    current_state
)


# ---------------------------------------------------
# CONTROL PANEL
# ---------------------------------------------------

st.subheader("🚗 Driver Simulation Controls")

col1, col2, col3 = st.columns(3)


# MOVE DRIVER

if col1.button("Move Driver"):

    if st.session_state.step < len(driver_points) - 1:
        st.session_state.step += 1
        st.rerun()


# AUTO DRIVE

if col2.button("Auto Drive"):

    if st.session_state.step < len(driver_points) - 1:
        st.session_state.step += 1
        time.sleep(1)
        st.rerun()


# RESET SIMULATION

if col3.button("Reset Simulation"):

    st.session_state.step = 0
    st.session_state.previous_state = "SAFE"

    st.rerun()

