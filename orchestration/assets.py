"""
Dagster asset definitions for the e-commerce pipeline.

Pipeline shape:

    generate_landing_data -> raw_warehouse_tables -> [dbt: staging -> intermediate -> marts]

The two Python assets model the "ingestion" side (a source system dropping
files, and a loader picking them up). The dbt assets are auto-loaded from
the dbt project manifest, so every staging/intermediate/mart model and
snapshot becomes its own asset with full lineage in the Dagster UI.
"""

import subprocess
import sys
from pathlib import Path

from dagster import AssetExecutionContext, AssetKey, AssetOut, MaterializeResult, asset, multi_asset
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT_DIR = ROOT / "dbt_project"

dbt_project = DbtProject(
    project_dir=str(DBT_PROJECT_DIR),
    profiles_dir=str(DBT_PROJECT_DIR),
)
dbt_project.prepare_if_dev()


@asset(group_name="ingestion", compute_kind="python")
def generate_landing_data(context: AssetExecutionContext) -> MaterializeResult:
    """Simulates the source system: generates daily batches into the landing zone."""
    script = ROOT / "ingestion" / "generate_source_data.py"
    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=False
    )
    context.log.info(result.stdout)
    if result.returncode != 0:
        context.log.error(result.stderr)
        raise RuntimeError("generate_source_data.py failed")
    return MaterializeResult(metadata={"stdout_tail": result.stdout[-1000:]})


RAW_ENTITIES = ["raw_customers", "raw_products", "raw_orders", "raw_order_items", "raw_payments"]


@multi_asset(
    group_name="ingestion",
    compute_kind="python",
    deps=[generate_landing_data],
    outs={
        entity: AssetOut(key=AssetKey(["raw", entity]), is_required=False)
        for entity in RAW_ENTITIES
    },
)
def raw_warehouse_tables(context: AssetExecutionContext):
    """Loads the landing zone CSVs into raw.* tables in DuckDB.

    Emits one output per raw table, with asset keys (["raw", <table>]) that
    exactly match the default Dagster asset keys dagster-dbt generates for
    each dbt source -- this is what wires a real dependency edge between
    this ingestion asset and the first layer of dbt staging models.
    """
    script = ROOT / "ingestion" / "load_to_warehouse.py"
    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=False
    )
    context.log.info(result.stdout)
    if result.returncode != 0:
        context.log.error(result.stderr)
        raise RuntimeError("load_to_warehouse.py failed")

    for entity in RAW_ENTITIES:
        yield MaterializeResult(asset_key=AssetKey(["raw", entity]))


@dbt_assets(manifest=dbt_project.manifest_path, project=dbt_project)
def dbt_analytics(context: AssetExecutionContext, dbt: DbtCliResource):
    """All dbt models, snapshots, and tests, with dependencies on the raw load."""
    yield from dbt.cli(["build"], context=context).stream()
