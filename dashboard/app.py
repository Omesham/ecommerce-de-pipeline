"""
Streamlit dashboard reading directly from the dbt marts in DuckDB.

Run: streamlit run dashboard/app.py
"""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "warehouse.duckdb"

st.set_page_config(page_title="E-Commerce Analytics", layout="wide")


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


def query(sql: str) -> pd.DataFrame:
    return get_connection().execute(sql).fetchdf()


st.title("📦 E-Commerce Analytics Dashboard")
st.caption("Built on dbt marts in DuckDB — orchestrated end-to-end with Dagster.")

if not DB_PATH.exists():
    st.error(
        "No warehouse.duckdb found. Run the pipeline first:\n\n"
        "```\npython ingestion/generate_source_data.py\n"
        "python ingestion/load_to_warehouse.py\n"
        "cd dbt_project && dbt snapshot && dbt build\n```"
    )
    st.stop()

# ---------- KPI row ----------
kpis = query("""
    select
        sum(revenue)  as total_revenue,
        sum(margin)   as total_margin,
        sum(order_count) as total_orders,
        round(sum(revenue) / nullif(sum(order_count), 0), 2) as avg_order_value
    from main_marts.mart_daily_revenue
""").iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", f"${kpis['total_revenue']:,.0f}")
c2.metric("Total Margin", f"${kpis['total_margin']:,.0f}")
c3.metric("Total Orders", f"{int(kpis['total_orders']):,}")
c4.metric("Avg Order Value", f"${kpis['avg_order_value']:,.2f}")

st.divider()

# ---------- Revenue over time ----------
left, right = st.columns([2, 1])

with left:
    st.subheader("Daily Revenue by Channel")
    daily = query("""
        select order_date, channel, revenue
        from main_marts.mart_daily_revenue
        order by order_date
    """)
    fig = px.line(daily, x="order_date", y="revenue", color="channel", markers=True)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Revenue Share by Channel")
    by_channel = query("""
        select channel, sum(revenue) as revenue
        from main_marts.mart_daily_revenue
        group by 1
    """)
    fig2 = px.pie(by_channel, names="channel", values="revenue", hole=0.45)
    fig2.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ---------- Product performance ----------
st.subheader("Revenue by Category")
by_category = query("""
    select category, sum(line_revenue) as revenue, sum(line_margin) as margin
    from main_marts.fact_order_items
    group by 1
    order by revenue desc
""")
fig3 = px.bar(by_category, x="category", y=["revenue", "margin"], barmode="group")
fig3.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ---------- Top customers ----------
st.subheader("Top Customers by Lifetime Revenue")
top_customers = query("""
    select
        first_name || ' ' || last_name as customer,
        country,
        lifetime_orders,
        lifetime_revenue,
        lifetime_margin
    from main_marts.mart_customer_ltv
    order by lifetime_revenue desc
    limit 15
""")
st.dataframe(top_customers, use_container_width=True, hide_index=True)

st.divider()

# ---------- Data quality panel ----------
st.subheader("🔍 Data Quality Snapshot")
dq1, dq2 = st.columns(2)

with dq1:
    missing_email = query("""
        select count(*) as missing_email_count
        from main_staging.stg_customers
        where email is null
    """).iloc[0, 0]
    st.metric("Customers missing email", int(missing_email))

with dq2:
    orphaned = query("""
        select count(*) as orphaned_line_items
        from main_staging.stg_order_items
        where is_orphaned_product
    """).iloc[0, 0]
    st.metric("Order items with invalid product_id", int(orphaned))

st.caption(
    "These numbers come directly from dbt's staging layer and are surfaced "
    "here intentionally -- a real pipeline should make data quality visible, "
    "not hide it."
)
