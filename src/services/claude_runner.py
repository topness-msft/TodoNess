"""Shared subprocess manager for `claude -p` commands.

Spawns and tracks labeled subprocesses.  Different labels run in parallel;
the same label won't double-spawn.
"""

import logging
import os
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"

# label -> subprocess.Popen
_processes: dict[str, subprocess.Popen] = {}
# label -> open file handle (so we can close it when process finishes)
_log_files: dict[str, object] = {}


def _cleanup(label: str) -> None:
    """Close log file handle for a finished process."""
    fh = _log_files.pop(label, None)
    if fh:
        try:
            fh.close()
        except Exception as e:
            logger.debug(f"Failed to close log file for '{label}': {e}")


def _skill_persist(label: str) -> None:
    """Extract skill output from log file and write to DB.

    This is the PRIMARY persistence path — skill commands just output text,
    and this function captures it from the log after the process exits.

    Extraction priority:
    1. Content between <<<SKILL_OUTPUT>>> / <<<END_SKILL_OUTPUT>>> markers
    2. Full log content as-is (fallback when Claude skips markers)
    """
    if not label.startswith("skill:"):
        return

    parts = label.split(":")
    if len(parts) != 3:
        return

    skill_name, task_id_str = parts[1], parts[2]
    try:
        task_id = int(task_id_str)
    except ValueError:
        return

    db_path = PROJECT_ROOT / "data" / "claudetodo.db"
    if not db_path.exists():
        return

    # Read log file first (before opening DB) so we can bail early
    safe_label = label.replace(":", "_").replace("/", "_")
    log_path = LOG_DIR / f"{safe_label}.log"
    if not log_path.exists():
        logger.warning(f"[{label}] persist: log file not found")
        return

    try:
        log_content = log_path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as e:
        logger.error(f"[{label}] persist: failed to read log: {e}")
        return

    if not log_content:
        logger.warning(f"[{label}] persist: log file is empty")
        return

    # Try marker extraction first
    match = re.search(
        r"<<<SKILL_OUTPUT>>>\s*\n(.*?)\n\s*<<<END_SKILL_OUTPUT>>>",
        log_content,
        re.DOTALL,
    )
    if match:
        extracted = match.group(1).strip()
        source = "markers"
    else:
        extracted = log_content
        source = "full log"

    if not extracted:
        logger.warning(f"[{label}] persist: extracted content is empty")
        return

    conn = sqlite3.connect(str(db_path))
    try:
        # Check if skill_output was already written (e.g. Claude did execute DB code)
        row = conn.execute(
            "SELECT skill_output FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row and row[0]:
            logger.info(f"[{label}] persist: skill_output already in DB, skipping")
            return

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "UPDATE tasks SET skill_output = ?, suggestion_refreshed_at = ?, updated_at = ? WHERE id = ?",
            (extracted, now, now, task_id),
        )
        conn.commit()
        logger.info(
            f"[{label}] persist: saved skill_output from {source} ({len(extracted)} chars)"
        )
    except Exception as e:
        logger.error(f"[{label}] persist failed: {e}")
    finally:
        conn.close()


def is_running(label: str) -> bool:
    """Check if a labeled process is still running."""
    proc = _processes.get(label)
    if proc is None:
        return False
    if proc.poll() is not None:
        _skill_persist(label)
        _cleanup(label)
        del _processes[label]
        return False
    return True


def run_claude(command: str, label: str) -> dict:
    """Launch `claude -p "<command>"` if *label* is not already running.

    Returns {"ok": True/False, "message": ...}.
    """
    if is_running(label):
        return {"ok": False, "message": f"'{label}' already running."}

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    safe_label = label.replace(":", "_").replace("/", "_")
    log_path = LOG_DIR / f"{safe_label}.log"

    try:
        fh = open(str(log_path), "w")
        proc = subprocess.Popen(
            [
                "claude", "-p", command,
                "--no-session-persistence",
                "--allowedTools",
                "mcp__workiq__ask_work_iq,Bash,Read,Write,Glob,Grep",
            ],
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=fh,
            stderr=fh,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        _processes[label] = proc
        _log_files[label] = fh
        logger.info(f"[{label}] started: PID {proc.pid}")
        return {"ok": True, "message": f"'{label}' started (PID {proc.pid})."}
    except FileNotFoundError:
        logger.warning("claude CLI not found on PATH")
        return {"ok": False, "message": "claude CLI not found on PATH."}
    except Exception as e:
        logger.error(f"[{label}] launch failed: {e}")
        return {"ok": False, "message": str(e)}


def get_status() -> dict:
    """Return dict of all tracked labels and whether they're running."""
    # Prune finished processes
    labels = list(_processes.keys())
    for label in labels:
        is_running(label)  # side-effect: removes finished

    return {label: True for label in _processes}
