FROM apache/airflow:slim-3.3.2-python3.12

COPY --chown=airflow:root pyproject.toml README.md LICENSE /opt/retcon/
COPY --chown=airflow:root src/retcon /opt/retcon/src/retcon

# Build and install the same plugin package used by an existing Airflow install.
# Pin Airflow so installing provider dependencies cannot change the base version.
RUN pip install --no-cache-dir "apache-airflow==3.3.2" /opt/retcon && pip check

WORKDIR /opt/airflow
