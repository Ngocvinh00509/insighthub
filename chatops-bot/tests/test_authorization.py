import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.authorization import (
    ApprovalGrant,
    ApprovalRequired,
    PermissionDenied,
    PermissionPolicy,
    PermissionTier,
    UnknownAction,
    arguments_hash,
    authorize_action,
)


POLICY = PermissionPolicy(
    read_users=frozenset({"U-read"}),
    diagnostic_users=frozenset({"U-diagnostic"}),
    mutation_users=frozenset({"U-mutation"}),
)


def test_allowed_read() -> None:
    assert authorize_action(POLICY, "U-read", "intent.health") is PermissionTier.READ


def test_denied_read_defaults_to_deny() -> None:
    with pytest.raises(PermissionDenied, match="permission_denied"):
        authorize_action(POLICY, "U-unknown", "intent.health")


def test_allowed_diagnostic() -> None:
    assert authorize_action(POLICY, "U-diagnostic", "kubernetes.get_events") is PermissionTier.DIAGNOSTIC


def test_denied_diagnostic_for_read_only_user() -> None:
    with pytest.raises(PermissionDenied, match="permission_denied"):
        authorize_action(POLICY, "U-read", "kubernetes.get_events")


def test_mutation_without_approval_is_not_executed() -> None:
    with pytest.raises(ApprovalRequired, match="approval_required"):
        authorize_action(POLICY, "U-mutation", "kubernetes.scale_deployment", {"replicas": 3})


def test_approved_mutation_must_match_user_action_arguments_and_expiry() -> None:
    arguments = {"replicas": 3}
    grant = ApprovalGrant("U-mutation", "kubernetes.scale_deployment", arguments_hash(arguments), 1001)
    assert authorize_action(
        POLICY,
        "U-mutation",
        "kubernetes.scale_deployment",
        arguments,
        grant,
        now=1000,
    ) is PermissionTier.MUTATION


def test_unknown_action_is_denied() -> None:
    with pytest.raises(UnknownAction, match="unknown_action"):
        authorize_action(POLICY, "U-read", "shell.run")
