"""Dependency-free checks that can run before the virtual environment is installed."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def main() -> None:
    python_files = [
        path
        for folder in ("app", "migrations", "scripts", "tests")
        for path in (ROOT / folder).rglob("*.py")
    ]
    for path in python_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    revisions = sorted(path.name for path in (ROOT / "migrations/versions").glob("*.py"))
    assert revisions == [
        "0001_extensions_enums.py",
        "0002_users_farms.py",
        "0003_blocks_spatial.py",
        "0004_telegram_agent.py",
    ]

    spatial = (ROOT / "migrations/versions/0003_blocks_spatial.py").read_text(encoding="utf-8")
    for contract in (
        "st_area(new.boundary::extensions.geography)",
        "st_coveredby",
        "st_intersection",
        "st_covers",
        "st_dwithin",
        "resolve_blocks_by_location",
        "pg_advisory_xact_lock",
        ">1.0",
    ):
        assert contract in spatial.lower(), f"Kontrak GIS hilang: {contract}"

    secret_patterns = (
        re.compile(r"SUPABASE_SERVICE_ROLE_KEY\s*=\s*[^\s<]+"),
        re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    )
    for path in ROOT.rglob("*"):
        if (
            path.is_file()
            and path != Path(__file__)
            and not path.name.startswith(".env")
            and not {
                ".git",
                "__pycache__",
                "palm_agronomy",
                ".venv",
                ".pytest_cache",
                ".ruff_cache",
            }.intersection(path.parts)
        ):
            content = path.read_text(encoding="utf-8", errors="ignore")
            assert not any(pattern.search(content) for pattern in secret_patterns), (
                f"Secret ditemukan: {path}"
            )

    print(f"Source verification passed: {len(python_files)} Python files, 4 migrations.")


if __name__ == "__main__":
    main()
