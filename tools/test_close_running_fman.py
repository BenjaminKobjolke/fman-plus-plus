"""Check that the Windows build closes only processes in its build folder."""

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


SCRIPT = Path(__file__).with_name("close_running_fman.ps1")


def report_progress(message):
    print(message, flush=True)


def run_helper(directory, timeout_seconds):
    return subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(SCRIPT), "-Directory", str(directory),
            "-TimeoutSeconds", str(timeout_seconds), "-CountdownSeconds", "1",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        # A run normally takes 2 s, but PowerShell startup and Add-Type
        # sometimes stall for 20-30 s on this machine (AV scanning).
        timeout=90,
    )


def start_cmd(directory):
    executable = directory / "cmd.exe"
    shutil.copyfile(Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe", executable)
    return subprocess.Popen(
        [str(executable), "/Q"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def start_dll_user(directory):
    # A process started elsewhere that only loaded a DLL from the folder, like
    # php.exe launched from a terminal fman opened.
    # A venv's python.exe is a launcher whose child loads the DLL under a different PID.
    dll = directory / "fman_close_test.dll"
    shutil.copyfile(Path(os.environ["SystemRoot"]) / "System32" / "version.dll", dll)
    load_and_wait = (
        "import ctypes, sys; "
        "dll = ctypes.WinDLL(sys.argv[1]); sys.stdin.read()"
    )
    return subprocess.Popen(
        [sys._base_executable, "-c", load_and_wait, str(dll)],
        stdin=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


# Stands in for fman's BuildShutdownFilter: a window that answers the close
# request, and with "exit" also quits, as fman does once the countdown ends.
# The message name must match MESSAGE_NAME in fman/impl/build_shutdown.py.
COUNTDOWN_WINDOW = r'''
import ctypes, sys
from ctypes import wintypes
user32 = ctypes.windll.user32
message = user32.RegisterWindowMessageW("fman.CloseForBuild")
exits = sys.argv[1] == "exit"
WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)
user32.CreateWindowExW.restype = wintypes.HWND
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
user32.SetWindowLongPtrW.restype = ctypes.c_void_p
user32.CallWindowProcW.argtypes = [
    ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
user32.CallWindowProcW.restype = ctypes.c_ssize_t

def answer(hwnd, msg, wparam, lparam):
    if msg == message:
        if exits:
            user32.PostQuitMessage(0)
        return 1
    return user32.CallWindowProcW(default, hwnd, msg, wparam, lparam)

proc = WNDPROC(answer)
hwnd = user32.CreateWindowExW(
    0, "STATIC", "fman", 0, 0, 0, 0, 0, None, None, None, None
)
default = user32.SetWindowLongPtrW(hwnd, -4, ctypes.cast(proc, ctypes.c_void_p))
msg = wintypes.MSG()
while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
    user32.DispatchMessageW(ctypes.byref(msg))
'''


def start_countdown_window(directory, mode):
    # The helper only asks processes running from the folder, so run a copy of
    # the base interpreter from there. A venv's python.exe is a launcher whose
    # real interpreter would run from elsewhere.
    base = Path(sys._base_executable).parent
    for name in ["python.exe", *(dll.name for dll in base.glob("*.dll"))]:
        if not (directory / name).exists():
            shutil.copyfile(base / name, directory / name)
    return subprocess.Popen(
        [str(directory / "python.exe"), "-c", COUNTDOWN_WINDOW, mode],
        env={**os.environ, "PYTHONHOME": sys.base_prefix},
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def stop_cmd(process):
    if process.poll() is None:
        process.terminate()
    process.wait(timeout=10)
    if process.stdin and not process.stdin.closed:
        process.stdin.close()


def check_close_running_fman():
    with tempfile.TemporaryDirectory(prefix="close-running-fman-") as temporary:
        directory = Path(temporary)

        report_progress("Checking a missing build directory")
        result = run_helper(directory / "missing", 1)
        assert result.returncode == 0, result.stdout + result.stderr

        report_progress("Checking a process that does not answer")
        process = start_cmd(directory)
        try:
            result = run_helper(directory, 1)
            assert result.returncode == 1, result.stdout + result.stderr
            assert str(process.pid) in result.stdout + result.stderr
            assert process.poll() is None, "The helper must not kill a process"
        finally:
            stop_cmd(process)

        report_progress("Checking a process that closes its input")
        process = start_cmd(directory)
        close_stdin = threading.Timer(0.5, process.stdin.close)
        try:
            close_stdin.start()
            result = run_helper(directory, 10)
            assert result.returncode == 0, result.stdout + result.stderr
        finally:
            close_stdin.cancel()
            close_stdin.join()
            stop_cmd(process)

        report_progress("Checking fman closing after its countdown")
        process = start_countdown_window(directory, "exit")
        try:
            time.sleep(1)
            result = run_helper(directory, 10)
            assert result.returncode == 0, result.stdout + result.stderr
            assert "closes in 1 s" in result.stdout, result.stdout
        finally:
            stop_cmd(process)

        report_progress("Checking fman canceling its countdown")
        process = start_countdown_window(directory, "cancel")
        try:
            time.sleep(1)
            result = run_helper(directory, 1)
            assert result.returncode == 1, result.stdout + result.stderr
            assert "countdown was canceled" in result.stdout, result.stdout
            assert process.poll() is None, "The helper must not kill a process"
        finally:
            stop_cmd(process)

        report_progress("Checking a process that loaded a DLL from the build directory")
        process = start_dll_user(directory)
        try:
            time.sleep(1)
            result = run_helper(directory, 1)
            assert result.returncode == 1, result.stdout + result.stderr
            assert str(process.pid) in result.stdout + result.stderr
            assert process.poll() is None, "The helper must not kill a process"
        finally:
            stop_cmd(process)


if __name__ == "__main__":
    check_close_running_fman()
    print("close running fman OK")
