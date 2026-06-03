"""Spine fitness function (evolutionary architecture).

The core architectural invariant: the transports (backend/mcp, backend/api) are THIN
wrappers — they never reach the database directly. All SQL and session handling lives
in backend/services. This test makes that invariant executable: it parses every module
under the transport packages and fails if any imports sqlalchemy or references a query
call (.execute/.scalar/.scalars) or a `session`.

Parsing the source (not importing it) means docstrings that merely mention "session"
do not trip the check — only real code references do.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TRANSPORT_DIRS = [_REPO_ROOT / "backend" / "mcp", _REPO_ROOT / "backend" / "api"]
_QUERY_METHODS = {"execute", "scalar", "scalars"}


def _transport_modules() -> list[Path]:
    modules: list[Path] = []
    for directory in _TRANSPORT_DIRS:
        modules.extend(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts)
    return modules


def _violations(module: Path) -> list[str]:
    tree = ast.parse(module.read_text(encoding="utf-8"))
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "sqlalchemy":
            bad.append(f"imports sqlalchemy ({node.module})")
        elif isinstance(node, ast.Import):
            bad += [
                f"imports sqlalchemy ({a.name})"
                for a in node.names
                if a.name.split(".")[0] == "sqlalchemy"
            ]
        elif isinstance(node, ast.Attribute) and node.attr in _QUERY_METHODS:
            bad.append(f"calls .{node.attr}()")
        elif isinstance(node, ast.Name) and node.id == "session":
            bad.append("references `session`")
    return bad


def test_fitness_function_actually_covers_the_transports() -> None:
    # Guard against a vacuous pass if discovery breaks: the known transports must be seen.
    names = {p.name for p in _transport_modules()}
    assert "server.py" in names
    assert "app.py" in names


@pytest.mark.parametrize(
    "module", _transport_modules(), ids=lambda p: str(p.relative_to(_REPO_ROOT))
)
def test_transport_module_is_db_free(module: Path) -> None:
    bad = _violations(module)
    assert not bad, (
        f"{module.relative_to(_REPO_ROOT)} breaks the spine "
        f"(transports must be DB-free; all DB access lives in backend/services): {bad}"
    )
