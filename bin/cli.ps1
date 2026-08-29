#!/usr/bin/env pwsh
# cliOS - PowerShell frontend. Reads config/cli.json and executes the resolved action.
# The bash frontend (cli) must stay behaviourally identical.

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $PSCommandPath
$script:Config = if ($env:CLIOS_CONFIG) { $env:CLIOS_CONFIG } else { Join-Path $ScriptDir '../config/cli.json' }
$script:DryRun = $false
$script:RawArgs = $args
$script:Frontend = 'pwsh'
$script:Platform = if ($IsWindows) { 'windows' } elseif ($IsMacOS) { 'darwin' } else { 'linux' }

# --------------------------------------------------------------------- log ---

function Write-UsageLog([int]$Status) {
    if ($script:DryRun) { return }
    try {
        if ($script:Spec.ContainsKey('log') -and $script:Spec.log -eq $false) { return }
        $path = if ($script:Spec.ContainsKey('log_path')) { $script:Spec.log_path } else { '${HOME}/.cliOS/history.txt' }
        $path = Expand-Roots $path
        $dir = Split-Path -Parent $path
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
        $now = Get-Date
        $stamp = $now.ToString('yyyy-MM-ddTHH:mm:ss') + $now.ToString('zzz').Replace(':', '')
        $machine = if ($env:COMPUTERNAME) { $env:COMPUTERNAME } else { [System.Net.Dns]::GetHostName() }
        $line = @($stamp, $machine, $script:Frontend, $Status, "cli $($script:RawArgs -join ' ')") -join "`t"
        # Explicit LF: Add-Content would write CRLF here and the bash frontend LF.
        [System.IO.File]::AppendAllText($path, "$line`n", (New-Object System.Text.UTF8Encoding($false)))
    } catch {}
}

function Complete-Run([int]$Status) {
    Write-UsageLog $Status
    exit $Status
}

function Stop-WithError([string]$Message) {
    [Console]::Error.WriteLine($Message)
    Complete-Run 1
}

# ------------------------------------------------------------------- roots ---

function Expand-Roots([string]$Value) {
    while ($Value -match '\$\{([A-Z_]+)\}') {
        $name = $Matches[1]
        $token = '${' + $name + '}'
        if ($name -eq 'HOME') {
            $resolved = $script:HomePath
        } else {
            $root = $script:Spec.roots[$name]
            $resolved = $null
            if ($root) {
                if ($root.ContainsKey($script:Platform)) { $resolved = $root[$script:Platform] }
                elseif ($root.ContainsKey('default')) { $resolved = $root['default'] }
            }
            if (-not $resolved) {
                Stop-WithError "root $name is not configured on this machine ($($script:Platform))"
            }
            $resolved = $resolved.Replace('${HOME}', $script:HomePath)
        }
        $Value = $Value.Replace($token, $resolved)
    }
    return $Value
}

function ConvertTo-NativePath([string]$Value) {
    if ($script:Platform -eq 'windows') { return $Value.Replace('/', '\') }
    return $Value
}

# ----------------------------------------------------------------- openers ---

function Open-Url([string]$Url) {
    if ($script:Platform -eq 'darwin') { & open $Url }
    elseif ($script:Platform -eq 'windows') { Start-Process $Url }
    else { & xdg-open $Url }
}

function Open-ItemPath([string]$Target) {
    $native = ConvertTo-NativePath $Target
    if (-not (Test-Path -LiteralPath $native)) { Stop-WithError "path does not exist: $Target" }
    $isDir = (Get-Item -LiteralPath $native).PSIsContainer
    if ($script:Platform -eq 'windows') {
        if ($isDir) { Start-Process explorer.exe -ArgumentList "`"$native`"" }
        else { Start-Process explorer.exe -ArgumentList "/select,`"$native`"" }
    } elseif ($script:Platform -eq 'darwin') {
        if ($isDir) { & open $native } else { & open -R $native }
    } else {
        & xdg-open (Split-Path -Parent $native)
    }
}

# ----------------------------------------------------------------- listing ---

function Get-SortedKeys($Table) {
    $keys = [string[]]@($Table.Keys)
    [Array]::Sort($keys, [StringComparer]::Ordinal)
    return $keys
}

function Show-Table([string]$TableName, [string]$Verb, [switch]$ToStderr) {
    $lines = @("try one of the following:")
    foreach ($key in Get-SortedKeys $script:Spec[$TableName]) { $lines += "  cli $Verb $key" }
    foreach ($line in $lines) {
        if ($ToStderr) { [Console]::Error.WriteLine($line) } else { Write-Output $line }
    }
}

function Show-Verbs([switch]$ToStderr) {
    $lines = @("cliOS - commands:")
    foreach ($key in Get-SortedKeys $script:Spec.commands) {
        $help = $script:Spec.commands[$key].help
        $lines += "  cli $key - $help"
    }
    foreach ($line in $lines) {
        if ($ToStderr) { [Console]::Error.WriteLine($line) } else { Write-Output $line }
    }
}

# ----------------------------------------------------------------- capture ---

function Add-LineToSection([string]$File, [string]$After, [string]$At, [string]$Line) {
    # Split on "`n" only so each line keeps its own trailing "`r": the file may be
    # mixed, and the bash frontend preserves endings line by line.
    $raw = [System.IO.File]::ReadAllText($File)
    $hadTrailing = $raw.EndsWith("`n")
    $lines = [System.Collections.ArrayList]@($raw -split "`n")
    if ($hadTrailing -and $lines.Count -gt 0) { $lines.RemoveAt($lines.Count - 1) }

    $eol = ''
    $headingIndex = -1
    $sectionEnd = -1
    $level = 0
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $text = $lines[$i].TrimEnd("`r")
        if ($text -ne $lines[$i]) { $eol = "`r" }
        if ($headingIndex -lt 0) {
            if ($text.StartsWith($After)) {
                $headingIndex = $i
                $level = ($text.Length - $text.TrimStart('#').Length)
            }
        } elseif ($sectionEnd -lt 0 -and $text.StartsWith('#')) {
            $thisLevel = ($text.Length - $text.TrimStart('#').Length)
            if ($thisLevel -le $level) { $sectionEnd = $i }
        }
    }
    if ($headingIndex -lt 0) { return $false }

    if ($At -eq 'start') {
        $target = $headingIndex
    } else {
        $target = if ($sectionEnd -ge 0) { $sectionEnd - 1 } else { $lines.Count - 1 }
        while ($target -gt $headingIndex -and [string]::IsNullOrWhiteSpace($lines[$target])) { $target-- }
    }
    $lines.Insert($target + 1, "$Line$eol") | Out-Null
    $out = ($lines -join "`n")
    if ($hadTrailing) { $out += "`n" }
    [System.IO.File]::WriteAllText($File, $out, (New-Object System.Text.UTF8Encoding($false)))
    return $true
}

function Invoke-Capture([string]$Id, [string[]]$Rest) {
    $text = ($Rest -join ' ')
    if (-not $text) { Stop-WithError "cli $Id needs some text" }
    $spec = $script:Spec.captures[$Id]
    if (-not $spec) { Stop-WithError "unknown capture: $Id" }

    $file = $spec.file.Replace('{date}', (Get-Date -Format 'yyyy-MM-dd'))
    $file = Expand-Roots $file
    $at = if ($spec.ContainsKey('at')) { $spec.at } else { 'start' }
    $isTask = $spec.ContainsKey('task') -and $spec.task
    $line = "$(Get-Date -Format 'HH:mm') $text"
    if ($isTask) { $line = "- [ ] $line" }

    if ($script:DryRun) {
        Write-Output "capture $Id"
        Write-Output "  file:   $file"
        Write-Output "  after:  $($spec.after) ($at)"
        Write-Output "  line:   $line"
        Complete-Run 0
    }

    $native = ConvertTo-NativePath $file
    if (-not (Test-Path -LiteralPath $native)) {
        $dir = Split-Path -Parent $native
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
        if ($spec.ContainsKey('template') -and $spec.template) {
            $template = ConvertTo-NativePath (Expand-Roots $spec.template)
            if (-not (Test-Path -LiteralPath $template)) { Stop-WithError "template not found: $template" }
            Copy-Item -LiteralPath $template -Destination $native
        } else {
            New-Item -ItemType File -Path $native | Out-Null
        }
    }

    if (-not (Add-LineToSection $native $spec.after $at $line)) {
        Stop-WithError "heading '$($spec.after)' not found in $file"
    }
    Write-Output $line
    Write-Output "  -> $file"
}

# ------------------------------------------------------------ config writes ---

function ConvertTo-CanonicalJson($Value, [int]$Indent = 0) {
    # Byte for byte equivalent of `jq -S --indent 2`.
    $pad = ' ' * $Indent
    $padInner = ' ' * ($Indent + 2)
    if ($null -eq $Value) { return 'null' }
    if ($Value -is [bool]) { return $(if ($Value) { 'true' } else { 'false' }) }
    if ($Value -is [int] -or $Value -is [long] -or $Value -is [double] -or $Value -is [decimal]) {
        return $Value.ToString([System.Globalization.CultureInfo]::InvariantCulture)
    }
    if ($Value -is [string]) { return ConvertTo-JsonString $Value }
    if ($Value -is [System.Collections.IDictionary]) {
        $keys = Get-SortedKeys $Value
        if ($keys.Count -eq 0) { return '{}' }
        $parts = foreach ($key in $keys) {
            "$padInner$(ConvertTo-JsonString $key): $(ConvertTo-CanonicalJson $Value[$key] ($Indent + 2))"
        }
        return "{`n" + ($parts -join ",`n") + "`n$pad}"
    }
    if ($Value -is [System.Collections.IEnumerable]) {
        $items = @($Value)
        if ($items.Count -eq 0) { return '[]' }
        $parts = foreach ($item in $items) { "$padInner$(ConvertTo-CanonicalJson $item ($Indent + 2))" }
        return "[`n" + ($parts -join ",`n") + "`n$pad]"
    }
    return ConvertTo-JsonString ([string]$Value)
}

function ConvertTo-JsonString([string]$Value) {
    $sb = [System.Text.StringBuilder]::new()
    [void]$sb.Append('"')
    foreach ($ch in $Value.ToCharArray()) {
        switch ($ch) {
            '"' { [void]$sb.Append('\"'); continue }
            '\' { [void]$sb.Append('\\'); continue }
            "`b" { [void]$sb.Append('\b'); continue }
            "`f" { [void]$sb.Append('\f'); continue }
            "`n" { [void]$sb.Append('\n'); continue }
            "`r" { [void]$sb.Append('\r'); continue }
            "`t" { [void]$sb.Append('\t'); continue }
            default {
                if ([int]$ch -lt 32) { [void]$sb.Append('\u{0:x4}' -f [int]$ch) }
                else { [void]$sb.Append($ch) }
            }
        }
    }
    [void]$sb.Append('"')
    return $sb.ToString()
}

function Save-Spec {
    $json = (ConvertTo-CanonicalJson $script:Spec) + "`n"
    [System.IO.File]::WriteAllText($script:Config, $json, (New-Object System.Text.UTF8Encoding($false)))
}

function Resolve-TableName([string]$Name) {
    switch ($Name) {
        { $_ -in 'link', 'links' } { return 'links' }
        { $_ -in 'folder', 'folders' } { return 'folders' }
        default { Stop-WithError "unknown table '$Name', expected link or folder" }
    }
}

function Invoke-ConfigSet([string[]]$Rest) {
    if ($Rest.Count -lt 3) { Stop-WithError 'usage: cli set link|folder <key> <value>' }
    $table = Resolve-TableName $Rest[0]
    $key = $Rest[1]
    $value = $Rest[2]
    if ($script:DryRun) {
        Write-Output "set $table.$key = $value"
        Complete-Run 0
    }
    $script:Spec[$table][$key] = $value
    Save-Spec
    Write-Output "set $table $key -> $value"
}

function Invoke-ConfigRemove([string[]]$Rest) {
    if ($Rest.Count -lt 2) { Stop-WithError 'usage: cli rm link|folder <key>' }
    $table = Resolve-TableName $Rest[0]
    $key = $Rest[1]
    if (-not $script:Spec[$table].ContainsKey($key)) {
        [Console]::Error.WriteLine("no such key '$key' in $table")
        Show-Table $table ($table -replace 's$', '') -ToStderr
        Complete-Run 1
    }
    if ($script:DryRun) {
        Write-Output "rm $table.$key"
        Complete-Run 0
    }
    $script:Spec[$table].Remove($key)
    Save-Spec
    Write-Output "removed $table $key"
}

# ----------------------------------------------------------------- actions ---

function Invoke-Lookup($Action, [string[]]$Rest) {
    $table = $Action.table
    $verb = $table -replace 's$', ''
    if ($Rest.Count -eq 0) {
        Show-Table $table $verb
        Complete-Run 1
    }
    $key = $Rest[0]
    if (-not $script:Spec[$table].ContainsKey($key)) {
        [Console]::Error.WriteLine("no such $verb '$key'")
        Show-Table $table $verb -ToStderr
        Complete-Run 1
    }
    $value = $script:Spec[$table][$key]
    if ($Action.as -eq 'url') {
        if ($script:DryRun) {
            Write-Output "url $value"
            Complete-Run 0
        }
        Open-Url $value
        Write-Output $value
    } else {
        $value = Expand-Roots $value
        if ($script:DryRun) {
            Write-Output "path $value"
            Complete-Run 0
        }
        Open-ItemPath $value
        Write-Output $value
    }
}

function Invoke-Search($Action, [string[]]$Rest) {
    $table = $Action.table
    if ($Rest.Count -eq 0) {
        [Console]::Error.WriteLine('usage: cli search [vertical] <query>')
        [Console]::Error.WriteLine('verticals:')
        foreach ($key in Get-SortedKeys $script:Spec[$table]) { [Console]::Error.WriteLine("  $key") }
        Complete-Run 1
    }
    $vertical = $Action.default
    if ($script:Spec[$table].ContainsKey($Rest[0])) {
        $vertical = $Rest[0]
        $Rest = @($Rest | Select-Object -Skip 1)
    }
    if ($Rest.Count -eq 0) { Stop-WithError "cli search $vertical needs a query" }
    $query = [uri]::EscapeDataString(($Rest -join ' '))
    $url = $script:Spec[$table][$vertical].Replace('{query}', $query)
    if ($script:DryRun) {
        Write-Output "url $url"
        Complete-Run 0
    }
    Open-Url $url
    Write-Output $url
}

function Invoke-Code($Action, [string[]]$Rest) {
    if ($Rest.Count -eq 0) { Stop-WithError 'usage: cli code <project>' }
    $root = Expand-Roots $Action.root
    $project = $Rest[0]
    $path = "$root/$project"
    if ($script:DryRun) {
        Write-Output "code $path"
        Complete-Run 0
    }
    $native = ConvertTo-NativePath $path
    if (-not (Test-Path -LiteralPath $native)) {
        Write-Output "$path does not exist"
        $url = $Action.clone.Replace('{1}', $project)
        $reply = Read-Host "clone $url ? [y/N]"
        if ($reply -ne 'y' -and $reply -ne 'Y') { Complete-Run 1 }
        Push-Location (ConvertTo-NativePath $root)
        try { & git clone $url } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) { Complete-Run $LASTEXITCODE }
    }
    & code $native
    Write-Output $path
}

function Invoke-Exec($Action, [string[]]$Rest) {
    $cwd = Expand-Roots $Action.cwd
    $argv = foreach ($part in $Action.argv) {
        $filled = $part
        for ($i = 0; $i -lt $Rest.Count; $i++) { $filled = $filled.Replace("{$($i + 1)}", $Rest[$i]) }
        $filled
    }
    if (($argv -join ' ') -like '*{1}*') { Stop-WithError "usage: cli $($script:RawArgs[0]) <name>" }
    if ($script:DryRun) {
        Write-Output "exec $($argv -join ' ') (cwd $cwd)"
        Complete-Run 0
    }
    Push-Location (ConvertTo-NativePath $cwd)
    try { & $argv[0] @($argv | Select-Object -Skip 1) } finally { Pop-Location }
    Complete-Run $LASTEXITCODE
}

function Invoke-Action($Action, [string[]]$Rest) {
    switch ($Action.type) {
        'lookup' { Invoke-Lookup $Action $Rest }
        'search' { Invoke-Search $Action $Rest }
        'code' { Invoke-Code $Action $Rest }
        'exec' { Invoke-Exec $Action $Rest }
        'capture' { Invoke-Capture $Action.id $Rest }
        'config-set' { Invoke-ConfigSet $Rest }
        'config-rm' { Invoke-ConfigRemove $Rest }
        default { Stop-WithError "unknown action type: $($Action.type)" }
    }
}

# -------------------------------------------------------------------- main ---

$script:HomePath = if ($env:HOME) { $env:HOME } else { $env:USERPROFILE }
$script:HomePath = $script:HomePath.Replace('\', '/')

if (-not (Test-Path -LiteralPath $script:Config)) {
    [Console]::Error.WriteLine("config not found: $($script:Config)")
    exit 1
}
$script:Spec = Get-Content -LiteralPath $script:Config -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable

$parsed = @()
foreach ($arg in $args) {
    if ($arg -eq '--dry-run') { $script:DryRun = $true }
    elseif ($arg -eq '-h') { $parsed += '--help' }
    else { $parsed += $arg }
}

if ($parsed.Count -eq 0 -or $parsed[0] -eq '--help') {
    Show-Verbs
    Complete-Run 0
}

$verb = $parsed[0]
$rest = @($parsed | Select-Object -Skip 1)

$node = $null
foreach ($key in Get-SortedKeys $script:Spec.commands) {
    $candidate = $script:Spec.commands[$key]
    $aliases = if ($candidate.ContainsKey('aliases')) { $candidate.aliases } else { @() }
    if ($key -eq $verb -or $aliases -contains $verb) { $node = $candidate; break }
}
if (-not $node) {
    [Console]::Error.WriteLine("no such command '$verb'")
    Show-Verbs -ToStderr
    Complete-Run 1
}
if ($rest.Count -gt 0 -and $rest[0] -eq '--help') {
    Write-Output "cli $verb - $($node.help)"
    Complete-Run 0
}

Invoke-Action $node.action $rest
Complete-Run 0
