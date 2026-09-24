"""RETCON writer workspace hosted by Airflow 3.3's own API server and UI."""

from airflow.plugins_manager import AirflowPlugin

from .plugin_auth import AirflowSessionMiddleware
from .webapp import app


app.add_middleware(AirflowSessionMiddleware)


class RetconPlugin(AirflowPlugin):
    name = "retcon"
    fastapi_apps = [{"app": app, "url_prefix": "/retcon", "name": "RETCON writer workspace"}]
    external_views = [
        {
            "name": "RETCON writer",
            "href": "/retcon/",
            "destination": "nav",
            "url_route": "retcon-writer",
            "category": "browse",
        }
    ]
