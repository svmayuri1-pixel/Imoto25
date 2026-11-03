
import streamlit as st
import streamlit.components.v1 as components
import folium
import requests

from charger import get_charging_stations
from prediction import predict_range, recommend_charging


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Imoto25 | EV Intelligence",
    page_icon="⚡",
    layout="wide"
)


# ==========================================
# NEON DRIVE UI THEME
# ==========================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap');

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

/* Main headings */

h1, h2, h3 {
    color: #F4F7FB !important;
    font-family: 'Inter', sans-serif !important;
}

p, label, .stMarkdown {
    color: #B6C3D2;
}

/* Sidebar */

section[data-testid="stSidebar"] {
    background: #101927;
    border-right: 1px solid #263447;
}

/* Inputs */

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

.stSlider [data-baseweb="slider"] {
    color: #B7FF5A;
}

/* Buttons */

.stButton > button {
    background: #B7FF5A;
    color: #101820;
    border: none;
    border-radius: 12px;
    padding: 0.75rem 1rem;
    font-weight: 800;
    width: 100%;
    transition: 0.2s ease;
}

.stButton > button:hover {
    background: #D4FF9A;
    color: #101820;
    box-shadow: 0 0 20px #B7FF5A55;
    transform: translateY(-2px);
}

/* Metrics */

[data-testid="stMetric"] {
    background: linear-gradient(145deg, #172437, #101927);
    border: 1px solid #304258;
    padding: 20px;
    border-radius: 16px;
}

[data-testid="stMetricValue"] {
    color: #B7FF5A !important;
    font-weight: 800;
    font-family: 'Orbitron', sans-serif;
}

[data-testid="stMetricLabel"] {
    color: #A8B8CB !important;
}

/* Tabs */

.stTabs [data-baseweb="tab"] {
    color: #A8B8CB;
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    color: #B7FF5A !important;
    border-bottom-color: #B7FF5A !important;
}

/* Expanders */

.streamlit-expanderHeader {
    background: #172437;
    border-radius: 10px;
    color: white;
}

/* Dividers */

hr {
    border-color: #29394D;
}

/* Custom cards */

.imoto-card {
    background: linear-gradient(145deg, #172437, #101927);
    border: 1px solid #304258;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 12px;
}

.imoto-label {
    color: #9BAFC5;
    font-size: 11px;
    letter-spacing: 2px;
    font-weight: 700;
}

.imoto-value {
    color: #B7FF5A;
    font-size: 30px;
    font-weight: 800;
    font-family: 'Orbitron', sans-serif;
}

.imoto-hero {
    background:
        radial-gradient(circle at 90% 20%, #B7FF5A18, transparent 30%),
        linear-gradient(120deg, #17283D, #0A111D);
    border: 1px solid #34485E;
    border-radius: 24px;
    padding: 35px;
    margin-bottom: 25px;
}

.imoto-logo {
    font-family: 'Orbitron', sans-serif;
    color: #B7FF5A;
    font-size: 38px;
    font-weight: 800;
    letter-spacing: 3px;
}

.imoto-tag {
    color: #B7FF5A;
    letter-spacing: 3px;
    font-size: 11px;
    font-weight: 800;
}

.imoto-subtitle {
    color: #A8B8CB;
    font-size: 15px;
}

.imoto-section {
    background: #111C2B;
    border: 1px solid #27394E;
    padding: 18px 22px;
    border-radius: 14px;
    margin-top: 10px;
    margin-bottom: 15px;
}

.imoto-footer {
    text-align: center;
    color: #71849B;
    font-size: 12px;
    letter-spacing: 1px;
    padding: 20px;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# CITY COORDINATES
# ==========================================

locations = {
    "Chennai": (13.0827, 80.2707),
    "Salem": (11.6643, 78.1460),
    "Bangalore": (12.9716, 77.5946),
    "Coimbatore": (11.0168, 76.9558),
    "Madurai": (9.9252, 78.1198)
}


# ==========================================
# OSRM ROAD ROUTE FUNCTION
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
            timeout=8
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

        return None, None, None

    except (requests.RequestException, ValueError, KeyError):
        return None, None, None


# ==========================================
# CHARGER COORDINATE VALIDATION
# ==========================================

def get_charger_coordinates(charger):

    latitude = charger.get("latitude")
    longitude = charger.get("longitude")

    if latitude is None or longitude is None:
        return None

    try:
        latitude = float(latitude)
        longitude = float(longitude)

        if not (-90 <= latitude <= 90):
            return None

        if not (-180 <= longitude <= 180):
            return None

        return latitude, longitude

    except (TypeError, ValueError):
        return None


# ==========================================
# HERO HEADER
# ==========================================

st.markdown("""
<div class="imoto-hero">

    <div class="imoto-tag">
        ELECTRIC MOBILITY INTELLIGENCE
    </div>

    <div class="imoto-logo">
        ⚡ IMOTO25
    </div>

    <h2 style="font-size:27px; margin-top:10px;">
        Your Journey. Your Energy.
    </h2>

    <p class="imoto-subtitle">
        Intelligent EV range prediction and smarter charging route planning.
    </p>

    <br>

    <span style="
        background:#B7FF5A;
        color:#101820;
        padding:8px 15px;
        border-radius:20px;
        font-size:11px;
        font-weight:800;
        letter-spacing:1px;">
        DRIVE SMARTER • TRAVEL FURTHER
    </span>

</div>
""", unsafe_allow_html=True)


# ==========================================
# DASHBOARD INTRO
# ==========================================

st.markdown("""
<div class="imoto-section">
    <div class="imoto-tag">01 / VEHICLE INTELLIGENCE</div>
    <h3 style="margin-bottom:5px;">Configure Your EV</h3>
    <p style="margin:0;">
        Enter your battery details to estimate your driving range.
    </p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# VEHICLE DETAILS
# ==========================================

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
        0,
        100,
        80
    )

with col2:

    soh = st.slider(
        "Battery Health (SOH %)",
        50,
        100,
        90
    )

    efficiency = st.number_input(
        "Energy Consumption (kWh/km)",
        min_value=0.01,
        value=0.15,
        step=0.01
    )


# Battery visual indicator

st.markdown("""
<div class="imoto-section">
    <div class="imoto-tag">LIVE INPUT / BATTERY LEVEL</div>
</div>
""", unsafe_allow_html=True)

st.progress(battery / 100)

battery_col1, battery_col2, battery_col3 = st.columns(3)

with battery_col1:
    st.metric("Battery", f"{battery}%")

with battery_col2:
    st.metric("Battery Health", f"{soh}%")

with battery_col3:
    st.metric("Capacity", f"{capacity:.1f} kWh")


st.divider()


# ==========================================
# JOURNEY DETAILS
# ==========================================

st.markdown("""
<div class="imoto-section">
    <div class="imoto-tag">02 / JOURNEY PLANNER</div>
    <h3 style="margin-bottom:5px;">Where Are You Going?</h3>
    <p style="margin:0;">
        Select your starting point and destination.
    </p>
</div>
""", unsafe_allow_html=True)

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


# ==========================================
# ROAD ROUTE
# ==========================================

st.markdown("""
<div class="imoto-section">
    <div class="imoto-tag">03 / ROUTE INTELLIGENCE</div>
    <h3 style="margin-bottom:5px;">Road Route Analysis</h3>
</div>
""", unsafe_allow_html=True)

with st.spinner("⚡ Calculating road route..."):

    road_coordinates, road_distance, travel_minutes = (
        get_road_route(start_coords, end_coords)
    )

if road_distance is not None:

    col5, col6 = st.columns(2)

    with col5:
        st.metric(
            "🛣️ Road Distance",
            f"{road_distance:.2f} km"
        )

    with col6:
        st.metric(
            "⏱️ Estimated Travel Time",
            f"{travel_minutes / 60:.2f} hours"
        )

    default_distance = float(round(road_distance, 2))

    st.success("Road route retrieved successfully.")

else:

    st.warning(
        "OSRM route service unavailable. "
        "Please enter journey distance manually."
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

st.markdown("""
<div class="imoto-section">
    <div class="imoto-tag">04 / ENERGY CONDITIONS</div>
    <h3 style="margin-bottom:5px;">Driving Environment</h3>
    <p style="margin:0;">
        Adjust estimated energy consumption for traffic and AC usage.
    </p>
</div>
""", unsafe_allow_html=True)

col7, col8 = st.columns(2)

with col7:

    traffic = st.slider(
        "🚦 Traffic Impact (%)",
        0,
        40,
        10
    )

with col8:

    ac_load = st.slider(
        "❄️ AC Load Impact (%)",
        0,
        20,
        5
    )


adjusted_efficiency = efficiency * (
    1 + (traffic + ac_load) / 100
)

st.metric(
    "Adjusted Energy Consumption",
    f"{adjusted_efficiency:.3f} kWh/km"
)

st.caption(
    "Traffic and AC impacts are demo assumptions."
)


st.divider()


# ==========================================
# NEO4J CHARGER LOOKUP
# ==========================================

st.markdown("""
<div class="imoto-section">
    <div class="imoto-tag">05 / CHARGING NETWORK</div>
    <h3 style="margin-bottom:5px;">Charging Station Intelligence</h3>
    <p style="margin:0;">
        Charger records retrieved from the Neo4j graph database.
    </p>
</div>
""", unsafe_allow_html=True)

chargers = []

try:

    with st.spinner("⚡ Connecting to Neo4j charging network..."):

        chargers = get_charging_stations(
            start_location,
            destination
        )

    with st.expander("🔍 Database Debug Information"):

        st.write("Starting Location:", start_location)
        st.write("Destination:", destination)
        st.write("Charger Records:", chargers)

    if chargers:

        st.success(
            f"{len(chargers)} charging station record(s) retrieved."
        )

        for charger in chargers:

            with st.container(border=True):

                station_col1, station_col2 = st.columns([3, 1])

                with station_col1:

                    st.markdown(
                        f"### 🔌 {charger.get('name', 'Unknown Station')}"
                    )

                    st.write(
                        "📍 Location:",
                        charger.get("location", "Unknown")
                    )

                with station_col2:

                    if charger.get("available") is True:
                        st.success("Demo Available")
                    else:
                        st.error("Unavailable")

                st.write(
                    "Reliability:",
                    charger.get("reliability", "Unknown"),
                    "(demo)"
                )

                coords = get_charger_coordinates(charger)

                if coords:
                    st.caption(f"Approximate coordinates: {coords}")
                else:
                    st.caption("Coordinates unavailable.")

    else:

        st.warning(
            "No charging station records found for this route."
        )

except Exception as error:

    chargers = []

    st.error(f"Neo4j Error: {error}")


st.divider()


# ==========================================
# INTERACTIVE DARK MAP
# ==========================================

st.markdown("""
<div class="imoto-section">
    <div class="imoto-tag">06 / VISUAL NAVIGATION</div>
    <h3 style="margin-bottom:5px;">Explore Your Route</h3>
    <p style="margin:0;">
        View the journey and charging station markers.
    </p>
</div>
""", unsafe_allow_html=True)


route_map = folium.Map(
    location=start_coords,
    zoom_start=7,
    control_scale=True,
    tiles="CartoDB dark_matter"
)


# START MARKER

folium.Marker(
    start_coords,
    tooltip=f"Start: {start_location}",
    popup=f"Starting Location: {start_location}",
    icon=folium.Icon(
        color="green",
        icon="play",
        prefix="fa"
    )
).add_to(route_map)


# DESTINATION MARKER

folium.Marker(
    end_coords,
    tooltip=f"Destination: {destination}",
    popup=f"Destination: {destination}",
    icon=folium.Icon(
        color="red",
        icon="flag",
        prefix="fa"
    )
).add_to(route_map)


# ROAD ROUTE

if road_coordinates:

    road_points = [
        [lat, lon]
        for lon, lat in road_coordinates
    ]

    folium.PolyLine(
        road_points,
        color="#B7FF5A",
        weight=5,
        opacity=0.9,
        tooltip="OSRM road route"
    ).add_to(route_map)

    route_map.fit_bounds(road_points)

else:

    folium.PolyLine(
        [start_coords, end_coords],
        color="#B7FF5A",
        weight=3,
        dash_array="8",
        tooltip="Demo connection - not a road route"
    ).add_to(route_map)


# CHARGER MARKERS

for charger in chargers:

    station_coords = get_charger_coordinates(charger)

    if station_coords:

        station_name = charger.get(
            "name",
            "Charging Station"
        )

        station_location = charger.get(
            "location",
            "Unknown"
        )

        folium.Marker(
            station_coords,
            tooltip=station_name,
            popup=(
                f"<b>{station_name}</b><br>"
                f"Location: {station_location}<br>"
                f"Available: {charger.get('available')}<br>"
                f"Reliability: {charger.get('reliability')} (demo)"
            ),
            icon=folium.Icon(
                color="orange",
                icon="bolt",
                prefix="fa"
            )
        ).add_to(route_map)


map_html = route_map.get_root().render()

components.html(
    map_html,
    height=480,
    scrolling=False
)

st.caption(
    "Neon green: OSRM road route. Orange: charger markers. "
    "Dashed line: demo connection if OSRM is unavailable. "
    "Charger coordinates may be approximate."
)


st.divider()


# ==========================================
# BATTERY RANGE PREDICTION
# ==========================================

st.markdown("""
<div class="imoto-section">
    <div class="imoto-tag">07 / RANGE INTELLIGENCE</div>
    <h3 style="margin-bottom:5px;">Will You Make It?</h3>
    <p style="margin:0;">
        Calculate estimated range and explore charging recommendations.
    </p>
</div>
""", unsafe_allow_html=True)


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
            "name",
            "Charging Station"
        )

        station_coords = get_charger_coordinates(
            first_charger
        )

        if station_coords:

            with st.spinner(
                "Calculating approximate charger road distance..."
            ):

                _, station_distance, _ = get_road_route(
                    start_coords,
                    station_coords
                )

    charger_distance_valid = (
        station_distance is not None
        and station_distance <= distance
    )


    # ======================================
    # RESULTS DASHBOARD
    # ======================================

    st.divider()

    st.markdown("""
    <div class="imoto-hero">
        <div class="imoto-tag">ANALYSIS COMPLETE</div>
        <h2 style="font-size:30px;">Your EV Intelligence Report</h2>
        <p>Here is your estimated battery and journey performance.</p>
    </div>
    """, unsafe_allow_html=True)


    result1, result2, result3 = st.columns(3)

    with result1:

        st.metric(
            "🔋 Battery Health",
            f"{soh}%"
        )

    with result2:

        st.metric(
            "⚡ Usable Energy",
            f"{energy:.2f} kWh"
        )

    with result3:

        st.metric(
            "🛣️ Estimated Range",
            f"{estimated_range:.2f} km"
        )


    # ======================================
    # BATTERY STATUS
    # ======================================

    st.markdown("""
    <div class="imoto-section">
        <div class="imoto-tag">BATTERY STATUS</div>
        <h3>Journey Readiness</h3>
    </div>
    """, unsafe_allow_html=True)


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
            "or the returned charger location."
        )


    # ======================================
    # RANGE COMPARISON
    # ======================================

    st.markdown("""
    <div class="imoto-section">
        <div class="imoto-tag">RANGE ANALYSIS</div>
        <h3>Estimated Range vs Journey</h3>
    </div>
    """, unsafe_allow_html=True)


    comparison_col1, comparison_col2 = st.columns(2)

    with comparison_col1:

        st.metric(
            "Estimated Range",
            f"{estimated_range:.2f} km"
        )

    with comparison_col2:

        st.metric(
            "Journey Distance",
            f"{distance:.2f} km"
        )


    if estimated_range >= distance:

        st.success(
            "Estimated battery range covers the journey."
        )

    else:

        shortfall = distance - estimated_range

        st.warning(
            f"Estimated range shortfall: {shortfall:.2f} km"
        )


    # ======================================
    # CHARGING RECOMMENDATION
    # ======================================

    st.markdown("""
    <div class="imoto-section">
        <div class="imoto-tag">CHARGING INTELLIGENCE</div>
        <h3>Smart Charging Recommendation</h3>
    </div>
    """, unsafe_allow_html=True)


    if not available_chargers:

        st.warning(
            "No available charger record was returned by the Neo4j lookup."
        )

    elif station_distance is None:

        st.warning(
            "Charger road distance could not be calculated. "
            "A charging stop cannot be assessed."
        )

    elif not charger_distance_valid:

        st.warning(
            "Approximate charger distance exceeds journey distance. "
            "Check the charger GPS coordinates."
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

        st.caption(
            f"Charger checked: {first_charger_name}"
        )

    else:

        st.info(
            "No valid charger road distance available."
        )


    # ======================================
    # JOURNEY SUMMARY
    # ======================================

    st.markdown("""
    <div class="imoto-section">
        <div class="imoto-tag">JOURNEY REPORT</div>
        <h3>Your Journey Summary</h3>
    </div>
    """, unsafe_allow_html=True)


    summary_col1, summary_col2 = st.columns(2)

    with summary_col1:

        st.write("📍 **Starting Point:**", start_location)
        st.write("🏁 **Destination:**", destination)
        st.write("🛣️ **Journey Distance:**", f"{distance:.2f} km")
        st.write("🔋 **Battery Level:**", f"{battery}%")


    with summary_col2:

        st.write("💚 **Battery SOH:**", f"{soh}%")
        st.write("⚡ **Usable Energy:**", f"{energy:.2f} kWh")
        st.write("🚗 **Estimated Range:**", f"{estimated_range:.2f} km")
        st.write("🔌 **Available Charger Records:**", len(available_chargers))


    # ======================================
    # FINAL STATUS
    # ======================================

    st.markdown("""
    <div class="imoto-section">
        <div class="imoto-tag">FINAL JOURNEY STATUS</div>
        <h3>Will You Make It?</h3>
    </div>
    """, unsafe_allow_html=True)


    if battery_status == "GREEN":

        st.success(
            "Destination is reachable based on the estimated battery range."
        )

    elif battery_status == "YELLOW":

        st.warning(
            "Estimated range may reach the returned charger location. "
            "Verify the actual station location and availability."
        )

    else:

        st.error(
            "Estimated range does not cover the destination "
            "or the returned charger location."
        )


    # ======================================
    # DISCLAIMER
    # ======================================

    st.markdown("""
    <div class="imoto-card">
        <div class="imoto-tag">IMPORTANT INFORMATION</div>
        <p>
        Imoto25 is a demo prediction system. Battery consumption,
        traffic and AC impacts are assumptions. Charger availability
        and reliability are demo data. Charger coordinates may be
        approximate town-centre coordinates, not verified station GPS.
        OSRM provides estimated routes, not live traffic. Actual journey
        feasibility must be independently verified.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# FOOTER
# ==========================================

st.markdown("""
<div class="imoto-footer">
    ⚡ IMOTO25
    <br><br>
    EV RANGE PREDICTION & CHARGING ROUTE PLANNER
    <br>
    DRIVE SMARTER • TRAVEL FURTHER
    <br><br>
    <span style="color:#52657B;">
        SOFTWARE PROTOTYPE • DEMO VERSION
    </span>
</div>
""", unsafe_allow_html=True)
