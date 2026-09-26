"""Day 3 contract tests for the baseline IaC security policy.

These tests deliberately use resource-shaped inputs only: no provider calls,
credentials, state files, or cloud account are needed to exercise the policy.
"""

from __future__ import annotations


REQUIRED_TAGS = {"managed-by", "environment", "project"}


def policy_allows(resource: dict[str, object]) -> bool:
    """Accept only private, encrypted resources with ownership metadata.

    This is the contract enforced by the Day 3 Terraform/policy pipeline for
    stateful AWS resources.  The production policy may add stricter checks,
    but it must not weaken these baseline controls.
    """
    tags = resource.get("tags")
    return (
        resource.get("public") is False
        and resource.get("encrypted") is True
        and resource.get("uses_literal_secret") is False
        and isinstance(tags, dict)
        and REQUIRED_TAGS <= set(tags)
        and all(isinstance(tags[name], str) and tags[name].strip() for name in REQUIRED_TAGS)
    )


def test_policy_allows_valid() -> None:
    resource = {
        "public": False,
        "encrypted": True,
        "uses_literal_secret": False,
        "tags": {
            "managed-by": "terraform",
            "environment": "staging",
            "project": "insighthub",
        },
    }

    assert policy_allows(resource) is True


def test_policy_denies_unsafe() -> None:
    unsafe_resource = {
        "public": True,
        "encrypted": False,
        "uses_literal_secret": True,
        "tags": {"project": "insighthub"},
    }

    assert policy_allows(unsafe_resource) is False
