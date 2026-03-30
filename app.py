"""
Load FDA adverse events CSV data into PostgreSQL.

This script:
1. Loads configuration from a .env file
2. Reads the CSV headers
3. Creates the target schema if needed
4. Creates the target table if needed
5. Creates helpful indexes
6. Truncates the table before reload
7. Loads CSV data into PostgreSQL
8. Reports the final row count
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extensions import connection

from conf.conf import logger


def load_config() -> dict[str, str]:
    """
    Load required configuration from the .env file.

    Returns:
        Dictionary of config values.

    Raises:
        ValueError: If any required value is missing.
    """
    load_dotenv()

    config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "csv_file": os.getenv("CSV_FILE"),
        "schema": os.getenv("DB_SCHEMA", "public"),
        "table": os.getenv("DB_TABLE", "adverse_events"),
    }

    required_keys = ["dbname", "user", "password", "csv_file"]
    missing = [key for key in required_keys if not config.get(key)]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return {key: str(value) for key, value in config.items()}


def get_project_root() -> Path:
    """
    Get the project root based on the location of this script.

    Returns:
        Project root path.
    """
    return Path(__file__).resolve().parent


def resolve_csv_path(csv_file: str) -> Path:
    """
    Resolve the CSV path relative to the project root.

    Args:
        csv_file: CSV path from configuration.

    Returns:
        Absolute CSV file path.
    """
    csv_path = Path(csv_file)

    if csv_path.is_absolute():
        return csv_path

    return get_project_root() / csv_path


def read_csv_headers(csv_path: Path) -> list[str]:
    """
    Read the CSV header row.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        List of column names from the CSV header.
    """
    with csv_path.open(mode="r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        return next(reader)


def connect_db(config: dict[str, str]) -> connection:
    """
    Create a PostgreSQL database connection.

    Args:
        config: Configuration dictionary.

    Returns:
        psycopg2 connection object.
    """
    return psycopg2.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["dbname"],
        user=config["user"],
        password=config["password"],
    )


def create_schema(cursor: Any, schema_name: str) -> None:
    """
    Create the schema if it does not exist.

    Args:
        cursor: Active database cursor.
        schema_name: Name of the schema.
    """
    query = sql.SQL("CREATE SCHEMA IF NOT EXISTS {};").format(
        sql.Identifier(schema_name)
    )
    cursor.execute(query)


def create_table(cursor: Any, schema_name: str, table_name: str) -> None:
    """
    Create the adverse_events table if it does not already exist.

    Args:
        cursor: Active database cursor.
        schema_name: Name of the schema.
        table_name: Name of the table.
    """
    query = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS {}.{} (
            report_id BIGINT PRIMARY KEY,
            receive_date DATE,
            year INTEGER CHECK (year >= 1900 AND year <= 2100),
            month INTEGER CHECK (month BETWEEN 1 AND 12),
            quarter VARCHAR(10),
            serious VARCHAR(20),
            serious_flags TEXT,
            is_fatal BOOLEAN,
            is_hospitalized BOOLEAN,
            is_life_threat BOOLEAN,
            is_disabling BOOLEAN,
            reactions TEXT,
            primary_reaction TEXT,
            reaction_outcomes TEXT,
            patient_recovered BOOLEAN,
            num_reactions INTEGER CHECK (num_reactions >= 0),
            suspect_drug TEXT,
            brand_name TEXT,
            drug_route VARCHAR(100),
            drug_indication TEXT,
            manufacturer TEXT,
            pharm_class TEXT,
            num_drugs INTEGER CHECK (num_drugs >= 0),
            drug_count_category VARCHAR(50),
            patient_age_years NUMERIC(8,2) CHECK (patient_age_years >= 0),
            age_group VARCHAR(50),
            patient_sex VARCHAR(20),
            patient_weight_kg NUMERIC(10,2) CHECK (patient_weight_kg >= 0),
            country VARCHAR(10),
            report_age_days INTEGER CHECK (report_age_days >= 0)
        );
        """
    ).format(sql.Identifier(schema_name), sql.Identifier(table_name))

    cursor.execute(query)


def create_indexes(cursor: Any, schema_name: str, table_name: str) -> None:
    """
    Create useful indexes for common query fields.

    Args:
        cursor: Active database cursor.
        schema_name: Name of the schema.
        table_name: Name of the table.
    """
    index_statements = [
        sql.SQL(
            "CREATE INDEX IF NOT EXISTS {} ON {}.{} (receive_date);"
        ).format(
            sql.Identifier(f"idx_{table_name}_receive_date"),
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
        ),
        sql.SQL(
            "CREATE INDEX IF NOT EXISTS {} ON {}.{} (year);"
        ).format(
            sql.Identifier(f"idx_{table_name}_year"),
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
        ),
        sql.SQL(
            "CREATE INDEX IF NOT EXISTS {} ON {}.{} (brand_name);"
        ).format(
            sql.Identifier(f"idx_{table_name}_brand_name"),
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
        ),
        sql.SQL(
            "CREATE INDEX IF NOT EXISTS {} ON {}.{} (suspect_drug);"
        ).format(
            sql.Identifier(f"idx_{table_name}_suspect_drug"),
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
        ),
        sql.SQL(
            "CREATE INDEX IF NOT EXISTS {} ON {}.{} (manufacturer);"
        ).format(
            sql.Identifier(f"idx_{table_name}_manufacturer"),
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
        ),
        sql.SQL(
            "CREATE INDEX IF NOT EXISTS {} ON {}.{} (country);"
        ).format(
            sql.Identifier(f"idx_{table_name}_country"),
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
        ),
    ]

    for statement in index_statements:
        cursor.execute(statement)


def truncate_table(cursor: Any, schema_name: str, table_name: str) -> None:
    """
    Truncate the target table before reloading.

    Args:
        cursor: Active database cursor.
        schema_name: Name of the schema.
        table_name: Name of the table.
    """
    query = sql.SQL("TRUNCATE TABLE {}.{};").format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name),
    )
    cursor.execute(query)


def load_csv_to_postgres(
    cursor: Any,
    csv_path: Path,
    schema_name: str,
    table_name: str,
) -> None:
    """
    Load CSV data into PostgreSQL using COPY.

    Args:
        cursor: Active database cursor.
        csv_path: Path to the CSV file.
        schema_name: Name of the schema.
        table_name: Name of the table.
    """
    copy_query = sql.SQL(
        """
        COPY {}.{} (
            report_id,
            receive_date,
            year,
            month,
            quarter,
            serious,
            serious_flags,
            is_fatal,
            is_hospitalized,
            is_life_threat,
            is_disabling,
            reactions,
            primary_reaction,
            reaction_outcomes,
            patient_recovered,
            num_reactions,
            suspect_drug,
            brand_name,
            drug_route,
            drug_indication,
            manufacturer,
            pharm_class,
            num_drugs,
            drug_count_category,
            patient_age_years,
            age_group,
            patient_sex,
            patient_weight_kg,
            country,
            report_age_days
        )
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            DELIMITER ','
        );
        """
    ).format(sql.Identifier(schema_name), sql.Identifier(table_name))

    with csv_path.open("r", encoding="utf-8") as file:
        cursor.copy_expert(copy_query.as_string(cursor.connection), file)


def get_row_count(cursor: Any, schema_name: str, table_name: str) -> int:
    """
    Get the row count from the target table.

    Args:
        cursor: Active database cursor.
        schema_name: Name of the schema.
        table_name: Name of the table.

    Returns:
        Row count.
    """
    query = sql.SQL("SELECT COUNT(*) FROM {}.{};").format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name),
    )
    cursor.execute(query)
    result = cursor.fetchone()
    return int(result[0]) if result is not None else 0


def main() -> None:
    """
    Main ETL process.
    """
    try:
        config = load_config()

        logger.info("Starting FDA adverse events load process")

        csv_path = resolve_csv_path(config["csv_file"])
        logger.info("Resolved CSV path: %s", csv_path)

        if not csv_path.exists():
            logger.error("CSV file not found: %s", csv_path)
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        headers = read_csv_headers(csv_path)
        logger.info("CSV headings found: %s", ", ".join(headers))

        logger.info(
            "Connecting to database '%s' on %s:%s",
            config["dbname"],
            config["host"],
            config["port"],
        )

        with connect_db(config) as conn:
            with conn.cursor() as cursor:
                logger.info("Creating schema if not exists: %s",
                            config["schema"])
                create_schema(cursor, config["schema"])

                logger.info(
                    "Creating table if not exists: %s.%s",
                    config["schema"],
                    config["table"],
                )
                create_table(cursor, config["schema"], config["table"])

                logger.info("Creating indexes")
                create_indexes(cursor, config["schema"], config["table"])

                logger.info(
                    "Truncating table before load: %s.%s",
                    config["schema"],
                    config["table"],
                )
                truncate_table(cursor, config["schema"], config["table"])

                logger.info("Loading CSV data into PostgreSQL")
                load_csv_to_postgres(
                    cursor,
                    csv_path,
                    config["schema"],
                    config["table"],
                )

                conn.commit()
                logger.info("Transaction committed successfully")

                row_count = get_row_count(
                    cursor,
                    config["schema"],
                    config["table"],
                )
                logger.info(
                    "Load complete. Total rows in %s.%s: %s",
                    config["schema"],
                    config["table"],
                    row_count,
                )

    except Exception as exc:
        logger.exception("ETL process failed: %s", exc)
        raise


if __name__ == "__main__":
    main()
