import streamlit as st
import pandas as pd
import osmnx as ox
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import time

st.title("🚦 Road Accident Risk Intelligence System")

# -----------------------------
# LOAD ACCIDENT DATA
# -----------------------------

DATA_FILE = "OSM_map.csv"

accidents = pd.read_csv(DATA_FILE)

# make sure columns exist
accidents = accidents.rename(columns={
    "lat": "latitude",
    "lon": "longitude"
})

# -----------------------------
# USER INPUT
# -----------------------------

start_location = st.text_input("Enter Start Location", "Varachha, Surat")
end_location = st.text_input("Enter Destination", "Adajan, Surat")

run_button = st.button("Calculate Route")

# -----------------------------
# ROUTE CALCULATION
# -----------------------------

if run_button:

    st.write("Downloading road network from OpenStreetMap...")

    place = "Mumbai, Maharashtra, India"

    G = ox.graph_from_place(place, network_type="drive")

    start = ox.geocode(start_location)
    end = ox.geocode(end_location)

    orig = ox.distance.nearest_nodes(G, start[1], start[0])
    dest = ox.distance.nearest_nodes(G, end[1], end[0])

    route = ox.shortest_path(G, orig, dest)

    # -----------------------------
    # CREATE MAP
    # -----------------------------

    route_map = ox.plot_route_folium(G, route)

    # add accident markers
    for i, row in accidents.iterrows():

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=6,
            popup="Accident Risk Zone",
            color="red",
            fill=True
        ).add_to(route_map)

    st.write("Route Map")
    st_folium(route_map, width=700)

    # -----------------------------
    # DRIVER SIMULATION
    # -----------------------------

    st.write("Driver Simulation Started")

    nodes = route

    for node in nodes:

        point = (G.nodes[node]["y"], G.nodes[node]["x"])

        for i, row in accidents.iterrows():

            accident_point = (row["latitude"], row["longitude"])

            distance = geodesic(point, accident_point).meters

            if distance < 500:
                st.warning("⚠ Approaching Risk Zone")

            if distance < 100:
                st.error("🚨 Entered Risk Zone")

        time.sleep(0.5)

    st.success("✅ Route Completed")
