"""Expose the DAGs shipped in the RETCON wheel to Airflow's DAG processor."""

from pathlib import Path

from airflow.dag_processing.bundles.base import BaseDagBundle


class RetconDagBundle(BaseDagBundle):
    """An installed-package bundle, available on every Airflow component.

    Install the same RETCON wheel on the DAG processor and workers. Like
    Airflow's LocalDagBundle, this bundle always uses the installed code; it
    does not retain historical package versions for running tasks.
    """

    supports_versioning = False

    @property
    def path(self) -> Path:
        return Path(__file__).resolve().parent / "dags"

    def get_current_version(self) -> None:
        return None

    def refresh(self) -> None:
        """Package installation supplies the files; there is nothing to fetch."""
