# Description: LogicMonitor REST API client with authentication support.
# Description: Handles Bearer token and LMv1 authentication for LM API interactions.

"""LogicMonitor REST API client with authentication support."""

import base64
import hashlib
import hmac
import json as json_module
import logging
import time
from collections.abc import Generator
from typing import Any

import httpx
from pydantic import SecretStr

from lm_cloud_sync.core.exceptions import LMAPIError, RateLimitError

logger = logging.getLogger(__name__)


class BearerAuth(httpx.Auth):
    """Bearer token authentication for LogicMonitor API."""

    def __init__(self, token: SecretStr) -> None:
        self._token = token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """Add Bearer token to request headers."""
        request.headers["Authorization"] = f"Bearer {self._token.get_secret_value()}"
        yield request


class LMv1Auth(httpx.Auth):
    """LMv1 signature authentication for LogicMonitor API."""

    def __init__(self, access_id: str, access_key: SecretStr) -> None:
        self._access_id = access_id
        self._access_key = access_key

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """Add LMv1 signature to request headers."""
        epoch = str(int(time.time() * 1000))

        resource_path = request.url.path
        if "/santaba/rest" in resource_path:
            resource_path = resource_path.split("/santaba/rest", 1)[1]

        body = ""
        if request.content:
            body = (
                request.content.decode("utf-8")
                if isinstance(request.content, bytes)
                else str(request.content)
            )

        request_vars = f"{request.method}{epoch}{body}{resource_path}"

        hmac_hash = hmac.new(
            self._access_key.get_secret_value().encode(),
            msg=request_vars.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        signature = base64.b64encode(hmac_hash.encode()).decode()

        auth_header = f"LMv1 {self._access_id}:{signature}:{epoch}"
        request.headers["Authorization"] = auth_header

        yield request


class LogicMonitorClient:
    """HTTP client for LogicMonitor REST API with retry support."""

    RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)

    def __init__(
        self,
        company: str,
        bearer_token: SecretStr | None = None,
        access_id: str | None = None,
        access_key: SecretStr | None = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        timeout: float = 30.0,
    ) -> None:
        """Initialize LogicMonitor API client.

        Args:
            company: LogicMonitor company/portal name.
            bearer_token: Bearer token for authentication.
            access_id: LMv1 access ID (used if bearer_token not provided).
            access_key: LMv1 access key (used if bearer_token not provided).
            max_retries: Maximum number of retry attempts.
            base_delay: Base delay between retries in seconds.
            max_delay: Maximum delay between retries in seconds.
            timeout: Request timeout in seconds.
        """
        self._base_url = f"https://{company}.logicmonitor.com/santaba/rest"
        self._company = company
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._timeout = timeout

        if bearer_token:
            self._auth: httpx.Auth = BearerAuth(bearer_token)
        elif access_id and access_key:
            self._auth = LMv1Auth(access_id, access_key)
        else:
            raise ValueError("Either bearer_token or (access_id and access_key) must be provided")

        self._client = httpx.Client(
            base_url=self._base_url,
            auth=self._auth,
            timeout=timeout,
            headers={"Content-Type": "application/json", "X-Version": "3"},
        )

    @property
    def company(self) -> str:
        """Get the company name."""
        return self._company

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic."""
        last_exception: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                )

                if response.status_code == 429:
                    if attempt < self._max_retries:
                        self._wait_with_backoff(attempt)
                        continue
                    try:
                        error_body = response.json() if response.content else {}
                    except json_module.JSONDecodeError:
                        error_body = {"errmsg": response.text[:500]}
                    raise RateLimitError(
                        "Rate limit exceeded",
                        status_code=429,
                        response=error_body,
                    )

                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    if attempt < self._max_retries:
                        self._wait_with_backoff(attempt)
                        continue

                if response.status_code >= 400:
                    try:
                        error_data = response.json() if response.content else {}
                    except json_module.JSONDecodeError:
                        error_data = {"errmsg": response.text[:500]}
                    error_msg = error_data.get("errorMessage", f"HTTP {response.status_code}")
                    raise LMAPIError(
                        error_msg, status_code=response.status_code, response=error_data
                    )

                if not response.content:
                    return {}

                try:
                    data = response.json()
                except json_module.JSONDecodeError as e:
                    raise LMAPIError(
                        f"Invalid JSON in response: {e}",
                        status_code=response.status_code,
                        response={"raw": response.text[:500]},
                    ) from e

                if isinstance(data, dict):
                    err_msg = data.get("errmsg") or data.get("errorMessage")
                    if err_msg:
                        raise LMAPIError(
                            str(err_msg),
                            status_code=response.status_code,
                            response=data,
                        )

                return data

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt < self._max_retries:
                    self._wait_with_backoff(attempt)
                    continue
                raise LMAPIError(f"Network error: {e}", status_code=0) from e

        if last_exception:
            raise LMAPIError(f"Request failed after {self._max_retries} retries", status_code=0)

        raise LMAPIError("Request failed: unexpected state after retry loop", status_code=0)

    def _wait_with_backoff(self, attempt: int) -> None:
        """Wait with exponential backoff."""
        delay = min(self._base_delay * (2**attempt), self._max_delay)
        time.sleep(delay)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make GET request."""
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make POST request."""
        return self._request("POST", path, json=json)

    def put(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make PUT request."""
        return self._request("PUT", path, json=json)

    def delete(self, path: str) -> dict[str, Any]:
        """Make DELETE request."""
        return self._request("DELETE", path)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "LogicMonitorClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
