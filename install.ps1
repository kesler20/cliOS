# Adds the `cli` function to your PowerShell profile. Run once per machine:
#   pwsh -File install.ps1

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSCommandPath
$entry = Join-Path $repo 'bin/cli.ps1'
$marker = '# cliOS'

$block = @"
$marker
function cli { & "$entry" @args }
"@

if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
    Write-Host "created $PROFILE"
}

$current = Get-Content -LiteralPath $PROFILE -Raw
if ($current -and $current.Contains($marker)) {
    Write-Host "cliOS is already installed in $PROFILE"
} else {
    Add-Content -LiteralPath $PROFILE -Value "`n$block"
    Write-Host "added the cli function to $PROFILE"
    Write-Host "open a new terminal, or run: . `$PROFILE"
}
