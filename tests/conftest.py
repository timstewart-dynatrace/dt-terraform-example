"""Shared pytest fixtures."""

import os
import pytest

from pipelines.core.types import TenantConfig
from pipelines.core.dt_client import DynatraceClient


CLASSIC_TOKEN = "dt0c01.AAAAAAAAAAAAAAAAAAAAAAAA.BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
PLATFORM_TOKEN_S16 = "dt0s16.CCCCCCCCCCCCCCCCCCCCCCCC.DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD"
PLATFORM_TOKEN_S01 = "dt0s01.EEEEEEEEEEEEEEEEEEEEEEEE.FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
TENANT_URL = "https://abc12345.live.dynatrace.com"


@pytest.fixture
def classic_tenant() -> TenantConfig:
    """Tenant configured with a classic API Token only (back-compat path)."""
    return TenantConfig(url=TENANT_URL, token=CLASSIC_TOKEN)


@pytest.fixture
def platform_tenant_dt0s16() -> TenantConfig:
    """Tenant configured with a Platform Token only (dt0s16)."""
    return TenantConfig(url=TENANT_URL, token=PLATFORM_TOKEN_S16)


@pytest.fixture
def platform_tenant_dt0s01() -> TenantConfig:
    """Tenant configured with a Platform Token only (dt0s01)."""
    return TenantConfig(url=TENANT_URL, token=PLATFORM_TOKEN_S01)


@pytest.fixture
def combined_tenant() -> TenantConfig:
    """Tenant configured with Platform Token primary + classic API Token secondary."""
    return TenantConfig(
        url=TENANT_URL,
        token=PLATFORM_TOKEN_S16,
        api_token=CLASSIC_TOKEN,
    )


@pytest.fixture
def classic_client(classic_tenant) -> DynatraceClient:
    return DynatraceClient(classic_tenant)


@pytest.fixture
def platform_client(platform_tenant_dt0s16) -> DynatraceClient:
    return DynatraceClient(platform_tenant_dt0s16)


@pytest.fixture
def combined_client(combined_tenant) -> DynatraceClient:
    return DynatraceClient(combined_tenant)


@pytest.fixture(autouse=True)
def clean_tenant_env(monkeypatch):
    """Strip tenant env vars so tests are deterministic.

    Used as autouse so every test starts with a clean environment regardless
    of whether the developer happens to have SOURCE_TENANT_TOKEN set locally.
    """
    for var in (
        "SOURCE_TENANT_URL",
        "SOURCE_TENANT_TOKEN",
        "SOURCE_TENANT_API_TOKEN",
        "TARGET_TENANT_URL",
        "TARGET_TENANT_TOKEN",
        "TARGET_TENANT_API_TOKEN",
    ):
        monkeypatch.delenv(var, raising=False)
