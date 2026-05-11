"""Tests for `_header_for_token` — Authorization header format by token prefix."""

import pytest

from pipelines.core.dt_client import _header_for_token


class TestHeaderForToken:
    """Token-prefix → Authorization header format mapping.

    Source-of-truth for the mapping:
    https://docs.dynatrace.com/docs/manage/identity-access-management/access-tokens-and-oauth-clients/platform-tokens
    """

    @pytest.mark.parametrize(
        "token",
        [
            "dt0s16.AAAA.BBBB",
            "dt0s16.IIIIIIIIIIIIIIIIIIIIIIII.JJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJJ",
        ],
    )
    def test_dt0s16_uses_bearer(self, token):
        assert _header_for_token(token) == f"Bearer {token}"

    @pytest.mark.parametrize(
        "token",
        [
            "dt0s01.CCCC.DDDD",
            "dt0s01.KKKKKKKKKKKKKKKKKKKKKKKK.LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL",
        ],
    )
    def test_dt0s01_uses_bearer(self, token):
        assert _header_for_token(token) == f"Bearer {token}"

    @pytest.mark.parametrize(
        "token",
        [
            "dt0c01.EEEE.FFFF",
            "dt0c01.MMMMMMMMMMMMMMMMMMMMMMMM.NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN",
        ],
    )
    def test_dt0c01_uses_api_token(self, token):
        assert _header_for_token(token) == f"Api-Token {token}"

    @pytest.mark.parametrize(
        "token",
        [
            "unknown.GGGG.HHHH",
            "dt0s99.QQQQ.RRRR",  # hypothetical future prefix we don't know about
            "",
        ],
    )
    def test_unknown_prefix_falls_back_to_api_token(self, token):
        """Unknown prefix uses Api-Token as a safe default.

        Rationale: classic Api-Token format has been around longest; a token
        of unknown shape is more likely to be a classic-style than a
        Bearer-style. Treating it as classic surfaces 401s clearly rather
        than masking them as malformed Bearer.
        """
        assert _header_for_token(token) == f"Api-Token {token}"

    def test_partial_prefix_match_does_not_count_as_platform(self):
        """A token whose prefix happens to *start* with `dt0s1` but lacks the dot
        should not be treated as a Platform Token. The check is prefix-with-dot."""
        # `dt0s160` is 5 chars matching `dt0s16` but no dot — must not match
        assert _header_for_token("dt0s160abc.XXX.YYY").startswith("Api-Token ")
