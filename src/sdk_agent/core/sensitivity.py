from __future__ import annotations

from sdk_agent.models import SensitiveChangeReport


SENSITIVE_PATH_RULES: dict[str, str] = {
    "auth": "authentication",
    "billing": "billing",
    "payment": "billing",
    "deploy": "deployment",
    "infra": "infrastructure",
    "migration": "database",
    "secrets": "secrets",
    ".github/workflows": "cicd",
    "security": "security",
}


def classify_sensitive_changes(files: list[str]) -> SensitiveChangeReport:
    sensitive: list[str] = []
    categories: set[str] = set()

    for file_path in files:
        lowered = file_path.lower()
        for token, category in SENSITIVE_PATH_RULES.items():
            if token in lowered:
                sensitive.append(file_path)
                categories.add(category)
                break

    return SensitiveChangeReport(
        files=files,
        sensitive_files=sensitive,
        categories=sorted(categories),
        requires_security_review=bool(sensitive),
    )
