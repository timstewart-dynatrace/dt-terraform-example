"""Tests for `TenantConfig` — the tenant connection settings dataclass."""

import pytest

from pipelines.core.types import TenantConfig


class TestTenantConfigConstruction:
    def test_minimal_fields(self):
        """url + token are the only required fields."""
        t = TenantConfig(url="https://x.live.dynatrace.com", token="dt0c01.x.y")
        assert t.url == "https://x.live.dynatrace.com"
        assert t.token == "dt0c01.x.y"
        assert t.api_token is None

    def test_api_token_defaults_to_none(self):
        """Back-compat: existing call sites that don't pass api_token get None."""
        t = TenantConfig(url="x", token="y")
        assert t.api_token is None

    def test_all_three_fields(self):
        """Combined-auth construction."""
        t = TenantConfig(
            url="https://x.live.dynatrace.com",
            token="dt0s16.x.y",
            api_token="dt0c01.x.y",
        )
        assert t.token == "dt0s16.x.y"
        assert t.api_token == "dt0c01.x.y"

    def test_api_token_keyword_only(self):
        """`api_token` should be settable as a keyword argument."""
        t = TenantConfig(url="u", token="t", api_token="a")
        assert t.api_token == "a"
