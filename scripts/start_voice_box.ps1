[CmdletBinding()]
param(
    [string]$HostName = "192.168.34.200",
    [string]$UserName = "bst"
)

$ErrorActionPreference = "Stop"
$remote = "${UserName}@${HostName}"
$localScript = Join-Path $PSScriptRoot "configure_voice_box.sh"
$remoteScript = "/tmp/configure_voice_box.sh"

if (-not (Test-Path -LiteralPath $localScript -PathType Leaf)) {
    throw "Missing helper script: $localScript"
}

foreach ($command in @("ssh", "scp")) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Command '$command' is unavailable. Install the Windows OpenSSH Client first."
    }
}

Write-Host "[1/4] Checking target network $HostName ..."
$connection = Test-NetConnection -ComputerName $HostName -Port 22 -WarningAction SilentlyContinue
if (-not $connection.TcpTestSucceeded) {
    throw "Cannot connect to ${HostName}:22. Check the cable, Windows IPv4 address and the target SSH service."
}

Write-Host "[2/4] Checking SSH login for $remote ..."
& ssh -o ConnectTimeout=8 $remote "printf 'SSH connection OK\n'"
if ($LASTEXITCODE -ne 0) {
    throw "SSH login failed with exit code $LASTEXITCODE."
}

Write-Host "[3/4] Uploading the configuration helper ..."
& scp $localScript "${remote}:${remoteScript}"
if ($LASTEXITCODE -ne 0) {
    throw "SCP upload failed with exit code $LASTEXITCODE."
}

Write-Host "[4/4] Updating the wake word configuration ..."
& ssh -t $remote "chmod 700 '$remoteScript' && '$remoteScript'"
if ($LASTEXITCODE -ne 0) {
    throw "Remote keyword update failed with exit code $LASTEXITCODE. Read the error above."
}

Write-Host "Done. The UTF-8 wake word update succeeded. The speech service was not started." -ForegroundColor Green
