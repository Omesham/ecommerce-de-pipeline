FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DBT_PROFILES_DIR=/app/dbt_project
ENV DAGSTER_HOME=/app/.dagster_home

RUN mkdir -p /app/.dagster_home /app/data

EXPOSE 3000 8501

CMD ["bash"]
