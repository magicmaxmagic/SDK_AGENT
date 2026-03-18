from __future__ import annotations

from pathlib import Path

from sdk_agent.context import ProjectContext
from sdk_agent.guardrails import ensure_path_within


def safe_list_files(context: ProjectContext, pattern: str = "**/*") -> list[str]:
    root = context.repo_path.resolve()
    files = []
    for path in root.glob(pattern):
        if path.is_file():
            safe_path = ensure_path_within(root, path)
            files.append(str(safe_path.relative_to(root)))
    return sorted(files)


def safe_read_file(context: ProjectContext, relative_path: str, max_chars: int = 50_000) -> str:
    root = context.repo_path.resolve()
    target = ensure_path_within(root, root / relative_path)
    content = target.read_text(encoding="utf-8")
    return content[:max_chars]


def load_project_rules(context: ProjectContext) -> list[str]:
    return list(context.project_rules)
