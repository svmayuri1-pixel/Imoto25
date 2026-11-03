
import streamlit as st
import folium
import requests
from streamlit_folium import st_folium

from charger import get_charging_stations
from prediction import predict_range, recommend_charging


# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="Imoto25 | EV Intelligence",
    page_icon="⚡",
    layout="wide"
)


# ==========================================
# NEON DRIVE THEME
# ==========================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap');

.stApp {
    background: #080D16;
    color: #F3F7FC;
    font-family: 'Inter', sans-serif;
}

header[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    max-width: 1350px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    color: #F4F7FB !important;
    font-family: 'Inter', sans-serif !important;
}

p, label, .stMarkdown {
    color: #B6C3D2;
}

section[data-testid="stSidebar"] {
    background: #101927;
}

.stTextInput input,
.stNumberInput input {
    background: #141E2D !important;
    color: white !important;
    border: 1px solid #35465B !important;
    border-radius: 10px !important;
}

.stSelectbox div[data-baseweb="select"] {
    background: #141E2D !important;
    border-radius: 10px !important;
}

.stSelectbox div,
.stSelectbox span {
    color: white;
}

.stButton > button {
    background: #B7FF5A;
    color: #101820;
    border: none;
    border-radius: 12px;
    padding: 0.8rem;
    font-weight: 800;
    width: 100%;
}

.stButton > button:hover {
    background: #D4FF9A;
    color: #101820;
    box-shadow: 0 0 20px #B7FF5A55;
}

[data-testid="stMetric"] {
    background: linear-gradient(145deg, #172437, #101927);
    border: 1px solid #304258;
    padding: 18px;
    border-radius: 16px;
}

[data-testid="stMetricValue"] {
    color: #B7FF5A !important;
    font-family: 'Orbitron', sans-serif;
    font-weight: 800;
}

[data-testid="stMetricLabel"] {
    color: #A8B8CB !important;
}

.stProgress > div > div > div > div {
    background-color: #B7FF5A;
}

hr {
    border-color: #29394D;
}

.imoto-logo {
    color: #B7FF5A;
    font-family: 'Orbitron', sans-serif;
    font-size: 38px;
    font-weight: 800;
    letter-spacing: 3px;
}

.imoto-footer {
    text-align: center;
    color: #71849B;
    padding: 25px;
    font-size: 12px;
    letter-spacing: 1px;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# LOCATIONS
# ==========================================

locations = {
    "Chennai": (13.0827, 80.2707),
    "Salem": (11.6643, 78.1460),
    "Bangalore": (12.9716, 77.5946),
    "Coimbatore": (11.0168, 76.9558),
    "Madurai": (9.9252, 78.1198)
}


# ==========================================
# OSRM ROUTE FUNCTION
# ==========================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_road_route(start_coords, end_coords):

    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
    )

    params = {
        "overview": "full",
        "geometries": "geojson"
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        if data.get("code") == "Ok" and data.get("routes"):

            route = data["routes"][0]

            return (
                route["geometry"]["coordinates"],
                route["distance"] / 1000,
                route["duration"] / 60
            )

    except (requests.RequestException, ValueError, KeyError):
        pass

    return None, None, None


# ==========================================
# CHARGER COORDINATE VALIDATION
# ==========================================

def get_charger_coordinates(charger):

    try:
        latitude = float(charger.get("latitude"))
        longitude = float(charger.get("longitude"))

        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return latitude, longitude

    except (TypeError, ValueError):
        pass

    return None


# ==========================================
# HERO
# ==========================================

with st.container(border=True):

    st.caption("⚡ ELECTRIC MOBILITY INTELLIGENCE")

    st.markdown(
        '<p class="imoto-logo">⚡ IMOTO25</p>',
        unsafe_allow_html=True
    )

    st.title("Your Journey. Your Energy.")

    st.write(
        "Intelligent EV range prediction and smarter charging route planning."
    )

    st.success("DRIVE SMARTER • TRAVEL FURTHER")


# ==========================================
# VEHICLE DETAILS
# ==========================================

st.markdown("### 01 / VEHICLE INTELLIGENCE")
st.subheader("Configure Your EV")
st.caption("Enter your battery details to estimate your driving range.")

col1, col2 = st.columns(2)

with col1:
    capacity = st.number_input(
        "🔋 Battery Capacity (kWh)",
        min_value=1.0,
        value=40.0,
        step=1.0
    )

    battery = st.slider(
        "Current Battery Level (%)",
        0, 100, 80
    )

with col2:
    soh = st.slider(
        "Battery Health (SOH %)",
        50, 100, 90
    )

    efficiency = st.number_input(
        "Energy Consumption (kWh/km)",
        min_value=0.01,
        value=0.15,
        step=0.01
    )

st.markdown("#### LIVE INPUT / BATTERY LEVEL")
st.progress(battery / 100)

b1, b2, b3 = st.columns(3)

b1.metric("Battery", f"{battery}%")
b2.metric("Battery Health", f"{soh}%")
b3.metric("Capacity", f"{capacity:.1f} kWh")

st.divider()


# ==========================================
# JOURNEY PLANNER
# ==========================================

st.markdown("### 02 / JOURNEY PLANNER")
st.subheader("Where Are You Going?")

col3, col4 = st.columns(2)

with col3:
    start_location = st.selectbox(
        "📍 Starting Location",
        list(locations.keys())
    )

destination_options = [
    place for place in locations
    if place != start_location
]

with col4:
    destination = st.selectbox(
        "🏁 Destination",
        destination_options
    )

start_coords = locations[start_location]
end_coords = locations[destination]

st.divider()


# ==========================================
# ROAD ROUTE
# ==========================================

st.markdown("### 03 / ROUTE INTELLIGENCE")
st.subheader("Road Route Analysis")

with st.spinner("Calculating road route..."):

    road_coordinates, road_distance, travel_minutes = (
        get_road_route(start_coords, end_coords)
    )

if road_distance is not None:

    r1, r2 = st.columns(2)

    r1.metric("🛣️ Road Distance", f"{road_distance:.2f} km")

    r2.metric(
        "⏱️ Estimated Travel Time",
        f"{travel_minutes / 60:.2f} hours"
    )

    st.success("Road route retrieved successfully.")

    default_distance = float(round(road_distance, 2))

else:

    st.warning(
        "OSRM route service unavailable. Enter journey distance manually."
    )

    default_distance = 350.0

distance = st.number_input(
    "Journey Distance Used for Prediction (km)",
    min_value=1.0,
    value=default_distance,
    step=1.0
)

st.divider()


# ==========================================
# DRIVING CONDITIONS
# ==========================================

st.markdown("### 04 / ENERGY CONDITIONS")
st.subheader("Driving Environment")

col5, col6 = st.columns(2)

with col5:
    traffic = st.slider("🚦 Traffic Impact (%)", 0, 40, 10)

with col6:
    ac_load = st.slider("❄️ AC Load Impact (%)", 0, 20, 5)

adjusted_efficiency = efficiency * (
    1 + (traffic + ac_load) / 100
)

st.metric(
    "Adjusted Energy Consumption",
    f"{adjusted_efficiency:.3f} kWh/km"
)

st.caption("Traffic and AC impacts are demo assumptions.")

st.divider()


# ==========================================
# NEO4J CHARGER LOOKUP
# ==========================================

st.markdown("### 05 / CHARGING NETWORK")
st.subheader("Charging Station Intelligence")

chargers = []

try:

    with st.spinner("Connecting to Neo4j charging network..."):

        chargers = get_charging_stations(
            start_location,
            destination
        )

    with st.expander("Database Debug Information"):

        st.write("Starting Location:", start_location)
        st.write("Destination:", destination)
        st.write("Charger records:", chargers)

    if chargers:

        st.success(
            f"{len(chargers)} charging station record(s) retrieved."
        )

        for charger in chargers:

            with st.container(border=True):

                st.markdown(
                    f"#### 🔌 {charger.get('name', 'Unknown Station')}"
                )

                st.write(
                    "📍 Location:",
                    charger.get("location", "Unknown")
                )

                if charger.get("available") is True:
                    st.success("Demo Available")
                else:
                    st.warning("Unavailable")

                st.write(
                    "Reliability:",
                    charger.get("reliability", "Unknown"),
                    "(demo)"
                )

                coords = get_charger_coordinates(charger)

                if coords:
                    st.caption(
                        f"Approximate coordinates: {coords}"
                    )

    else:
        st.warning("No charging station records found.")

except Exception as error:

    chargers = []

    st.error(f"Neo4j Error: {error}")

st.divider()


# ==========================================
# INTERACTIVE MAP
# ==========================================

st.markdown("### 06 / VISUAL NAVIGATION")
st.subheader("Explore Your Route")

# Create map with OpenStreetMap as the default tile source.
route_map = folium.Map(
    location=start_coords,
    zoom_start=7,
    tiles="OpenStreetMap",
    control_scale=True
)

# Add another map style as an optional layer.
folium.TileLayer(
    tiles="CartoDB positron",
    name="Light Map",
    control=True
).add_to(route_map)


# Start marker
folium.Marker(
    location=start_coords,
    tooltip=f"Start: {start_location}",
    popup=f"Starting Location: {start_location}",
    icon=folium.Icon(
        color="green",
        icon="play",
        prefix="fa"
    )
).add_to(route_map)


# Destination marker
folium.Marker(
    location=end_coords,
    tooltip=f"Destination: {destination}",
    popup=f"Destination: {destination}",
    icon=folium.Icon(
        color="red",
        icon="flag",
        prefix="fa"
    )
).add_to(route_map)


# Draw actual OSRM route if available
if road_coordinates:

    road_points = [
        [lat, lon] for lon, lat in road_coordinates
    ]

    folium.PolyLine(
        locations=road_points,
        color="#80CC28",
        weight=6,
        opacity=0.95,
        tooltip="OSRM Road Route"
    ).add_to(route_map)

    route_map.fit_bounds(road_points)

else:

    # Straight demo connection only, not a real road route.
    folium.PolyLine(
        locations=[start_coords, end_coords],
        color="#80CC28",
        weight=4,
        dash_array="8",
        tooltip="Demo connection - not a road route"
    ).add_to(route_map)

    route_map.fit_bounds([start_coords, end_coords])


# Add charging station markers
for charger in chargers:

    station_coords = get_charger_coordinates(charger)

    if station_coords:

        folium.Marker(
            location=station_coords,
            tooltip=charger.get("name", "Charging Station"),
            popup=(
                f"Station: {charger.get('name', 'Unknown')}<br>"
                f"Location: {charger.get('location', 'Unknown')}<br>"
                f"Availability: {charger.get('available')} (demo)"
            ),
            icon=folium.Icon(
                color="orange",
                icon="bolt",
                prefix="fa"
            )
        ).add_to(route_map)


# Show layer selection control
folium.LayerControl(
    collapsed=True
).add_to(route_map)


# Display interactive map
st_folium(
    route_map,
    width=1100,
    height=520,
    returned_objects=[],
    key="imoto25_route_map"
)

st.caption(
    "🟢 Green: Starting point | 🔴 Red: Destination | "
    "🟠 Orange: Charger | Green line: OSRM route"
)

st.caption(
    "Map tiles require an internet connection. "
    "Charger coordinates may be approximate."
)

st.divider()


# ==========================================
# RANGE PREDICTION
# ==========================================

st.markdown("### 07 / RANGE INTELLIGENCE")
st.subheader("Will You Make It?")

if st.button(
    "⚡ INITIATE JOURNEY ANALYSIS",
    use_container_width=True
):

    energy, estimated_range = predict_range(
        capacity,
        battery,
        adjusted_efficiency,
        soh
    )

    available_chargers = [
        charger for charger in chargers
        if charger.get("available") is True
    ]

    station_distance = None
    first_charger_name = None

    if available_chargers:

        first_charger = available_chargers[0]

        first_charger_name = first_charger.get(
            "name", "Charging Station"
        )

        station_coords = get_charger_coordinates(first_charger)

        if station_coords:

            with st.spinner("Calculating charger road distance..."):

                _, station_distance, _ = get_road_route(
                    start_coords,
                    station_coords
                )

    charger_distance_valid = (
        station_distance is not None
        and station_distance <= distance
    )

    st.divider()

    st.success("ANALYSIS COMPLETE")

    st.markdown("## Your EV Intelligence Report")

    x1, x2, x3 = st.columns(3)

    x1.metric("🔋 Battery Health", f"{soh}%")
    x2.metric("⚡ Usable Energy", f"{energy:.2f} kWh")
    x3.metric("🛣️ Estimated Range", f"{estimated_range:.2f} km")

    st.markdown("### BATTERY STATUS")

    if estimated_range >= distance:

        battery_status = "GREEN"

        st.success(
            "🟢 GREEN — Estimated range covers the destination distance."
        )

    elif (
        charger_distance_valid
        and estimated_range >= station_distance
    ):

        battery_status = "YELLOW"

        st.warning(
            "🟡 YELLOW — Estimated range may reach the selected charger."
        )

    else:

        battery_status = "RED"

        st.error(
            "🔴 RED — Estimated range is insufficient for the destination "
            "or returned charger location."
        )

    st.markdown("### RANGE ANALYSIS")

    y1, y2 = st.columns(2)

    y1.metric("Estimated Range", f"{estimated_range:.2f} km")
    y2.metric("Journey Distance", f"{distance:.2f} km")

    if estimated_range < distance:

        st.warning(
            f"Estimated range shortfall: "
            f"{distance - estimated_range:.2f} km"
        )

    else:

        st.success("Estimated battery range covers the journey.")

    st.markdown("### CHARGING INTELLIGENCE")

    if not available_chargers:

        st.warning("No available charger record returned by Neo4j.")

    elif station_distance is None:

        st.warning(
            "Charger road distance could not be calculated."
        )

    elif not charger_distance_valid:

        st.warning(
            "Approximate charger distance exceeds journey distance. "
            "Check the charger coordinates."
        )

    else:

        recommendation = recommend_charging(
            estimated_range,
            distance,
            available_chargers,
            start_to_charger_distance=station_distance
        )

        st.info(recommendation)

    if station_distance is not None:

        st.metric(
            "Approximate Road Distance to Charger",
            f"{station_distance:.2f} km"
        )

        st.caption(f"Charger checked: {first_charger_name}")

    st.markdown("### JOURNEY REPORT")

    s1, s2 = st.columns(2)

    with s1:

        st.write("📍 Starting Point:", start_location)
        st.write("🏁 Destination:", destination)
        st.write("🛣️ Journey Distance:", f"{distance:.2f} km")
        st.write("🔋 Battery Level:", f"{battery}%")

    with s2:

        st.write("💚 Battery SOH:", f"{soh}%")
        st.write("⚡ Usable Energy:", f"{energy:.2f} kWh")
        st.write("🚗 Estimated Range:", f"{estimated_range:.2f} km")
        st.write(
            "🔌 Available Charger Records:",
            len(available_chargers)
        )

    st.markdown("### FINAL JOURNEY STATUS")

    if battery_status == "GREEN":

        st.success(
            "Destination is reachable based on estimated battery range."
        )

    elif battery_status == "YELLOW":

        st.warning(
            "Estimated range may reach the returned charger location. "
            "Verify actual station location and availability."
        )

    else:

        st.error(
            "Estimated range does not cover the destination "
            "or returned charger location."
        )

    st.markdown("### IMPORTANT INFORMATION")

    st.info(
        "Imoto25 is a demo prediction system. Battery consumption, "
        "traffic and AC impacts are assumptions. Charger availability "
        "and reliability are demo data. Charger coordinates may be "
        "approximate town-centre coordinates, not verified station GPS. "
        "OSRM provides estimated routes, not live traffic. Actual journey "
        "feasibility must be independently verified."
    )


# ==========================================
# FOOTER
# ==========================================

st.markdown("---")

st.markdown(
    '<p class="imoto-footer">'
    'IMOTO25<br><br>'
    'EV RANGE PREDICTION & CHARGING ROUTE PLANNER<br>'
    'DRIVE SMARTER • TRAVEL FURTHER<br><br>'
    'SOFTWARE PROTOTYPE • DEMO VERSION'
    '</p>',
    unsafe_allow_html=True
)
