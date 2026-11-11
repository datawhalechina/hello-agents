"""Back up or restore the Compose PostgreSQL database."""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = PROJECT_ROOT / "deploy" / "docker-compose.yml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup", help="Create a compressed pg_dump archive")
    backup.add_argument("--output", type=Path)

    restore = subparsers.add_parser("restore", help="Restore a pg_dump archive")
    restore.add_argument("archive", type=Path)
    restore.add_argument(
        "--confirm-restore",
        action="store_true",
        help="Required because restore replaces existing database objects.",
    )
    return parser.parse_args()


def compose_command(*args: str) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), *args]


def backup(output: Path | None) -> int:
    if output is None:
        stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
        output = PROJECT_ROOT / "backups" / f"pubmed-agent-{stamp}.dump"
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    command = compose_command(
        "exec",
        "-T",
        "postgres",
        "sh",
        "-c",
        'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc',
    )
    with output.open("wb") as destination:
        result = subprocess.run(command, cwd=PROJECT_ROOT, stdout=destination)
    if result.returncode != 0:
        output.unlink(missing_ok=True)
        return result.returncode
    print(f"Backup created: {output}")
    return 0


def restore(archive: Path, confirmed: bool) -> int:
    if not confirmed:
        print("Restore refused: pass --confirm-restore to acknowledge replacement.")
        return 2
    archive = archive.expanduser().resolve()
    if not archive.is_file():
        print(f"Archive not found: {archive}")
        return 2
    command = compose_command(
        "exec",
        "-T",
        "postgres",
        "sh",
        "-c",
        'exec pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
        "--clean --if-exists --no-owner --exit-on-error",
    )
    with archive.open("rb") as source:
        result = subprocess.run(command, cwd=PROJECT_ROOT, stdin=source)
    if result.returncode == 0:
        print(f"Restore completed: {archive}")
    return result.returncode


def main() -> int:
    args = parse_args()
    if args.command == "backup":
        return backup(args.output)
    return restore(args.archive, args.confirm_restore)


if __name__ == "__main__":
    sys.exit(main())
