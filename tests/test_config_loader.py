"""Tests for `PipelineConfig.get_source_tenant` / `get_target_tenant` — env + yaml loading."""

import pytest

from pipelines.core.config import PipelineConfig


class TestSourceTenantFromEnv:
    def test_url_and_token_from_env(self, monkeypatch):
        monkeypatch.setenv("SOURCE_TENANT_URL", "https://src.live.dynatrace.com")
        monkeypatch.setenv("SOURCE_TENANT_TOKEN", "dt0c01.AAA.BBB")
        cfg = PipelineConfig({})
        t = cfg.get_source_tenant()
        assert t.url == "https://src.live.dynatrace.com"
        assert t.token == "dt0c01.AAA.BBB"
        assert t.api_token is None

    def test_api_token_from_env(self, monkeypatch):
        monkeypatch.setenv("SOURCE_TENANT_URL", "https://src.live.dynatrace.com")
        monkeypatch.setenv("SOURCE_TENANT_TOKEN", "dt0s16.CCC.DDD")
        monkeypatch.setenv("SOURCE_TENANT_API_TOKEN", "dt0c01.EEE.FFF")
        cfg = PipelineConfig({})
        t = cfg.get_source_tenant()
        assert t.token == "dt0s16.CCC.DDD"
        assert t.api_token == "dt0c01.EEE.FFF"

    def test_no_env_returns_empty_strings_and_none(self):
        """conftest's clean_tenant_env fixture (autouse) strips all tenant env vars."""
        cfg = PipelineConfig({})
        t = cfg.get_source_tenant()
        assert t.url == ""
        assert t.token == ""
        assert t.api_token is None


class TestSourceTenantFromYaml:
    def test_yaml_overrides_env(self, monkeypatch):
        monkeypatch.setenv("SOURCE_TENANT_URL", "https://from-env.live.dynatrace.com")
        monkeypatch.setenv("SOURCE_TENANT_TOKEN", "dt0c01.ENV.TOKEN")
        cfg = PipelineConfig({
            "export": {
                "source_tenant_url": "https://from-yaml.live.dynatrace.com",
                "source_tenant_token": "dt0s16.YAML.TOKEN",
                "source_tenant_api_token": "dt0c01.YAML.API",
            }
        })
        t = cfg.get_source_tenant()
        assert t.url == "https://from-yaml.live.dynatrace.com"
        assert t.token == "dt0s16.YAML.TOKEN"
        assert t.api_token == "dt0c01.YAML.API"

    def test_yaml_api_token_alone(self):
        """YAML can set api_token even without url/token; falls through to empty strings."""
        cfg = PipelineConfig({
            "export": {
                "source_tenant_api_token": "dt0c01.ONLY.API",
            }
        })
        t = cfg.get_source_tenant()
        assert t.api_token == "dt0c01.ONLY.API"
        assert t.url == ""
        assert t.token == ""


class TestTargetTenant:
    """Mirror coverage for the target side — same logic, different env vars."""

    def test_target_url_and_token_from_env(self, monkeypatch):
        monkeypatch.setenv("TARGET_TENANT_URL", "https://tgt.live.dynatrace.com")
        monkeypatch.setenv("TARGET_TENANT_TOKEN", "dt0s16.TGT.TOKEN")
        cfg = PipelineConfig({})
        t = cfg.get_target_tenant()
        assert t.url == "https://tgt.live.dynatrace.com"
        assert t.token == "dt0s16.TGT.TOKEN"
        assert t.api_token is None

    def test_target_api_token_from_env(self, monkeypatch):
        monkeypatch.setenv("TARGET_TENANT_URL", "https://tgt.live.dynatrace.com")
        monkeypatch.setenv("TARGET_TENANT_TOKEN", "dt0s16.TGT.TOKEN")
        monkeypatch.setenv("TARGET_TENANT_API_TOKEN", "dt0c01.TGT.API")
        cfg = PipelineConfig({})
        t = cfg.get_target_tenant()
        assert t.api_token == "dt0c01.TGT.API"

    def test_target_yaml_overrides_env(self, monkeypatch):
        monkeypatch.setenv("TARGET_TENANT_TOKEN", "dt0c01.ENV.TGT")
        cfg = PipelineConfig({
            "deploy": {
                "target_tenant_url": "https://yaml-tgt.live.dynatrace.com",
                "target_tenant_token": "dt0s16.YAML.TGT",
            }
        })
        t = cfg.get_target_tenant()
        assert t.url == "https://yaml-tgt.live.dynatrace.com"
        assert t.token == "dt0s16.YAML.TGT"


class TestEmptyStringApiTokenFallsBackToNone:
    """An empty `*_API_TOKEN` env var should be treated as unset (None),
    not as an empty string — that prevents accidentally passing '' as a token."""

    def test_empty_env_var_becomes_none(self, monkeypatch):
        monkeypatch.setenv("SOURCE_TENANT_URL", "u")
        monkeypatch.setenv("SOURCE_TENANT_TOKEN", "t")
        monkeypatch.setenv("SOURCE_TENANT_API_TOKEN", "")
        cfg = PipelineConfig({})
        t = cfg.get_source_tenant()
        assert t.api_token is None
