import os
import shutil
import sys
import subprocess
import threading
from pathlib import Path


def _gemini_exe() -> str:
    """Return the resolved gemini executable path (handles gemini.cmd on Windows)."""
    return shutil.which("gemini") or "gemini"


class _ModelNotFoundError(Exception):
    pass


def _get_system_md_path() -> str:
    candidates = [
        Path.cwd() / ".gemini" / "system.md",
        Path(__file__).parent.parent / ".gemini" / "system.md",
    ]
    for path in candidates:
        if path.exists():
            return str(path.resolve())
    return ""


def execute(plan_text: str) -> str:
    """Run Gemini CLI with the plan. Streams output to terminal. Returns full output."""
    system_md = _get_system_md_path()
    env = os.environ.copy()
    if system_md:
        env["GEMINI_SYSTEM_MD"] = system_md

    full_output: list = []

    # First attempt: gemini-3-flash-preview
    try:
        _run_gemini(
            [_gemini_exe(), "-p", plan_text, "-m", "gemini-3-flash-preview", "--output-format", "text"],
            env=env,
            output_collector=full_output,
        )
        return "\n".join(full_output)
    except _ModelNotFoundError:
        pass  # Fall through to default model

    # Fallback: default Gemini CLI model
    full_output.clear()
    _run_gemini(
        [_gemini_exe(), "-p", plan_text, "--output-format", "text"],
        env=env,
        output_collector=full_output,
    )
    return "\n".join(full_output)


def _run_gemini(cmd: list, env: dict, output_collector: list) -> None:
    """Run gemini subprocess, stream stdout. Raises _ModelNotFoundError or sys.exit on error."""
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        print("Error: Gemini CLI not installed.")
        print("Install with: npm install -g @google/gemini-cli")
        sys.exit(1)

    killed = [False]

    def _kill_on_timeout():
        import time
        time.sleep(120)
        if process.poll() is None:
            killed[0] = True
            process.kill()

    timer = threading.Thread(target=_kill_on_timeout, daemon=True)
    timer.start()

    stderr_chunks: list = []

    def _read_stderr():
        for chunk in process.stderr:
            stderr_chunks.append(chunk)

    stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
    stderr_thread.start()

    for line in process.stdout:
        try:
            sys.stdout.write(line)
        except UnicodeEncodeError:
            # Windows cmd.exe may be cp1252 — replace unencodable chars
            sys.stdout.write(line.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding))
        sys.stdout.flush()
        output_collector.append(line.rstrip("\n"))

    process.wait()
    stderr_thread.join(timeout=5)

    if killed[0]:
        print("\nGemini took too long. Try a simpler query.")
        sys.exit(1)

    stderr_text = "".join(stderr_chunks).lower()

    if process.returncode != 0:
        if any(w in stderr_text for w in ("auth", "login", "unauthorized", "credential")):
            print("\nRun gemini in terminal and login with Google account.")
            sys.exit(1)
        if any(w in stderr_text for w in ("rate", "quota", "limit", "exceeded", "1000")):
            print("\nDaily Gemini free limit reached. Resets at midnight Pacific Time.")
            sys.exit(1)
        # Model not found, permission denied, or any other non-zero exit → trigger fallback
        raise _ModelNotFoundError()
