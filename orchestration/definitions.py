from pathlib import Path

from dagster import Definitions, ScheduleDefinition, define_asset_job
from dagster_dbt import DbtCliResource

from .assets import DBT_PROJECT_DIR, dbt_analytics, generate_landing_data, raw_warehouse_tables

full_pipeline_job = define_asset_job(name="full_pipeline_job", selection="*")

daily_schedule = ScheduleDefinition(
    job=full_pipeline_job,
    cron_schedule="0 5 * * *",  # 5am daily, mimicking a nightly batch pipeline
)

defs = Definitions(
    assets=[generate_landing_data, raw_warehouse_tables, dbt_analytics],
    jobs=[full_pipeline_job],
    schedules=[daily_schedule],
    resources={
        "dbt": DbtCliResource(project_dir=str(DBT_PROJECT_DIR), profiles_dir=str(DBT_PROJECT_DIR)),
    },
)
