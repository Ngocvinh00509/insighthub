"""Deterministic, default-deny authorization for ChatOps actions."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class PermissionTier(StrEnum):
    READ = "read"
    DIAGNOSTIC = "diagnostic"
    MUTATION = "mutation"


ACTION_TIERS: dict[str, PermissionTier] = {
    "intent.health": PermissionTier.READ,
    "intent.ingestion": PermissionTier.READ,
    "intent.pods": PermissionTier.READ,
    "prometheus.health": PermissionTier.READ,
    "prometheus.metrics": PermissionTier.READ,
    "kubernetes.list_pods": PermissionTier.READ,
    "kubernetes.get_events": PermissionTier.DIAGNOSTIC,
    "kubernetes.get_pod_logs": PermissionTier.DIAGNOSTIC,
    "kubernetes.describe_pod": PermissionTier.DIAGNOSTIC,
    "kubernetes.scale_deployment": PermissionTier.MUTATION,
    "kubernetes.restart_pod": PermissionTier.MUTATION,
    "kubernetes.delete_resource": PermissionTier.MUTATION,
}
INTENT_ACTIONS = {"health": "intent.health", "ingestion": "intent.ingestion", "pods": "intent.pods"}


class PermissionDenied(RuntimeError):
    """The authenticated Slack user is not allowed to perform an action."""


class ApprovalRequired(PermissionDenied):
    """A permitted mutation needs a separately validated approval grant."""


class UnknownAction(PermissionDenied):
    """Action is absent from the server-side capability registry."""


@dataclass(frozen=True)
class PermissionPolicy:
    read_users: frozenset[str]
    diagnostic_users: frozenset[str]
    mutation_users: frozenset[str]
    approver_users: frozenset[str] = frozenset()
    allow_self_approval: bool = False


@dataclass(frozen=True)
class ApprovalGrant:
    """Validated server-side approval bound to identity, action and arguments."""

    user_id: str
    action: str
    arguments_hash: str
    expires_at: float


def arguments_hash(arguments: dict[str, Any]) -> str:
    encoded = json.dumps(arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def required_tier(action: str) -> PermissionTier:
    try:
        return ACTION_TIERS[action]
    except KeyError as exc:
        raise UnknownAction("unknown_action") from exc


def authorize_action(
    policy: PermissionPolicy,
    user_id: str,
    action: str,
    arguments: dict[str, Any] | None = None,
    approval: ApprovalGrant | None = None,
    *,
    now: float | None = None,
) -> PermissionTier:
    """Enforce role membership and approval without relying on model output."""
    if not user_id:
        raise PermissionDenied("identity_required")
    tier = required_tier(action)
    if tier is PermissionTier.READ:
        allowed = policy.read_users | policy.diagnostic_users | policy.mutation_users
    elif tier is PermissionTier.DIAGNOSTIC:
        allowed = policy.diagnostic_users | policy.mutation_users
    else:
        allowed = policy.mutation_users
    if user_id not in allowed:
        raise PermissionDenied("permission_denied")
    if tier is PermissionTier.MUTATION:
        current_time = time.time() if now is None else now
        if (
            approval is None
            or approval.user_id != user_id
            or approval.action != action
            or approval.arguments_hash != arguments_hash(arguments or {})
            or approval.expires_at <= current_time
        ):
            raise ApprovalRequired("approval_required")
    return tier


def authorize_intent(policy: PermissionPolicy, user_id: str, intent: str | None) -> PermissionTier:
    if intent is None:
        raise UnknownAction("unknown_action")
    try:
        return authorize_action(policy, user_id, INTENT_ACTIONS[intent])
    except KeyError as exc:
        raise UnknownAction("unknown_action") from exc
