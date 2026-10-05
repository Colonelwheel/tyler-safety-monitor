"""Read-only staged-file privacy gate for this public repository.

Reports paths and categories, never matched private contents. Run before commit.
This is defense in depth: keep runtime data outside Git and review every diff.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
import subprocess
import sys


PRIVATE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff",
                    ".mp4", ".avi", ".mkv", ".mov", ".wav", ".mp3", ".db", ".sqlite",
                    ".sqlite3", ".log", ".task", ".tflite", ".onnx", ".pem", ".key", ".pfx"}
PRIVATE_PARTS = {".venv", "__pycache__", "calibration", "incidents", "events", "models",
                 "logs", "database", "runtime", "local", "replays", ".pytest_cache", "build", "dist"}
PATTERNS = (
    ("credential identifier", re.compile(r"\b(?:AC|SK)[0-9a-fA-F]{32}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("phone number", re.compile(r"(?<!\w)(?:\+?1[ .-]?)?\(?[2-9]\d{2}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")),
    ("credential assignment", re.compile(
        r"(?im)(?:auth_token|api_secret|twilio_token|password)\s*[:=]\s*[\"'](?!redacted|example|placeholder|[<${])[A-Za-z0-9_+/=-]{12,}[\"']")),
)


def issues_for(path: str, content: bytes) -> list[str]:
    parsed = PurePosixPath(path)
    issues = []
    if parsed.suffix.lower() in PRIVATE_SUFFIXES or any(part.lower() in PRIVATE_PARTS for part in parsed.parts):
        issues.append("private/generated file type or directory")
    if parsed.name == ".env" or parsed.name.startswith(".env."):
        issues.append("environment file")
    if parsed.suffix.lower() == ".json" and parsed.name != "config.example.json":
        issues.append("nonexample runtime/configuration JSON")
    if parsed.suffix.lower() == ".jsonl":
        issues.append("runtime feature sequence JSONL")
    if len(content) > 1024 * 1024 or b"\0" in content:
        issues.append("binary or oversized artifact requires separate review")
        return issues
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        issues.append("nontext artifact")
        return issues
    for label, pattern in PATTERNS:
        if pattern.search(text):
            issues.append(label)
    return issues


def main() -> int:
    names = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
                           check=True, capture_output=True).stdout.decode("utf-8").split("\0")
    failed = False
    count = 0
    for name in filter(None, names):
        count += 1
        content = subprocess.run(["git", "show", f":{name}"], check=True, capture_output=True).stdout
        issues = issues_for(name, content)
        if issues:
            failed = True
            print(f"BLOCKED {name}: {', '.join(issues)}")
    print(f"Staged privacy review: {count} files; {'FAILED' if failed else 'passed'}.")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
