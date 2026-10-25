# freeze() cannot replace target\fman while a process is running from it.
# Ask fman to close itself so it can save its session normally. It shows a
# countdown first, which the user can cancel with Esc.
param(
    [Parameter(Mandatory = $true)][string]$Directory,
    [int]$TimeoutSeconds = 15,
    [int]$CountdownSeconds = 10
)

# Must match MESSAGE_NAME in src\main\python\fman\impl\build_shutdown.py.
$MessageName = 'fman.CloseForBuild'

$prefix = [IO.Path]::GetFullPath($Directory).TrimEnd('\') + '\'
function Test-InFolder([string]$path) {
    $path -and $path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)
}

# A missing build directory cannot contain a process or locked DLL.
if (-not (Test-Path -LiteralPath $prefix)) { exit 0 }

# Other programs can hold a DLL from the folder too, eg. php.exe started from a
# terminal fman opened (child processes inherit PyInstaller's DLL directory).
# They are not ours to close, so name them and stop the build. The Restart
# Manager answers "who holds these files" directly; enumerating every process's
# modules from PowerShell takes minutes.
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public static class FileLockers {
    [StructLayout(LayoutKind.Sequential)]
    struct RM_UNIQUE_PROCESS { public int dwProcessId; public System.Runtime.InteropServices.ComTypes.FILETIME ProcessStartTime; }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct RM_PROCESS_INFO {
        public RM_UNIQUE_PROCESS Process;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)] public string strAppName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)] public string strServiceShortName;
        public int ApplicationType; public uint AppStatus; public uint TSSessionId;
        [MarshalAs(UnmanagedType.Bool)] public bool bRestartable;
    }

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    static extern int RmStartSession(out uint handle, int flags, string key);
    [DllImport("rstrtmgr.dll")]
    static extern int RmEndSession(uint handle);
    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    static extern int RmRegisterResources(uint handle, uint nFiles, string[] files, uint nApps, IntPtr apps, uint nServices, string[] services);
    [DllImport("rstrtmgr.dll")]
    static extern int RmGetList(uint handle, out uint needed, ref uint count, [In, Out] RM_PROCESS_INFO[] infos, ref uint reasons);

    public static int[] Find(string[] files) {
        uint handle;
        if (RmStartSession(out handle, 0, Guid.NewGuid().ToString()) != 0) return new int[0];
        try {
            if (RmRegisterResources(handle, (uint)files.Length, files, 0, IntPtr.Zero, 0, null) != 0) return new int[0];
            uint needed, count = 0, reasons = 0;
            RM_PROCESS_INFO[] infos = null;
            int result;
            // ERROR_MORE_DATA (234): the list grew between the two calls.
            do {
                infos = new RM_PROCESS_INFO[count];
                result = RmGetList(handle, out needed, ref count, infos, ref reasons);
                count = needed;
            } while (result == 234);
            if (result != 0) return new int[0];
            var ids = new List<int>();
            for (int i = 0; i < needed; i++) ids.Add(infos[i].Process.dwProcessId);
            return ids.ToArray();
        } finally { RmEndSession(handle); }
    }
}

public static class FmanWindow {
    delegate bool EnumWindowsProc(IntPtr hwnd, IntPtr lParam);
    [DllImport("user32.dll")]
    static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);
    [DllImport("user32.dll")]
    static extern uint GetWindowThreadProcessId(IntPtr hwnd, out int processId);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    static extern uint RegisterWindowMessage(string name);
    [DllImport("user32.dll")]
    static extern IntPtr SendMessageTimeout(IntPtr hwnd, uint msg, IntPtr wParam, IntPtr lParam, uint flags, uint timeoutMs, out IntPtr result);
    [DllImport("user32.dll")]
    static extern bool AllowSetForegroundWindow(int processId);

    const uint SMTO_ABORTIFHUNG = 2;

    // True once a window of the process started the countdown. An fman built
    // before the countdown existed does not know the message and answers 0.
    public static bool AskToClose(int processId, string messageName, int seconds) {
        uint message = RegisterWindowMessage(messageName);
        // The build console is in front; this lets fman raise its countdown.
        AllowSetForegroundWindow(processId);
        bool started = false;
        EnumWindows((hwnd, _) => {
            int owner;
            GetWindowThreadProcessId(hwnd, out owner);
            IntPtr answer;
            if (owner == processId
                && SendMessageTimeout(hwnd, message, (IntPtr)seconds, IntPtr.Zero, SMTO_ABORTIFHUNG, 2000, out answer) != IntPtr.Zero
                && answer == (IntPtr)1) {
                started = true;
            }
            return !started;
        }, IntPtr.Zero);
        return started;
    }
}
'@

function Exit-IfDllsLocked {
    if (-not (Test-Path -LiteralPath $prefix)) { return }
    $files = @(Get-ChildItem -LiteralPath $prefix -Recurse -File -Include *.dll, *.pyd | ForEach-Object FullName)
    if ($files.Count -eq 0) { return }
    $holders = @([FileLockers]::Find($files) | Sort-Object -Unique)
    if ($holders.Count -eq 0) { return }
    foreach ($id in $holders) {
        $name = (Get-Process -Id $id -ErrorAction SilentlyContinue).ProcessName
        Write-Host "ERROR: $name (PID $id) has a DLL loaded from $prefix"
    }
    Write-Host "Close it by hand, then build again."
    exit 1
}

$running = @(Get-Process | Where-Object { Test-InFolder $_.Path })
if ($running.Count -eq 0) { Exit-IfDllsLocked; exit 0 }

$waitSeconds = $TimeoutSeconds
foreach ($process in $running) {
    if ([FmanWindow]::AskToClose($process.Id, $MessageName, $CountdownSeconds)) {
        Write-Host "$($process.ProcessName) (PID $($process.Id)) closes in $CountdownSeconds s. Press Esc there to keep it running."
        $waitSeconds = $TimeoutSeconds + $CountdownSeconds
        continue
    }
    Write-Host "Closing $($process.ProcessName) (PID $($process.Id))..."
    # Never kill it: a file operation may still be in progress.
    [void]$process.CloseMainWindow()
}

$deadline = (Get-Date).AddSeconds($waitSeconds)
while ((Get-Date) -lt $deadline -and ($running | Where-Object { -not $_.HasExited })) {
    Start-Sleep -Milliseconds 200
}

$left = @($running | Where-Object { -not $_.HasExited })
if ($left.Count -gt 0) {
    foreach ($process in $left) {
        Write-Host "ERROR: $($process.ProcessName) (PID $($process.Id)) is still running from $prefix"
    }
    Write-Host "Close it by hand (a dialog may be waiting for an answer, or the countdown was canceled), then build again."
    exit 1
}
Exit-IfDllsLocked
exit 0
