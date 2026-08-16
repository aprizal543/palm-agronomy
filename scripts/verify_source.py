"""Dependency-free checks that can run before the virtual environment is installed."""

import ast
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

    forbidden = ("SUPABASE_SERVICE_ROLE_KEY=", "TELEGRAM_BOT_TOKEN=")
    for path in ROOT.rglob("*"):
        if (
            path.is_file()
            and path != Path(__file__)
            and ".git" not in path.parts
            and "__pycache__" not in path.parts
        ):
            content = path.read_text(encoding="utf-8", errors="ignore")
            assert not any(secret in content for secret in forbidden), f"Secret ditemukan: {path}"

    print(f"Source verification passed: {len(python_files)} Python files, 3 migrations.")


if __name__ == "__main__":
    main()
