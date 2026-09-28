"""One-time, identity-bound approvals for allowlisted mutation actions."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from threading import Lock
from typing import Any

from .authorization import ApprovalGrant, PermissionDenied, PermissionPolicy, arguments_hash, authorize_action
from .audit import log_approval_event


class ApprovalError(PermissionDenied):
    """Approval does not exist, is invalid, expired, or cannot be consumed."""


@dataclass(frozen=True)
class PendingApproval:
    request_id: str
    requester_user_id: str
    action: str
    arguments_hash: str
    expires_at: float
    approver_user_id: str | None = None
    consumed: bool = False


class ApprovalStore:
    """Atomic local state machine; replace with a shared Redis store for replicas."""

    def __init__(self) -> None:
        self._records: dict[str, PendingApproval] = {}
        self._lock = Lock()

    def create(
        self,
        policy: PermissionPolicy,
        requester_user_id: str,
        action: str,
        arguments: dict[str, Any],
        *,
        expires_at: float,
        now: float | None = None,
    ) -> PendingApproval:
        current_time = time.time() if now is None else now
        if expires_at <= current_time:
            raise ApprovalError("invalid_approval_expiry")
        # This verifies the requester holds the mutation role. It deliberately
        # returns approval_required because no grant exists at creation time.
        try:
            authorize_action(policy, requester_user_id, action, arguments, now=current_time)
        except PermissionDenied as exc:
            if exc.args != ("approval_required",):
                raise ApprovalError("mutation_not_permitted") from exc
        record = PendingApproval(
            request_id=uuid.uuid4().hex,
            requester_user_id=requester_user_id,
            action=action,
            arguments_hash=arguments_hash(arguments),
            expires_at=expires_at,
        )
        with self._lock:
            self._records[record.request_id] = record
        log_approval_event(record.request_id, action, requester_user_id, "approval_required")
        return record

    def approve(
        self,
        policy: PermissionPolicy,
        request_id: str,
        approver_user_id: str,
        *,
        now: float | None = None,
    ) -> PendingApproval:
        current_time = time.time() if now is None else now
        with self._lock:
            record = self._get_pending(request_id, current_time)
            if approver_user_id not in policy.approver_users:
                raise ApprovalError("unauthorized_approver")
            if not policy.allow_self_approval and approver_user_id == record.requester_user_id:
                raise ApprovalError("self_approval_denied")
            record = PendingApproval(
                **{**record.__dict__, "approver_user_id": approver_user_id}
            )
            self._records[request_id] = record
        log_approval_event(
            request_id,
            record.action,
            record.requester_user_id,
            "approved",
            approver_user_id,
        )
        return record

    def consume(
        self,
        request_id: str,
        requester_user_id: str,
        action: str,
        arguments: dict[str, Any],
        *,
        now: float | None = None,
    ) -> ApprovalGrant:
        current_time = time.time() if now is None else now
        with self._lock:
            record = self._get_pending(request_id, current_time, allow_approved=True)
            if record.approver_user_id is None:
                raise ApprovalError("approval_not_granted")
            if (
                record.requester_user_id != requester_user_id
                or record.action != action
                or record.arguments_hash != arguments_hash(arguments)
            ):
                raise ApprovalError("approval_binding_mismatch")
            self._records[request_id] = PendingApproval(**{**record.__dict__, "consumed": True})
        log_approval_event(
            request_id,
            action,
            requester_user_id,
            "allowed",
            record.approver_user_id,
        )
        return ApprovalGrant(requester_user_id, action, record.arguments_hash, record.expires_at)

    def _get_pending(self, request_id: str, now: float, *, allow_approved: bool = False) -> PendingApproval:
        record = self._records.get(request_id)
        if record is None:
            raise ApprovalError("unknown_approval")
        if record.expires_at <= now:
            raise ApprovalError("expired_approval")
        if record.consumed:
            raise ApprovalError("replayed_approval")
        if record.approver_user_id is not None and not allow_approved:
            raise ApprovalError("approval_already_granted")
        return record
