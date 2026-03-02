"""Install TodoNess as a Windows startup application via Task Scheduler."""

import subprocess
import sys
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAY_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "todoness_tray.pyw")
TASK_NAME = "TodoNess"


def ensure_dependencies():
    """Install pystray and Pillow if not already available."""
    missing = []
    try:
        import pystray  # noqa: F401
    except ImportError:
        missing.append("pystray")
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing.append("Pillow")

    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + missing,
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"Failed to install dependencies:\n{result.stderr}")
            return False
        print("Dependencies installed successfully.")
    else:
        print("All dependencies already installed.")
    return True


def find_pythonw():
    """Find pythonw.exe in the same directory as the current Python interpreter."""
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if not os.path.isfile(pythonw):
        print(f"ERROR: pythonw.exe not found at {pythonw}")
        return None
    return pythonw


def register_scheduled_task(pythonw):
    """Register TodoNess as a scheduled task that runs at logon."""
    ps_script = f'''
$action = New-ScheduledTaskAction -Execute '"{pythonw}"' -Argument '"{TRAY_SCRIPT}"' -WorkingDirectory '"{PROJECT_ROOT}"'
$trigger = New-ScheduledTaskTrigger -AtLogon -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName "{TASK_NAME}" -Action $action -Trigger $trigger -Settings $settings -Force
'''
    print(f"Registering scheduled task '{TASK_NAME}'...")
    result = subprocess.run(
        ["powershell", "-Command", ps_script],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        print(f"ERROR: Failed to register scheduled task.\n{result.stderr}")
        return False

    print(f"Scheduled task '{TASK_NAME}' registered successfully.")
    print(f"  Python:    {pythonw}")
    print(f"  Script:    {TRAY_SCRIPT}")
    print(f"  WorkDir:   {PROJECT_ROOT}")
    print(f"  Trigger:   At logon for current user")
    return True


def start_tray_now(pythonw):
    """Start the tray application immediately."""
    print("Starting TodoNess tray app...")
    try:
        subprocess.Popen(
            [pythonw, TRAY_SCRIPT],
            cwd=PROJECT_ROOT,
            creationflags=subprocess.DETACHED_PROCESS,
        )
        print("TodoNess tray app started.")
    except Exception as e:
        print(f"ERROR: Failed to start tray app: {e}")


def main():
    print("=" * 50)
    print("  TodoNess Startup Installer")
    print("=" * 50)
    print()

    # Step 1: Check/install dependencies
    if not ensure_dependencies():
        sys.exit(1)
    print()

    # Step 2: Find pythonw.exe
    pythonw = find_pythonw()
    if not pythonw:
        sys.exit(1)
    print()

    # Step 3: Register scheduled task
    if not register_scheduled_task(pythonw):
        sys.exit(1)
    print()

    # Step 4: Optionally start now
    answer = input("Start TodoNess tray app now? [Y/n] ").strip().lower()
    if answer in ("", "y", "yes"):
        start_tray_now(pythonw)
    else:
        print("Skipped. The tray app will start at next logon.")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
