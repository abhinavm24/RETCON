"""Forward Airflow's native session to its REST API; RETCON adds no role system."""
from contextvars import ContextVar

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware


airflow_token: ContextVar[str | None] = ContextVar("retcon_airflow_token", default=None)


class AirflowSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from airflow.api_fastapi.app import get_auth_manager
        from airflow.api_fastapi.auth.managers.base_auth_manager import COOKIE_NAME_JWT_TOKEN
        from airflow.api_fastapi.core_api.security import resolve_user_from_token

        scheme, _, credentials = request.headers.get("authorization", "").partition(" ")
        token = credentials.strip() if scheme.lower() == "bearer" else request.cookies.get(COOKIE_NAME_JWT_TOKEN)
        try:
            request.state.user = await resolve_user_from_token(token)
        except HTTPException as exc:
            if "/api/" not in request.url.path and request.method in {"GET", "HEAD"}:
                return RedirectResponse(get_auth_manager().get_url_login(), status_code=303)
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

        marker = airflow_token.set(token)
        try:
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"
            return response
        finally:
            airflow_token.reset(marker)
