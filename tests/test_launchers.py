"""Automated verification suite for cross-platform launcher scripts and caching."""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MAX_LOC = 400

LAUNCHER_FILES = {
    "run.bat": REPO_ROOT / "run.bat",
    "run.sh": REPO_ROOT / "run.sh",
    "run_windows.ps1": REPO_ROOT / "launchers" / "run_windows.ps1",
    "run_unix.sh": REPO_ROOT / "launchers" / "run_unix.sh",
}


def test_launcher_files_exist_and_loc_budget() -> None:
    """Verifies that all 4 launcher entry points exist and stay strictly < 400 LOC."""
    for name, path in LAUNCHER_FILES.items():
        assert path.is_file(), f"Expected launcher script missing: {name}"
        lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        assert lines < MAX_LOC, f"Launcher {name} exceeded {MAX_LOC} LOC ceiling: {lines} lines."


def test_run_bat_properties() -> None:
    """Verifies run.bat configuration: UTF-8 codepage, ExecutionPolicy Bypass, pause trap."""
    content = LAUNCHER_FILES["run.bat"].read_text(encoding="utf-8")
    assert "chcp 65001" in content, "run.bat missing UTF-8 codepage 65001"
    assert "ExecutionPolicy Bypass" in content, "run.bat missing ExecutionPolicy Bypass"
    assert "run_windows.ps1" in content, "run.bat must delegate to run_windows.ps1"
    assert "pause" in content.lower(), "run.bat must contain pause trap on exit"


def test_run_sh_properties() -> None:
    """Verifies run.sh POSIX compliance: shebang, delegation to run_unix.sh, arg forwarding."""
    content = LAUNCHER_FILES["run.sh"].read_text(encoding="utf-8")
    assert content.startswith("#!/"), "run.sh must begin with an executable shebang"
    assert "run_unix.sh" in content, "run.sh must delegate to launchers/run_unix.sh"
    assert '"$@"' in content, "run.sh must forward CLI arguments"


def test_bilingual_progress_badges_and_guidance() -> None:
    """Verifies all 4 terminal progress badges and download guidance in both orchestrators."""
    expected_badges = ["[1/4]", "[2/4]", "[3/4]", "[4/4]"]
    expected_keywords = [
        ("requisitos", "requirements"),
        ("entorno virtual", "virtual environment"),
        ("dependencias", "dependencies"),
        ("iniciando", "starting"),
    ]

    for script_key in ("run_windows.ps1", "run_unix.sh"):
        content = LAUNCHER_FILES[script_key].read_text(encoding="utf-8").lower()
        for badge in expected_badges:
            assert badge in content, f"Missing badge {badge} in {script_key}"
        for es_kw, en_kw in expected_keywords:
            assert es_kw in content, f"Missing Spanish milestone '{es_kw}' in {script_key}"
            assert en_kw in content, f"Missing English milestone '{en_kw}' in {script_key}"

        assert "https://www.python.org/downloads/" in content, f"Missing python.org URL in {script_key}"
        assert "3.10" in content, f"Missing Python 3.10 minimum version in {script_key}"


def test_powershell_ast_syntax() -> None:
    """Validates PowerShell AST syntax with zero parser errors."""
    ps_exe = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not ps_exe:
        pytest.skip("PowerShell executable not found on host.")

    ps1_path = LAUNCHER_FILES["run_windows.ps1"]
    parse_cmd = (
        f"$code = Get-Content -Raw '{ps1_path}'; "
        "$errs = $null; "
        "[System.Management.Automation.Language.Parser]::ParseInput($code, [ref]$null, [ref]$errs); "
        "if ($errs.Count -gt 0) { $errs | ForEach-Object { Write-Error $_.Message }; exit 1 } else { exit 0 }"
    )
    result = subprocess.run([ps_exe, "-NoProfile", "-Command", parse_cmd], capture_output=True, text=True)
    assert result.returncode == 0, f"PowerShell AST syntax errors in run_windows.ps1:\n{result.stderr}"


def test_bash_syntax_when_available() -> None:
    """Validates POSIX bash syntax via 'bash -n' when a working bash binary is accessible."""
    bash_candidates = [shutil.which("bash")]
    # Check common Git bash paths on Windows
    for git_bash in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"D:\TellesVM\Programas\Apps Para programar\Git\Git\Git\bin\bash.exe",
    ):
        if Path(git_bash).is_file():
            bash_candidates.append(git_bash)

    valid_bash = None
    for cand in filter(None, bash_candidates):
        try:
            probe = subprocess.run([cand, "--version"], capture_output=True, text=True, timeout=3)
            if probe.returncode == 0 and "GNU bash" in probe.stdout:
                valid_bash = cand
                break
        except Exception:
            continue

    if not valid_bash:
        pytest.skip("Working GNU bash executable not found in test environment.")

    for script_key in ("run.sh", "run_unix.sh"):
        script_path = str(LAUNCHER_FILES[script_key])
        proc = subprocess.run([valid_bash, "-n", script_path], capture_output=True, text=True)
        assert proc.returncode == 0, f"Bash syntax check failed for {script_key}:\n{proc.stderr}"


def test_dependency_hash_cache_workflow(tmp_path: Path) -> None:
    """Simulates dependency hash calculation, cache match (hit), and invalidation (miss)."""
    req_file = tmp_path / "requirements.txt"
    hash_file = tmp_path / ".requirements.hash"

    req_file.write_text("streamlit==1.42.0\nlibrosa==0.10.2.post1\n", encoding="utf-8")
    initial_hash = hashlib.sha256(req_file.read_bytes()).hexdigest().lower()
    hash_file.write_text(initial_hash, encoding="utf-8")

    # Simulation 1: Identical requirements -> Cache hit
    current_hash = hashlib.sha256(req_file.read_bytes()).hexdigest().lower()
    saved_hash = hash_file.read_text(encoding="utf-8").strip().lower()
    assert current_hash == saved_hash, "Initial cache check must match (cache hit)"

    # Simulation 2: Modified requirements -> Cache miss
    req_file.write_text("streamlit==1.42.0\nlibrosa==0.10.2.post1\nsoundfile>=0.12.1\n", encoding="utf-8")
    new_hash = hashlib.sha256(req_file.read_bytes()).hexdigest().lower()
    assert new_hash != saved_hash, "Modified requirements must produce hash mismatch (cache miss)"

    # Simulation 3: Cache update after install -> Cache hit renewed
    hash_file.write_text(new_hash, encoding="utf-8")
    updated_saved_hash = hash_file.read_text(encoding="utf-8").strip().lower()
    assert new_hash == updated_saved_hash, "Updated cache must match new requirements hash"


def test_unix_scripts_executable_mode_in_git() -> None:
    """Verifies that Unix launcher scripts are tracked with 100755 filemode in git."""
    git_exe = shutil.which("git")
    if not git_exe:
        pytest.skip("git not found in test environment.")

    cmd = [git_exe, "ls-files", "--stage", "run.sh", "launchers/run_unix.sh"]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if proc.returncode == 0 and proc.stdout:
        for line in proc.stdout.strip().splitlines():
            mode = line.split()[0]
            assert mode == "100755", f"Unix script not set as executable (100755) in git index: {line}"
