import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import time
from math import radians, cos, sin, sqrt, atan2

st.set_page_config(layout="wide")

st.title("🚦 Road Accident Analysis and Alert System")

# -----------------------------
# Load Data
# -----------------------------

risk_data = pd.read_csv("data/export_123.csv")
path_data = pd.read_csv("data/driver_path_points.csv")

# -----------------------------
# Route
# -----------------------------

route = []

for _, row in path_data.iterrows():
    route.append([row["latitude"], row["longitude"]])

# -----------------------------
# Sidebar
# -----------------------------

st.sidebar.header("Route Control")

speed = st.sidebar.slider("Simulation Speed",0.2,2.0,0.8)

start = st.sidebar.button("Start Simulation")
stop = st.sidebar.button("Stop Simulation")
reset = st.sidebar.button("Reset")

# -----------------------------
# Session State
# -----------------------------

if "running" not in st.session_state:
    st.session_state.running = False

if "index" not in st.session_state:
    st.session_state.index = 0

if start:
    st.session_state.running = True

if stop:
    st.session_state.running = False

if reset:
    st.session_state.running = False
    st.session_state.index = 0

# -----------------------------
# Distance Function
# -----------------------------

def distance(lat1,lon1,lat2,lon2):

    R = 6371000

    lat1=radians(lat1)
    lon1=radians(lon1)
    lat2=radians(lat2)
    lon2=radians(lon2)

    dlon=lon2-lon1
    dlat=lat2-lat1

    a=sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c=2*atan2(sqrt(a),sqrt(1-a))

    return R*c

# -----------------------------
# Map Placeholder
# -----------------------------

map_placeholder = st.empty()
alert_box = st.empty()

# -----------------------------
# Current Position
# -----------------------------

current_index = st.session_state.index

if current_index >= len(route):
    current_index = len(route)-1

lat,lon = route[current_index]

# -----------------------------
# Build Map
# -----------------------------

m = folium.Map(location=[lat,lon],zoom_start=12)

# Draw route
folium.PolyLine(route,color="blue",weight=5).add_to(m)

# Accident Zones
for _,row in risk_data.iterrows():

    if row["risk_level"]=="High":
        color="red"

    elif row["risk_level"]=="Medium":
        color="orange"

    else:
        color="yellow"

    # BUFFER ZONE (400m for all)
    folium.Circle(
        location=[row["latitude"],row["longitude"]],
        radius=400,
        color=color,
        fill=True,
        fill_opacity=0.3
    ).add_to(m)

    # STRONG CENTER POINT
    folium.CircleMarker(
        location=[row["latitude"],row["longitude"]],
        radius=8,
        color="black",
        fill=True,
        fill_color=color,
        fill_opacity=1
    ).add_to(m)

    # ALERT CHECK
    d = distance(lat,lon,row["latitude"],row["longitude"])

    if d < 400 and d > 200:
        alert_box.warning(f"⚠ Approaching {row['risk_level']} risk zone")

    elif d <= 200:
        alert_box.error(f"🚨 ENTERED {row['risk_level']} RISK ZONE")

# -----------------------------
# Car Marker
# -----------------------------

folium.Marker(
    [lat,lon],
    icon=folium.Icon(color="blue",icon="car"),
    tooltip="Driver"
).add_to(m)

# -----------------------------
# Show Map
# -----------------------------

with map_placeholder:
    st_folium(m,width=1200,height=650)

# -----------------------------
# Simulation
# -----------------------------

if st.session_state.running:

    time.sleep(speed)

    st.session_state.index += 1

    if st.session_state.index >= len(route):
        st.session_state.running = False
