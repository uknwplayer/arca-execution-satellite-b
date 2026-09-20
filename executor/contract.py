from __future__ import annotations

from dataclasses import dataclass, field


ALLOWED_PROFILES = frozenset({
    "smoke",
    "python-unit",
    "investigative-public-v0.1",
})

ALLOWED_INVESTIGATIVE_TASKS = frozenset({
    "PUBLIC_SOURCE_NORMALIZATION",
    "ABSTRACT_TRACE_EXTRACTION",
    "SOURCE_LOCATOR_VERIFICATION",
    "TYPOLOGY_MATCHING",
})


@dataclass(frozen=True)
class ExecutionRequest:
    profile: str
    request_id: str
    task_class: str | None = None
    task_input: dict = field(default_factory=dict)

    def validate(self) -> None:
        if self.profile not in ALLOWED_PROFILES:
            raise ValueError(f"unsupported profile: {self.profile}")
        if not self.request_id or len(self.request_id) > 128:
            raise ValueError("request_id must be 1..128 characters")
        if not all(ch.isalnum() or ch in "-_." for ch in self.request_id):
            raise ValueError("request_id contains invalid characters")
        if self.profile == "investigative-public-v0.1":
            if self.task_class not in ALLOWED_INVESTIGATIVE_TASKS:
                raise ValueError("investigative task class is not allowlisted")
            if not isinstance(self.task_input, dict):
                raise ValueError("task_input must be an object")
        elif self.task_class is not None or self.task_input:
            raise ValueError("task metadata is allowed only for investigative-public-v0.1")
