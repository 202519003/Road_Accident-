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

st.set_page_config(
    page_title="Road Accident Risk Intelligence",
    layout="wide"
)

st.title("🚦 Road Accident Risk Intelligence System")

st.write(
"""
This system simulates **vehicle navigation** and warns drivers when
they approach **high accident risk zones**.

Steps:
1. Enter start location  
2. Enter destination  
3. System finds road route  
4. Car moves along road  
5. Alerts appear when approaching accident zones  
"""
)

# ============================================================
# LOAD ACCIDENT DATA
# ============================================================

DATA_FILE = "export_123.csv"

try:
    accidents = pd.read_csv(DATA_FILE)
except Exception as e:
    st.error(f"CSV loading error: {e}")
    st.stop()

# ------------------------------------------------------------
# CHECK REQUIRED COLUMNS
# ------------------------------------------------------------

if "latitude" not in accidents.columns or "longitude" not in accidents.columns:
    st.error("CSV must contain 'latitude' and 'longitude' columns.")
    st.stop()

# ------------------------------------------------------------
# CONVERT ACCIDENT POINTS
# ------------------------------------------------------------

accident_points = []

for i, row in accidents.iterrows():
    accident_points.append(
        Point(row["longitude"], row["latitude"])
    )


# ============================================================
# USER INPUT
# ============================================================

st.sidebar.header("Navigation Settings")

start_location = st.sidebar.text_input(
    "Start Location",
    "Dehradun"
)

end_location = st.sidebar.text_input(
    "Destination",
    "ISBT Dehradun"
)

speed_kmh = st.sidebar.slider(
    "Vehicle Speed (km/h)",
    20,
    120,
    60
)

start_button = st.sidebar.button("Start Navigation")


# ============================================================
# GEOCODER
# ============================================================

geolocator = Nominatim(user_agent="risk_navigation_app")


# ============================================================
# FUNCTIONS
# ============================================================

def geocode_location(place):

    location = geolocator.geocode(place)

    if location:
        return (location.latitude, location.longitude)

    return None


# ------------------------------------------------------------

def download_road_network(center_point):

    graph = ox.graph_from_point(
        center_point,
        dist=5000,
        network_type="drive"
    )

    return graph


# ------------------------------------------------------------

def get_route(graph, start, end):

    start_node = ox.distance.nearest_nodes(
        graph,
        start[1],
        start[0]
    )

    end_node = ox.distance.nearest_nodes(
        graph,
        end[1],
        end[0]
    )

    route = nx.shortest_path(
        graph,
        start_node,
        end_node,
        weight="length"
    )

    route_coords = [
        (graph.nodes[n]["y"], graph.nodes[n]["x"])
        for n in route
    ]

    return route_coords


# ------------------------------------------------------------

def check_risk(driver_point):

    for risk in accident_points:

        dist = driver_point.distance(risk)

        # ~50 meters
        if dist < 0.0005:
            return "ENTER"

        # ~100 meters
        elif dist < 0.0008:
            return "APPROACH"

    return None


# ------------------------------------------------------------

def create_map(center):

    m = folium.Map(
        location=center,
        zoom_start=15
    )

    return m


# ------------------------------------------------------------

def draw_accident_points(m):

    for i, row in accidents.iterrows():

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            popup="Accident Risk",
            color="red",
            fill=True
        ).add_to(m)


# ------------------------------------------------------------

def simulate_drive(route_coords):

    alert_placeholder = st.empty()

    map_placeholder = st.empty()

    inside_zone = False

    for coord in route_coords:

        m = create_map(coord)

        # draw route
        folium.PolyLine(
            route_coords,
            weight=5
        ).add_to(m)

        # draw accidents
        draw_accident_points(m)

        # draw car
        folium.Marker(
            coord,
            tooltip="Driver",
            icon=folium.Icon(
                icon="car",
                prefix="fa"
            )
        ).add_to(m)

        map_placeholder.write(
            st_folium(
                m,
                width=900,
                height=600
            )
        )

        driver_point = Point(coord[1], coord[0])

        risk = check_risk(driver_point)

        # -------------------------------------------------
        # ALERT SYSTEM
        # -------------------------------------------------

        if risk == "APPROACH":

            alert_placeholder.warning(
                "⚠ Approaching Accident Risk Zone"
            )

        elif risk == "ENTER":

            inside_zone = True

            alert_placeholder.error(
                "🚨 Entered High Risk Accident Zone"
            )

        else:

            if inside_zone:

                alert_placeholder.success(
                    "✅ Exited Risk Zone"
                )

                inside_zone = False

        time.sleep(0.4)


# ============================================================
# MAIN LOGIC
# ============================================================

if start_button:

    st.info("Geocoding locations...")

    start_point = geocode_location(start_location)
    end_point = geocode_location(end_location)

    if start_point is None:
        st.error("Start location not found")
        st.stop()

    if end_point is None:
        st.error("Destination not found")
        st.stop()

    st.success("Locations found")

    # -------------------------------------------------------

    st.info("Downloading road network...")

    G = download_road_network(start_point)

    st.success("Road network ready")

    # -------------------------------------------------------

    st.info("Calculating route...")

    route_coords = get_route(G, start_point, end_point)

    st.success("Route created")

    # -------------------------------------------------------

    st.write("### Navigation Simulation")

    simulate_drive(route_coords)

    st.success("Navigation Completed")


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.markdown(
"""
Road Accident Risk Intelligence System

Features:
- Automatic route generation
- Real-time vehicle simulation
- Accident hotspot detection
- Driver risk alerts

Powered by OpenStreetMap + Python
"""
)
