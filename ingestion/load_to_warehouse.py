"""
Loads the landing zone (partitioned CSV batches, simulating daily drops from
a source system) into raw tables in DuckDB.

This models a realistic incremental ingestion pattern:
  - each entity's files are read in date-partition order
  - a `_loaded_at` / `_source_file` audit column is stamped on every row
  - loads are append-only into raw.* tables (raw layer is immutable history);
    de-duplication and "latest state" logic is dbt's job downstream, not the
    loader's -- this mirrors how raw/bronze layers work in real warehouses.

Run: python load_to_warehouse.py
"""

import glob
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LANDING = ROOT / "data" / "landing"
DB_PATH = ROOT / "data" / "warehouse.duckdb"

ENTITIES = ["customers", "products", "orders", "order_items", "payments"]


def load_entity(con, entity):
    pattern = str(LANDING / entity / "*" / f"{entity}_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"  no files found for {entity}, skipping")
        return 0

    frames = []
    for f in files:
        df = pd.read_csv(f)
        df["_source_file"] = Path(f).name
        df["_loaded_at"] = datetime.now(timezone.utc).isoformat()
        frames.append(df)

    combined_df = pd.concat(frames, ignore_index=True)
    table = f"raw_{entity}"
    con.execute(f"CREATE OR REPLACE TABLE raw.{table} AS SELECT * FROM combined_df")
    n = con.execute(f"SELECT COUNT(*) FROM raw.{table}").fetchone()[0]
    print(f"  raw.{table}: {n} rows loaded from {len(files)} files")
    return n


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    print(f"Loading landing zone -> {DB_PATH}")
    total = 0
    for entity in ENTITIES:
        total += load_entity(con, entity)

    print(f"\nLoad complete. {total} total rows across {len(ENTITIES)} raw tables.")
    con.close()


if __name__ == "__main__":
    main()
