
from database import get_driver, DATABASE


def get_charging_stations(start_location, destination):

    driver = get_driver()

    query = """
        MATCH (start:Location {name: $start})
              -[:CONNECTED_TO*1..3]->
              (charger:ChargingStation)

        WHERE charger.available = true

        AND (
            charger.location = $destination

            OR EXISTS {
                MATCH (charger)
                      -[:CONNECTED_TO*1..3]->
                      (:Location {name: $destination})
            }
        )

        RETURN DISTINCT
            charger.name AS name,
            charger.location AS location,
            charger.available AS available,
            charger.reliability AS reliability,
            charger.latitude AS latitude,
            charger.longitude AS longitude

        LIMIT 10
    """

    try:

        with driver.session(database=DATABASE) as session:

            result = session.run(
                query,
                start=start_location,
                destination=destination
            )

            return [
                record.data()
                for record in result
            ]

    finally:

        driver.close()


# TEST CHARGER LOOKUP
if __name__ == "__main__":

    test_routes = [
        ("Chennai", "Salem"),
        ("Chennai", "Bangalore")
    ]

    for start, destination in test_routes:

        print(f"\nTesting: {start} -> {destination}")

        try:

            stations = get_charging_stations(
                start,
                destination
            )

            if stations:

                for station in stations:
                    print(station)

            else:

                print("No charging stations found.")

        except Exception as error:

            print("Error:", error)
