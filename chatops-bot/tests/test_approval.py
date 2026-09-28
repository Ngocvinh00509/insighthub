import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.approval import ApprovalError, ApprovalStore
from app.authorization import PermissionPolicy


POLICY = PermissionPolicy(
    read_users=frozenset(),
    diagnostic_users=frozenset(),
    mutation_users=frozenset({"U-requester"}),
    approver_users=frozenset({"U-approver"}),
)
ACTION = "kubernetes.scale_deployment"
ARGUMENTS = {"namespace": "insighthub-dev", "deployment": "api", "replicas": 3}


def approved_request(store: ApprovalStore):
    request = store.create(POLICY, "U-requester", ACTION, ARGUMENTS, expires_at=1100, now=1000)
    store.approve(POLICY, request.request_id, "U-approver", now=1001)
    return request


def test_valid_approval_binds_exact_request() -> None:
    store = ApprovalStore()
    request = approved_request(store)

    grant = store.consume(request.request_id, "U-requester", ACTION, ARGUMENTS, now=1002)

    assert grant.user_id == "U-requester"
    assert grant.action == ACTION


def test_expired_approval_is_rejected() -> None:
    store = ApprovalStore()
    request = store.create(POLICY, "U-requester", ACTION, ARGUMENTS, expires_at=1001, now=1000)

    with pytest.raises(ApprovalError, match="expired_approval"):
        store.approve(POLICY, request.request_id, "U-approver", now=1001)


def test_modified_arguments_are_rejected() -> None:
    store = ApprovalStore()
    request = approved_request(store)

    with pytest.raises(ApprovalError, match="approval_binding_mismatch"):
        store.consume(request.request_id, "U-requester", ACTION, {**ARGUMENTS, "replicas": 5}, now=1002)


def test_wrong_requesting_user_is_rejected() -> None:
    store = ApprovalStore()
    request = approved_request(store)

    with pytest.raises(ApprovalError, match="approval_binding_mismatch"):
        store.consume(request.request_id, "U-other", ACTION, ARGUMENTS, now=1002)


def test_approval_is_one_time_and_replay_is_rejected() -> None:
    store = ApprovalStore()
    request = approved_request(store)
    store.consume(request.request_id, "U-requester", ACTION, ARGUMENTS, now=1002)

    with pytest.raises(ApprovalError, match="replayed_approval"):
        store.consume(request.request_id, "U-requester", ACTION, ARGUMENTS, now=1003)


def test_unauthorized_approver_is_rejected() -> None:
    store = ApprovalStore()
    request = store.create(POLICY, "U-requester", ACTION, ARGUMENTS, expires_at=1100, now=1000)

    with pytest.raises(ApprovalError, match="unauthorized_approver"):
        store.approve(POLICY, request.request_id, "U-untrusted", now=1001)


def test_self_approval_is_rejected_by_policy() -> None:
    policy = PermissionPolicy(
        read_users=frozenset(),
        diagnostic_users=frozenset(),
        mutation_users=frozenset({"U-requester"}),
        approver_users=frozenset({"U-requester"}),
    )
    store = ApprovalStore()
    request = store.create(policy, "U-requester", ACTION, ARGUMENTS, expires_at=1100, now=1000)

    with pytest.raises(ApprovalError, match="self_approval_denied"):
        store.approve(policy, request.request_id, "U-requester", now=1001)
