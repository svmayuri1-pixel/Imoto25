
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(
    Path(__file__).with_name(".env"),
    override=True
)

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")


def get_driver():

    if not all([URI, USERNAME, PASSWORD, DATABASE]):
        raise ValueError(
            "Neo4j configuration missing. Check .env file."
        )

    return GraphDatabase.driver(
        URI,
        auth=(USERNAME, PASSWORD),
        connection_timeout=30,
        connection_acquisition_timeout=30,
        max_transaction_retry_time=15
    )


if __name__ == "__main__":

    print("Connecting to Neo4j Aura...")

    driver = get_driver()

    try:

        driver.verify_connectivity()

        print("Connection successful!")

        with driver.session(database=DATABASE) as session:

            result = session.run(
                "RETURN 'SmartEV Database Connected' AS message"
            )

            print(result.single()["message"])

    except Exception as error:

        print("Connection Error:", error)

    finally:

        driver.close()
