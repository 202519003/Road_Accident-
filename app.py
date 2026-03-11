import streamlit as st
import pandas as pd
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
# LOAD DATA FROM CSV
# ---------------------------------------------------

# CHANGE THIS NAME to your CSV filename
DATA_FILE = "export_123.csv"

accidents = pd.read_csv(DATA_FILE)

# convert geometry text to shapely objects
accidents["geom"] = accidents["geom"].apply(wkt.loads)
accidents["buffer_geom"] = accidents["buffer_geom"].apply(wkt.loads)

# filter high risk
accidents = accidents[accidents["risk_level"] == "High"]


# ---------------------------------------------------
# DRIVER ROUTE (SIMULATED)
# ---------------------------------------------------

driver_points = [
    (72.830, 21.170),
    (72.831, 21.171),
    (72.832, 21.172),
    (72.833, 21.173),
    (72.834, 21.174),
    (72.835, 21.175),
]


# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------

if "step" not in st.session_state:
    st.session_state.step = 0

if "previous_state" not in st.session_state:
    st.session_state.previous_state = "SAFE"


# ---------------------------------------------------
# DRIVER LOCATION
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
# MAP CENTER
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
    Accident Area: {row['area']} <br>
    Severity Index: {row['severity_index']}
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
# HEATMAP
# ---------------------------------------------------

heat_data = [[row["geom"].y, row["geom"].x] for _, row in accidents.iterrows()]

HeatMap(heat_data).add_to(m)


# ---------------------------------------------------
# DRIVER ROUTE
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
# DISPLAY MAP
# ---------------------------------------------------

st_folium(m, width=1200, height=650)


# ---------------------------------------------------
# SIDEBAR DASHBOARD
# ---------------------------------------------------

st.sidebar.header("📊 System Dashboard")

st.sidebar.metric("High Risk Locations", len(accidents))
st.sidebar.metric("Driver Step", st.session_state.step)
st.sidebar.metric("Driver Status", current_state)


# ---------------------------------------------------
# CONTROL PANEL
# ---------------------------------------------------

st.subheader("🚗 Driver Simulation Controls")

col1, col2, col3 = st.columns(3)

# move driver
if col1.button("Move Driver"):

    if st.session_state.step < len(driver_points) - 1:
        st.session_state.step += 1
        st.rerun()


# auto drive
if col2.button("Auto Drive"):

    if st.session_state.step < len(driver_points) - 1:
        st.session_state.step += 1
        time.sleep(1)
        st.rerun()


# reset
if col3.button("Reset Simulation"):

    st.session_state.step = 0
    st.session_state.previous_state = "SAFE"

    st.rerun()

