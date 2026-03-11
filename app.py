import streamlit as st
import pandas as pd
import folium
from shapely.geometry import Point
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

st.title("🚦 Road Accident Risk Intelligence System")

# CSV FILE NAME
DATA_FILE = "export_123.csv"

# LOAD DATA
accidents = pd.read_csv(DATA_FILE)

# CREATE GEOMETRY FROM LAT/LON
accidents["geom"] = accidents.apply(
    lambda row: Point(row["longitude"], row["latitude"]), axis=1
)

# DRIVER ROUTE
driver_points = [
    (72.830, 21.170),
    (72.831, 21.171),
    (72.832, 21.172),
    (72.833, 21.173),
    (72.834, 21.174),
    (72.835, 21.175),
]

# SESSION STATE
if "step" not in st.session_state:
    st.session_state.step = 0

driver_location = driver_points[st.session_state.step]
driver_point = Point(driver_location)

# ALERT ENGINE USING DISTANCE
current_state = "SAFE"

for _, row in accidents.iterrows():
    distance = driver_point.distance(row["geom"])

    if distance < 0.002:
        current_state = "INSIDE"
        break
    elif distance < 0.005:
        current_state = "APPROACHING"

# ALERT DISPLAY
if current_state == "INSIDE":
    st.error("🚨 Entered Accident Prone Area")

elif current_state == "APPROACHING":
    st.warning("⚠️ Approaching High Risk Area")

else:
    st.success("✅ Safe Zone")

# MAP CENTER
center_lat = accidents["latitude"].mean()
center_lon = accidents["longitude"].mean()

# CREATE MAP
m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

# ACCIDENT POINTS
for _, row in accidents.iterrows():

    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=6,
        color="red",
        fill=True,
        popup=f"Area: {row['area']} | Severity: {row['severity_index']}"
    ).add_to(m)

# HEATMAP
heat_data = accidents[["latitude", "longitude"]].values.tolist()
HeatMap(heat_data).add_to(m)

# DRIVER ROUTE
path_latlon = [(y, x) for x, y in driver_points]

folium.PolyLine(
    path_latlon,
    color="blue",
    weight=4,
    opacity=0.7
).add_to(m)

# DRIVER MARKER
folium.Marker(
    [driver_location[1], driver_location[0]],
    icon=folium.Icon(color="blue", icon="car"),
    popup="Driver"
).add_to(m)

# DISPLAY MAP
st_folium(m, width=1200, height=650)

# CONTROLS
st.subheader("Driver Simulation")

if st.button("Move Driver"):
    if st.session_state.step < len(driver_points) - 1:
        st.session_state.step += 1
        st.rerun()

if st.button("Reset"):
    st.session_state.step = 0
    st.rerun()

