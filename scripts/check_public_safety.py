"""Fail when a public portfolio folder contains common sensitive artifacts."""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".toml",
    ".txt",
    ".json",
    ".sql",
    ".yml",
    ".yaml",
}
FORBIDDEN_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".csv",
    ".html",
    ".htm",
    ".parquet",
    ".pem",
    ".key",
}
SKIPPED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
}
FORBIDDEN_DIRECTORY_NAMES = {
    "data",
    "raw",
    "downloads",
    "logs",
    "browser-profile",
    "selenium-profile",
}

PATTERNS = {
    "email address": re.compile(
        r"(?i)(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
    ),
    "Windows user directory": re.compile(
        r"(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\s]+"
    ),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "assigned secret": re.compile(
        r"(?i)(?:api[_-]?key|access[_-]?token|secret|password|cookie)"
        r"\s*[:=]\s*[\"'][^\"']{8,}[\"']"
    ),
}


def is_skipped(path: Path) -> bool:
    relative_parts = path.relative_to(ROOT).parts
    return any(part in SKIPPED_DIRECTORY_NAMES for part in relative_parts)


def iter_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not is_skipped(path)
    ]


def main() -> int:
    findings: list[str] = []

    for path in ROOT.rglob("*"):
        if not path.is_dir() or is_skipped(path):
            continue
        if path.name in FORBIDDEN_DIRECTORY_NAMES:
            findings.append(f"forbidden directory: {path.relative_to(ROOT)}")

    for path in iter_files():
        relative = path.relative_to(ROOT)

        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"forbidden file type: {relative}")
            continue

        if path.name == ".env":
            findings.append(f"secret settings file: {relative}")
            continue

        if path.resolve() == SELF:
            continue

        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".gitignore":
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"unreadable text file: {relative}")
            continue

        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {relative}")

    if findings:
        print("PUBLIC SAFETY CHECK: FAILED")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        return 1

    print("PUBLIC SAFETY CHECK: PASSED")
    print(f"Scanned {len(iter_files())} files under {ROOT.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
