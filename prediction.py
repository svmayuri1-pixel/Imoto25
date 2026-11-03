
from charger import get_charging_stations


def predict_range(battery_capacity, battery_percent, efficiency, soh):
    actual_capacity = battery_capacity * soh / 100
    usable_energy = actual_capacity * battery_percent / 100
    estimated_range = usable_energy / efficiency

    return usable_energy, estimated_range


def recommend_charging(
    estimated_range,
    destination_distance,
    chargers,
    start_to_charger_distance=None
):
    # Check whether destination is reachable
    if estimated_range >= destination_distance:
        return "No charging stop required. Destination is reachable!"

    # Find available charging stations
    suitable_chargers = [
        charger for charger in chargers
        if charger.get("available") is True
    ]

    if not suitable_chargers:
        return "No suitable available charging station found."

    charger = suitable_chargers[0]

    # Check whether the vehicle can reach the charger
    if start_to_charger_distance is not None:
        if estimated_range < start_to_charger_distance:
            return (
                "Warning: Insufficient battery range to reach "
                + str(charger["name"])
            )

    return (
        "Charging stop recommended: "
        + str(charger["name"])
        + " at "
        + str(charger["location"])
        + ". Charger availability is demo data."
    )


if __name__ == "__main__":

    # Demo vehicle details
    capacity = 40
    battery = 80
    efficiency = 0.15
    soh = 90

    # Demo journey: Chennai to Salem
    distance = 200

    # Calculate battery range
    energy, estimated_range = predict_range(
        capacity,
        battery,
        efficiency,
        soh
    )

    # Get charging stations from Neo4j
    chargers = get_charging_stations("Chennai", "Salem")

    print("\n----- IMOTO25 PREDICTION -----")
    print("Battery Capacity:", capacity, "kWh")
    print("Battery Percentage:", battery, "%")
    print("Battery SOH:", soh, "%")
    print("Usable Energy:", energy, "kWh")
    print("Estimated Range:", estimated_range, "km")
    print("Destination Distance:", distance, "km")

    # Demo graph distance from Chennai to Salem charger
    recommendation = recommend_charging(
        estimated_range,
        distance,
        chargers,
        start_to_charger_distance=200
    )

    print("\nRecommendation:", recommendation)
