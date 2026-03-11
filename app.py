# ============================================================
# ROAD ACCIDENT RISK INTELLIGENCE SYSTEM
# Real-time navigation with accident risk alerts
# ============================================================

import streamlit as st
import pandas as pd
import osmnx as ox
import networkx as nx
import folium
import time

from shapely.geometry import Point
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(page_title="Road Accident Risk System", layout="wide")

st.title("🚦 Road Accident Risk Intelligence System")

st.write("""
This system simulates **vehicle navigation** and warns drivers when
they approach **high accident risk zones**.
""")


# ============================================================
# LOAD ACCIDENT DATA
# ============================================================

DATA_FILE = "export_123.csv"

try:
    accidents = pd.read_csv(DATA_FILE)
except:
    st.error("❌ CSV file not found")
    st.stop()

if "latitude" not in accidents.columns or "longitude" not in accidents.columns:
    st.error("CSV must contain latitude and longitude columns")
    st.stop()

# convert to shapely points
accident_points = [
    Point(row["longitude"], row["latitude"])
    for _, row in accidents.iterrows()
]


# ============================================================
# USER INPUT
# ============================================================

st.sidebar.header("Navigation Settings")

start_location = st.sidebar.text_input(
    "Start Location (name OR lat,lon)",
    "Andheri Mumbai"
)

end_location = st.sidebar.text_input(
    "Destination (name OR lat,lon)",
    "Bandra Mumbai"
)

speed_kmh = st.sidebar.slider("Vehicle Speed", 20, 120, 60)

start_button = st.sidebar.button("Start Navigation")


# ============================================================
# GEOCODER
# ============================================================

geolocator = Nominatim(user_agent="risk_navigation_app")


# ============================================================
# FUNCTIONS
# ============================================================

def parse_location(place):

    # allow coordinates
    if "," in place:
        try:
            lat, lon = place.split(",")
            return float(lat), float(lon)
        except:
            return None

    location = geolocator.geocode(place)

    if location:
        return location.latitude, location.longitude

    return None


# ------------------------------------------------------------

def download_roads(center):

    graph = ox.graph_from_point(
        center,
        dist=8000,
        network_type="drive"
    )

    return graph


# ------------------------------------------------------------

def calculate_route(graph, start, end):

    start_node = ox.distance.nearest_nodes(graph, start[1], start[0])
    end_node = ox.distance.nearest_nodes(graph, end[1], end[0])

    route = nx.shortest_path(graph, start_node, end_node, weight="length")

    coords = [(graph.nodes[n]["y"], graph.nodes[n]["x"]) for n in route]

    return coords


# ------------------------------------------------------------

def check_risk(point):

    for risk in accident_points:

        dist = point.distance(risk)

        if dist < 0.0005:
            return "ENTER"

        elif dist < 0.0009:
            return "APPROACH"

    return None


# ------------------------------------------------------------

def draw_accidents(m):

    for _, row in accidents.iterrows():

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color="red",
            fill=True,
            popup="Accident Risk"
        ).add_to(m)


# ------------------------------------------------------------

def simulate_drive(route):

    map_placeholder = st.empty()
    alert_box = st.empty()

    inside = False

    delay = 3600 / (speed_kmh * 1000)

    for coord in route:

        m = folium.Map(location=coord, zoom_start=15)

        # route line
        folium.PolyLine(route, weight=6).add_to(m)

        # accident points
        draw_accidents(m)

        # car marker
        folium.Marker(
            coord,
            tooltip="Vehicle",
            icon=folium.Icon(color="blue", icon="car", prefix="fa")
        ).add_to(m)

        with map_placeholder:
            st_folium(m, width=900, height=600)

        driver_point = Point(coord[1], coord[0])

        risk = check_risk(driver_point)

        if risk == "APPROACH":
            alert_box.warning("⚠ Approaching Accident Risk Zone")

        elif risk == "ENTER":
            inside = True
            alert_box.error("🚨 Entered High Risk Zone")

        else:
            if inside:
                alert_box.success("✅ Exited Risk Zone")
                inside = False

        time.sleep(0.4)


# ============================================================
# MAIN LOGIC
# ============================================================

if start_button:

    st.info("Finding locations...")

    start_point = parse_location(start_location)
    end_point = parse_location(end_location)

    if start_point is None:
        st.error("Start location not found")
        st.stop()

    if end_point is None:
        st.error("Destination not found")
        st.stop()

    st.success("Locations found")

    st.info("Downloading road network...")

    G = download_roads(start_point)

    st.success("Road network ready")

    st.info("Calculating route...")

    route_coords = calculate_route(G, start_point, end_point)

    st.success("Route generated")

    st.write("### 🚗 Navigation Simulation")

    simulate_drive(route_coords)

    st.success("Navigation Completed")


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.markdown("""
Road Accident Risk Intelligence System

Features
- Automatic route generation
- Vehicle movement simulation
- Accident hotspot detection
- Driver risk alerts
""")
