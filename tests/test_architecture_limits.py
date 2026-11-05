"""Architectural gate tests enforcing the <400 LOC file limit and S.O.L.I.D layer decoupling."""

import ast
import subprocess
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent.parent
MAX_LOC = 400
SCANNED_DIRS = ("audio_analysis", "export", "models", "ui", "tests", "launchers")
SCANNED_EXTENSIONS = {".py", ".html", ".js", ".css", ".ps1", ".sh", ".bat"}
DOMAIN_DIRS = ("models", "audio_analysis", "export")


def _collect_target_files() -> List[Path]:
    files: List[Path] = []
    for root_file in (REPO_ROOT / "app.py", REPO_ROOT / "run.bat", REPO_ROOT / "run.sh"):
        if root_file.is_file():
            files.append(root_file)

    for folder_name in SCANNED_DIRS:
        folder = REPO_ROOT / folder_name
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            if "__pycache__" in path.parts or not path.is_file():
                continue
            if path.suffix.lower() in SCANNED_EXTENSIONS:
                files.append(path)
    return files


def test_every_file_strictly_under_400_lines() -> None:
    """Every source, UI component, and test file must contain strictly fewer than 400 lines (< 400 LOC)."""
    target_files = _collect_target_files()
    assert target_files, "No source files discovered during architectural scan."

    violations: List[str] = []
    for file_path in target_files:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        line_count = len(text.splitlines())
        if line_count >= MAX_LOC:
            rel = file_path.relative_to(REPO_ROOT).as_posix()
            violations.append(f"{rel}: {line_count} lines (limit < {MAX_LOC})")

    assert not violations, "Files exceeding the < 400 LOC architectural ceiling:\n" + "\n".join(violations)


def test_domain_layers_do_not_import_streamlit() -> None:
    """Domain packages (models/, audio_analysis/, export/) must never depend on Streamlit UI."""
    violations: List[str] = []
    for folder_name in DOMAIN_DIRS:
        folder = REPO_ROOT / folder_name
        if not folder.is_dir():
            continue
        for py_file in sorted(folder.rglob("*.py")):
            if "__pycache__" in py_file.parts:
                continue
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "streamlit" or alias.name.startswith("streamlit."):
                            violations.append(f"{py_file.relative_to(REPO_ROOT).as_posix()}:{node.lineno}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module == "streamlit" or node.module.startswith("streamlit."):
                        violations.append(f"{py_file.relative_to(REPO_ROOT).as_posix()}:{node.lineno}")

    assert not violations, "Forbidden streamlit imports found in domain layers:\n" + "\n".join(violations)


def test_core_modules_standalone_import_without_circular_dependencies() -> None:
    """Core domain modules must import cleanly in an isolated subprocess without circular imports."""
    check_script = (
        "import sys; "
        "import audio_analysis.exceptions; "
        "import models.song_metadata as sm; "
        "import audio_analysis.security as sec; "
        "import audio_analysis.bpm_sections as bs; "
        "import export.package_builder as pb; "
        "assert hasattr(sm, 'SongMetadata'); "
        "assert hasattr(sec, 'validate_audio_upload'); "
        "assert hasattr(bs, 'recalculate_beats'); "
        "assert hasattr(pb, 'build_mod_zip'); "
        "assert 'streamlit' not in sys.modules"
    )
    proc = subprocess.run(
        [sys.executable, "-c", check_script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Standalone core import failed:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"


def test_zero_emojis_in_ui_and_app() -> None:
    """Per Streamlit best practices (SKILL.md), UI must use Material Symbols icons rather than emojis."""
    import re

    emoji_pattern = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
    targets = [REPO_ROOT / "app.py"] + list((REPO_ROOT / "ui").glob("*.py"))
    violations = []
    for path in targets:
        if path.is_file():
            matches = set(emoji_pattern.findall(path.read_text(encoding="utf-8")))
            if matches:
                violations.append(f"{path.name}: found emojis {matches}")
    assert not violations, "Emojis found in UI code:\n" + "\n".join(violations)


def test_all_python_files_have_valid_syntax() -> None:
    """All python files in the repository must be valid syntax and compile cleanly."""
    for file_path in _collect_target_files():
        if file_path.suffix.lower() == ".py":
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
            compile(tree, filename=str(file_path), mode="exec")

