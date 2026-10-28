param(
	[Parameter(Mandatory = $true)][int]$ProcessId,
	[Parameter(Mandatory = $true)][string]$Source,
	[Parameter(Mandatory = $true)][string]$Target,
	[string]$RestartPath
)

$ErrorActionPreference = 'Stop'

function Show-UpdateError([string]$Message) {
	Add-Type -AssemblyName System.Windows.Forms
	[System.Windows.Forms.MessageBox]::Show(
		$Message,
		'fman++ portable update',
		[System.Windows.Forms.MessageBoxButtons]::OK,
		[System.Windows.Forms.MessageBoxIcon]::Error
	) | Out-Null
}

function Copy-Folder([string]$From, [string]$To, [string[]]$Options) {
	& robocopy $From $To @Options | Out-Null
	return $LASTEXITCODE
}

try {
	if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
		Wait-Process -Id $ProcessId -Timeout 60 -ErrorAction SilentlyContinue
		if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
			throw "fman is still running after 60 seconds (process $ProcessId)."
		}
	}

	if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
		throw "The extracted update folder does not exist: $Source"
	}
	if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
		throw "The portable application folder does not exist: $Target"
	}

	Get-ChildItem -LiteralPath $Source -Directory | ForEach-Object {
		if ($_.Name -ne 'Data') {
			$destination = Join-Path $Target $_.Name
			$code = Copy-Folder -From $_.FullName -To $destination `
				-Options @('/MIR', '/R:10', '/W:1')
			if ($code -ge 8) {
				throw "Could not copy update folder '$($_.Name)' (robocopy exit code $code)."
			}
		}
	}

	$code = Copy-Folder -From $Source -To $Target `
		-Options @('/R:10', '/W:1', '/XF', 'portable.txt')
	if ($code -ge 8) {
		throw "Could not copy update files (robocopy exit code $code)."
	}

	if ($RestartPath) {
		Start-Process -FilePath $RestartPath
	}
	Remove-Item -LiteralPath $Source -Recurse -Force
}
catch {
	Show-UpdateError ("The portable update could not be installed.`n`n" +
		"The extracted update is still available here so you can copy it manually:`n" +
		"$Source`n`n$($_.Exception.Message)")
	exit 1
}

exit 0
