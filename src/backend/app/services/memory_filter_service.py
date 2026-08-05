"""Typed eligibility and privacy filter applied before candidate persistence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

_MAX_TEXT_CHARS = 1000
_MAX_PAYLOAD_BYTES = 16_384
_ABSOLUTE_PATH_RE = re.compile(
    r"(?:\b[A-Za-z]:[\\/][^\s,;]+|/(?:home|Users|var|tmp|data|mnt|media)/[^\s,;]+)"
)
_SECRET_RE = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|authorization|private[_-]?key)\s*[:=]\s*[^\s,;]+"
)
_SUBJECT_RE = re.compile(
    r"(?i)(?:\bsub-[a-z0-9]{2,}\b|\b(?:subject|patient)[-_ ]\d{2,}\b)"
)
_INSTRUCTION_RE = re.compile(
    r"(?i)(ignore (?:all )?(?:previous|prior) instructions|system prompt|developer message|"
    r"bypass (?:approval|safety|gate)|execute (?:this )?(?:command|code)|you are chatgpt)"
)
_PHI_KEYS = {
    "patientname",
    "patientid",
    "patientbirthdate",
    "birthdate",
    "accessionnumber",
    "institutionname",
    "medicalrecordnumber",
    "mrn",
    "phi",
    "raw_patient_data",
}
_SECRET_KEYS = {
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "authorization",
    "cookie",
    "private_key",
}


@dataclass(frozen=True)
class MemoryFilterResult:
    ok: bool
    cleaned: dict[str, Any] | None
    rejection_code: str | None = None
    flags: tuple[str, ...] = ()


class MemoryFilterService:
    """Reject disallowed data; never stores first and redacts later."""

    allowed_source_types = frozenset(
        {"agent_lifecycle_event", "observation", "goal_evaluation", "run_summary"}
    )

    def filter_source(
        self,
        *,
        source_type: str,
        source_trust_class: str,
        projection: dict[str, Any],
    ) -> MemoryFilterResult:
        if source_type not in self.allowed_source_types:
            return MemoryFilterResult(False, None, "MEMORY_SOURCE_NOT_ALLOWED")
        if source_trust_class == "external_untrusted":
            return MemoryFilterResult(False, None, "MEMORY_SOURCE_UNTRUSTED")
        return self._validate(projection)

    def filter_explicit(
        self, *, value: dict[str, Any], summary: str
    ) -> MemoryFilterResult:
        return self._validate({"value": value, "summary": summary})

    def _validate(self, value: dict[str, Any]) -> MemoryFilterResult:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if len(encoded.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
            return MemoryFilterResult(False, None, "MEMORY_PAYLOAD_TOO_LARGE")
        flags: list[str] = []
        code = self._scan(value, flags=flags)
        if code:
            return MemoryFilterResult(False, None, code, tuple(dict.fromkeys(flags)))
        return MemoryFilterResult(True, value, flags=tuple(dict.fromkeys(flags)))

    def _scan(self, value: Any, *, flags: list[str], key: str | None = None) -> str | None:
        if key is not None:
            normalized = key.replace("-", "_").casefold()
            compact = normalized.replace("_", "")
            if normalized in _SECRET_KEYS or compact in _SECRET_KEYS:
                flags.append("secret_key")
                return "MEMORY_SECRET_REJECTED"
            if compact in _PHI_KEYS or normalized in _PHI_KEYS:
                flags.append("phi_key")
                return "MEMORY_PHI_REJECTED"
        if isinstance(value, dict):
            for child_key, child in value.items():
                code = self._scan(child, flags=flags, key=str(child_key))
                if code:
                    return code
            return None
        if isinstance(value, (list, tuple)):
            for child in value:
                code = self._scan(child, flags=flags, key=key)
                if code:
                    return code
            return None
        if not isinstance(value, str):
            return None
        if len(value) > _MAX_TEXT_CHARS:
            flags.append("oversize_text")
            return "MEMORY_TEXT_TOO_LARGE"
        if _SECRET_RE.search(value):
            flags.append("secret_value")
            return "MEMORY_SECRET_REJECTED"
        if _ABSOLUTE_PATH_RE.search(value):
            flags.append("absolute_path")
            return "MEMORY_ABSOLUTE_PATH_REJECTED"
        if _SUBJECT_RE.search(value):
            flags.append("subject_identifier")
            return "MEMORY_SUBJECT_ID_REJECTED"
        if _INSTRUCTION_RE.search(value):
            flags.append("instruction_like")
            return "MEMORY_INSTRUCTION_REJECTED"
        return None
