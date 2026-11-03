# SmartEV – Battery-Aware EV Range Prediction and Charging Route Planner

## 1. Project Overview
SmartEV is a software-based Electric Vehicle (EV) range prediction and charging route planning application. It estimates how far an EV can travel based on battery capacity, battery percentage, State of Health (SOH), energy efficiency, traffic impact, and air-conditioning usage.

It also identifies charging stations stored in a Neo4j graph database and provides charging recommendations based on the estimated driving range.

## 2. Problem Statement
EV drivers may face range anxiety when travelling long distances. Battery condition, traffic, air-conditioning usage, and charging station availability can affect the journey.

SmartEV aims to help drivers understand their estimated driving range and plan charging stops before starting a journey.

## 3. Proposed Solution
SmartEV provides:
- EV battery range estimation.
- Battery State of Health (SOH) consideration.
- Traffic and AC impact adjustment.
- Road route and distance display.
- Charging station recommendations using Neo4j.
- Map visualization of the journey and charging stations.
- Warning when the estimated range is insufficient.

## 4. Technologies Used
- Python
- Streamlit
- Neo4j Aura
- Cypher Query Language
- Folium
- Streamlit-Folium
- OSRM Routing API
- Python Dotenv

## 5. Main Features
1. Battery-based driving range prediction.
2. Battery health consideration.
3. Traffic and AC energy impact estimation.
4. Road distance and route visualization.
5. Charging station search using Neo4j.
6. Charging recommendation and insufficient-range warning.

## 6. Battery Range Calculation
The application uses the following simplified calculation:

**Actual Battery Capacity:**

Actual Capacity = Battery Capacity × SOH / 100

**Usable Energy:**

Usable Energy = Actual Capacity × Battery Percentage / 100

**Estimated Range:**

Estimated Range = Usable Energy / Adjusted Energy Consumption

## 7. Project Structure

```text
Vehicle Route Planner/
│
├── app.py
├── database.py
├── charger.py
├── prediction.py
├── .env
├── .gitignore
└── README.md
```

## 8. Installation and Execution

### Step 1: Install required packages

```bash
pip install streamlit pandas neo4j python-dotenv folium streamlit-folium requests
```

### Step 2: Configure Neo4j

Create a `.env` file and add your Neo4j Aura connection details:

```text
NEO4J_URI=your_neo4j_uri
NEO4J_USERNAME=your_neo4j_username
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=your_neo4j_database
```

Do not upload the `.env` file or share database credentials.

### Step 3: Run the application

```bash
streamlit run app.py
```

## 9. Limitations
- Charging station information is currently demo data and is not verified live availability.
- Some charging station coordinates are approximate.
- OSRM provides route estimates, not live traffic conditions.
- Range predictions are estimates and may differ from actual vehicle performance.
- The application is a software prototype and has not been validated with real EV driving data.

## 10. Future Enhancements
- Integration with verified live charging station APIs.
- Real-time charger availability.
- Live traffic integration.
- Improved range prediction using real-world EV datasets.
- Support for more EV models and routes.

## 11. Conclusion
SmartEV demonstrates how battery information, route planning, and graph database technology can be combined to support EV journey planning. It aims to reduce range anxiety by providing estimated driving range and charging recommendations.