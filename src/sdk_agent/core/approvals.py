from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ApprovalDecision:
    target: str
    required: int
    active: int

    @property
    def approved(self) -> bool:
        return self.active >= self.required


def evaluate_approval_gate(*, target: str, required: int, active: int) -> ApprovalDecision:
    return ApprovalDecision(target=target, required=max(1, required), active=max(0, active))
