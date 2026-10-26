<#
.SYNOPSIS
Call fman's scripting API from PowerShell (5.1 or 7+).

.EXAMPLE
.\fman_api.ps1 state
.\fman_api.ps1 commands
.\fman_api.ps1 command move_cursor_down
.\fman_api.ps1 command open_directory -Arguments @{ url = 'file://C:/Windows' }
.\fman_api.ps1 command reload -Pane 1

Set $env:FMAN_API_URL to override the default http://127.0.0.1:47447.
#>
param(
    [Parameter(Mandatory)][ValidateSet('state', 'commands', 'command')][string]$Action,
    [string]$Name,
    [hashtable]$Arguments = @{},
    [Nullable[int]]$Pane
)

$ErrorActionPreference = 'Stop'
$apiUrl = if ($env:FMAN_API_URL) { $env:FMAN_API_URL } else { 'http://127.0.0.1:47447' }
$tokenFile = Join-Path $env:APPDATA 'fman\Local\ScriptingApiToken.txt'
if (-not (Test-Path $tokenFile)) {
    throw "No token file at $tokenFile. Run 'Toggle scripting API' in fman first."
}
$headers = @{ Authorization = 'Bearer ' + (Get-Content $tokenFile -Raw -Encoding UTF8).Trim() }

switch ($Action) {
    'state' { $result = Invoke-RestMethod -Headers $headers -Uri "$apiUrl/v1/state" }
    'commands' { $result = Invoke-RestMethod -Headers $headers -Uri "$apiUrl/v1/commands" }
    'command' {
        if (-not $Name) { throw 'command needs -Name, e.g. .\fman_api.ps1 command reload' }
        $body = @{ name = $Name; args = $Arguments }
        if ($null -ne $Pane) { $body.pane = $Pane }
        $json = $body | ConvertTo-Json -Compress -Depth 5
        # Send bytes so non-ASCII paths survive PowerShell 5.1's default body encoding.
        $result = Invoke-RestMethod -Method Post -Headers $headers -Uri "$apiUrl/v1/command" `
            -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($json))
    }
}
$result | ConvertTo-Json -Depth 5
