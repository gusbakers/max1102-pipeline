FROM apache/airflow:3.2.0-python3.12

RUN pip install --no-cache-dir \
    "apache-airflow==3.2.0" \
    "apache-airflow-providers-databricks==7.11.0" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.2.0/constraints-3.12.txt"