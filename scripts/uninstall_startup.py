"""Uninstall TodoNess from Windows startup and stop the tray process."""

import subprocess
import sys
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PID_FILE = os.path.join(PROJECT_ROOT, "data", "todoness.pid")
TASK_NAME = "TodoNess"


def remove_scheduled_task():
    """Remove the TodoNess scheduled task."""
    print(f"Removing scheduled task '{TASK_NAME}'...")
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "does not exist" in stderr.lower() or "cannot find" in stderr.lower():
            print(f"Scheduled task '{TASK_NAME}' does not exist (already removed).")
        else:
            print(f"WARNING: Failed to remove scheduled task.\n{stderr}")
            return False
    else:
        print(f"Scheduled task '{TASK_NAME}' removed successfully.")
    return True


def stop_tray_process():
    """Stop the running tray process using the PID file."""
    if not os.path.isfile(PID_FILE):
        print("No PID file found (tray app not running or already stopped).")
        return True

    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
    except (ValueError, OSError) as e:
        print(f"WARNING: Could not read PID file: {e}")
        cleanup_pid_file()
        return True

    # Check if process is still running
    check = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}"],
        capture_output=True, text=True,
    )

    if str(pid) not in check.stdout:
        print(f"Process {pid} is not running (already stopped).")
        cleanup_pid_file()
        return True

    print(f"Stopping tray process (PID {pid})...")
    result = subprocess.run(
        ["taskkill", "/F", "/PID", str(pid)],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        print(f"WARNING: Failed to kill process {pid}.\n{result.stderr.strip()}")
        cleanup_pid_file()
        return False

    print(f"Process {pid} stopped successfully.")
    cleanup_pid_file()
    return True


def cleanup_pid_file():
    """Remove the PID file."""
    try:
        if os.path.isfile(PID_FILE):
            os.remove(PID_FILE)
            print(f"Removed PID file: {PID_FILE}")
    except OSError as e:
        print(f"WARNING: Could not remove PID file: {e}")


def main():
    print("=" * 50)
    print("  TodoNess Startup Uninstaller")
    print("=" * 50)
    print()

    # Step 1: Remove scheduled task
    remove_scheduled_task()
    print()

    # Step 2: Stop running tray process
    stop_tray_process()
    print()

    print("Done. TodoNess will no longer start at logon.")


if __name__ == "__main__":
    main()
