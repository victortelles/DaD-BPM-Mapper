"""Security audit script: scanning for credentials, vulnerable patterns, and sensitive files."""

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|auth[_-]?key)\s*[:=]\s*['\"][^\'\"]+['\"]"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}"),
    re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"),
    re.compile(r"sk-[a-zA-Z0-9]{48}"),
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
]

IGNORED_DIRS = {".git", "venv", "__pycache__", ".pytest_cache", ".idea", ".vscode"}
IGNORED_EXTS = {".png", ".jpg", ".jpeg", ".wav", ".mp3", ".ogg", ".flac", ".zip", ".pyc"}


def run_audit():
    findings = []
    suspicious_files = []

    for path in REPO_ROOT.rglob("*"):
        if any(ignored in path.parts for ignored in IGNORED_DIRS):
            continue
        if not path.is_file():
            continue

        if path.name.lower() in {".env", "secrets.toml", "credentials.json", "id_rsa", "id_ed25519"}:
            suspicious_files.append(str(path.relative_to(REPO_ROOT)))

        if path.suffix.lower() in IGNORED_EXTS:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pat in PATTERNS:
            for match in pat.finditer(content):
                snippet = match.group(0)
                # Ignore harmless references and tests
                if any(ok in snippet.lower() for ok in ["fake", "example", "openai_api_key", "sample"]):
                    continue
                findings.append(f"{path.relative_to(REPO_ROOT)}: {snippet[:80]}")

    print("=== SECURITY AUDIT RESULTS ===")
    if suspicious_files:
        print(f"Suspicious sensitive files found: {suspicious_files}")
    else:
        print("No suspicious credential files found (.env, secrets.toml, etc.)")

    if findings:
        print(f"Potential credential matches found ({len(findings)}):")
        for f in findings:
            print("  ", f)
    else:
        print("No exposed credentials, tokens, or private keys found in files.")

    return len(findings) == 0 and len(suspicious_files) == 0


if __name__ == "__main__":
    success = run_audit()
    exit(0 if success else 1)
