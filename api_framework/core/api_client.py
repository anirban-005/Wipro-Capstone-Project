"""Resilient HTTP client for GoRest API interactions."""
from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config_manager import ConfigManager
from core.execution_state import execution_tracker


class ApiClient:
    """A requests session with transient-failure retries and optional auth."""

    def __init__(self, environment: str | None = None, token: str | None = None) -> None:
        config = ConfigManager(environment)
        self.base_url = config.base_url
        self.token = config.token if token is None else token
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _headers(self, authenticated: bool, headers: dict[str, str] | None) -> dict[str, str]:
        merged = {"Accept": "application/json"}
        if authenticated and self.token:
            merged["Authorization"] = f"Bearer {self.token}"
        if headers:
            merged.update(headers)
        return merged

    def request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        headers: dict[str, str] | None = None,
        track_execution: bool = True,
        **kwargs: Any,
    ) -> requests.Response:
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        if track_execution:
            execution_tracker.prepare_request(authenticated=authenticated and bool(self.token))
        if track_execution:
            execution_tracker.request_sent(method, path)
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=self._headers(authenticated, headers),
                timeout=kwargs.pop("timeout", 15),
                **kwargs,
            )
        except requests.RequestException as error:
            if track_execution:
                execution_tracker.transition("RESULT", f"Request error: {error}")
            raise
        if track_execution:
            execution_tracker.response_received(response.status_code, round(response.elapsed.total_seconds() * 1000))
        return response

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", path, **kwargs)
