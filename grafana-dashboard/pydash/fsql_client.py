from flightsql import FlightSQLClient
import pandas as pd
import re
# `pip install flightsql-dbapi`

from src.metric_panels import MetricPanels

CLIENT = FlightSQLClient(
    host="localhost", port=8816, insecure=True, user="", password=""
)


def basic_checks():
    print("Running GetCatalogs")

    info = CLIENT.get_catalogs()
    reader = CLIENT.do_get(info.endpoints[0].ticket)
    catalogs = reader.read_all().to_pandas()

    print(f"Catalogs: {catalogs}\n")

    print("Running GetDbSchemas")

    info = CLIENT.get_db_schemas()
    reader = CLIENT.do_get(info.endpoints[0].ticket)
    schemas = reader.read_all().to_pandas()

    print(f"Schemas: {schemas}\n")

    print("Running GetTables")

    info = CLIENT.get_tables()
    reader = CLIENT.do_get(info.endpoints[0].ticket)
    tables = reader.read_all().to_pandas()

    print(f"Tables: {tables}\n")


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""

    info = CLIENT.get_tables()
    reader = CLIENT.do_get(info.endpoints[0].ticket)
    tables = reader.read_all().to_pandas()
    existing_tables = tables["table_name"].values

    print(f"Existing tables: {existing_tables}")

    return table_name in tables["table_name"].values


def drain_flight(flight_info) -> pd.DataFrame:
    """Drain an active flight req and return the result."""

    reader = CLIENT.do_get(flight_info.endpoints[0].ticket)
    return reader.read_all().to_pandas()


def create_and_populate_table(table_name: str):
    """Create a table and populate it with some random data."""

    flight = CLIENT.execute(f"""
        CREATE TABLE {table_name} (
            id INTEGER,
            name VARCHAR
        )
    """)

    drain_flight(flight)

    flight = CLIENT.execute(f"""
        INSERT INTO {table_name} VALUES 
        (1, 'Alice'),
        (2, 'Bob')
    """)

    drain_flight(flight)


def drop_table(table_name: str):
    flight = CLIENT.execute(f"DROP TABLE {table_name}")
    drain_flight(flight)


def print_table(table_name: str):
    info = CLIENT.execute(f"SELECT * FROM {table_name}")
    reader = CLIENT.do_get(info.endpoints[0].ticket)
    table = reader.read_all()
    print(table.to_pandas())


def run():
    basic_checks()

    table_name = "test_table"
    print(f"Checking if table {table_name} exists")

    exist_ret = table_exists(table_name)
    print(f"Exist check: {exist_ret}\n")

    if not exist_ret:
        print(f"Table {table_name} does not exist - creating\n")
        create_and_populate_table(table_name)
    else:
        print(f"Table {table_name} already exists - not creating\n")

    print(f"Printing table {table_name}\n")
    print_table(table_name)

    print(f"Dropping table {table_name}\n")
    drop_table(table_name)


def test_panels():
    # panel = MetricPanels.bulk_latency_panel().build()
    panel = MetricPanels.bulk_qsz_panel().build()
    panel_query = panel.targets[0].query_text
    query_stripped = re.sub(r"\$__timeFilter\(timestamp\)\s*AND", "", panel_query)
    df = drain_flight(CLIENT.execute(query_stripped))
    print(df)


def test_metrics():
    metric_name = "HGRPC_RATE_BYTES"
    metric_name = "HGRPC_BLKLAT_NS_AVG"
    query = f"SELECT * FROM orca_metrics WHERE metric_name = '{metric_name}'"
    df = drain_flight(CLIENT.execute(query))
    print(df)

    print_table("orca_twopc_events")


if __name__ == "__main__":
    # run()
    # test_metrics()
    test_panels()
