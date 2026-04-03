"""Tests for LogicMonitor API client."""

import pytest
from pydantic import SecretStr

from lm_cloud_sync.core.exceptions import LMAPIError, RateLimitError
from lm_cloud_sync.core.lm_client import BearerAuth, LMv1Auth, LogicMonitorClient


class TestBearerAuth:
    """Tests for BearerAuth class."""

    def test_auth_adds_bearer_header(self) -> None:
        """Test that Bearer token is added to request headers."""
        import httpx

        auth = BearerAuth(SecretStr("test-token"))
        request = httpx.Request("GET", "https://example.com/api")

        # Get the generator
        flow = auth.auth_flow(request)
        modified_request = next(flow)

        assert "Authorization" in modified_request.headers
        assert modified_request.headers["Authorization"] == "Bearer test-token"


class TestLMv1Auth:
    """Tests for LMv1Auth class."""

    def test_auth_adds_lmv1_header(self) -> None:
        """Test that LMv1 signature is added to request headers."""
        import httpx

        auth = LMv1Auth("access-id", SecretStr("access-key"))
        request = httpx.Request("GET", "https://company.logicmonitor.com/santaba/rest/device/groups")

        flow = auth.auth_flow(request)
        modified_request = next(flow)

        assert "Authorization" in modified_request.headers
        auth_header = modified_request.headers["Authorization"]
        assert auth_header.startswith("LMv1 access-id:")


class TestLogicMonitorClient:
    """Tests for LogicMonitorClient class."""

    def test_init_with_bearer_token(self) -> None:
        """Test client initialization with bearer token."""
        client = LogicMonitorClient(
            company="test-company",
            bearer_token=SecretStr("test-token"),
        )
        assert client.company == "test-company"
        client.close()

    def test_init_with_lmv1(self) -> None:
        """Test client initialization with LMv1 credentials."""
        client = LogicMonitorClient(
            company="test-company",
            access_id="test-id",
            access_key=SecretStr("test-key"),
        )
        assert client.company == "test-company"
        client.close()

    def test_init_without_credentials_raises_error(self) -> None:
        """Test that initialization without credentials raises error."""
        with pytest.raises(ValueError, match="Either bearer_token or"):
            LogicMonitorClient(company="test-company")

    def test_context_manager(self) -> None:
        """Test client as context manager."""
        with LogicMonitorClient(
            company="test-company",
            bearer_token=SecretStr("test-token"),
        ) as client:
            assert client.company == "test-company"


class TestLogicMonitorClientWithMocks:
    """Tests for LogicMonitorClient with mocked HTTP responses."""

    def test_get_request(self, httpx_mock) -> None:
        """Test GET request."""
        httpx_mock.add_response(
            url="https://test-company.logicmonitor.com/santaba/rest/device/groups",
            json={"items": [], "total": 0},
        )

        with LogicMonitorClient(
            company="test-company",
            bearer_token=SecretStr("test-token"),
        ) as client:
            result = client.get("device/groups")

        assert result == {"items": [], "total": 0}

    def test_post_request(self, httpx_mock) -> None:
        """Test POST request."""
        httpx_mock.add_response(
            url="https://test-company.logicmonitor.com/santaba/rest/device/groups",
            method="POST",
            json={"id": 123, "name": "Test Group"},
        )

        with LogicMonitorClient(
            company="test-company",
            bearer_token=SecretStr("test-token"),
        ) as client:
            result = client.post("device/groups", json={"name": "Test Group"})

        assert result["id"] == 123

    def test_api_error_response(self, httpx_mock) -> None:
        """Test handling of API error response."""
        httpx_mock.add_response(
            url="https://test-company.logicmonitor.com/santaba/rest/device/groups",
            status_code=400,
            json={"errorMessage": "Bad request"},
        )

        with LogicMonitorClient(
            company="test-company",
            bearer_token=SecretStr("test-token"),
        ) as client, pytest.raises(LMAPIError) as exc_info:
            client.get("device/groups")

        assert exc_info.value.status_code == 400
        assert "Bad request" in str(exc_info.value)

    def test_rate_limit_error(self, httpx_mock) -> None:
        """Test handling of rate limit error."""
        # Add multiple 429 responses (client will retry)
        for _ in range(4):
            httpx_mock.add_response(
                url="https://test-company.logicmonitor.com/santaba/rest/device/groups",
                status_code=429,
                json={"errorMessage": "Rate limit exceeded"},
            )

        with LogicMonitorClient(
            company="test-company",
            bearer_token=SecretStr("test-token"),
            max_retries=3,
            base_delay=0.01,  # Fast retries for testing
        ) as client:
            with pytest.raises(RateLimitError):
                client.get("device/groups")
