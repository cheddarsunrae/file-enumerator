#requires -Version 5.1
<#
.SYNOPSIS
Recursively enumerates files with filetype, filename, and folder filters.

.DESCRIPTION
Exclusions always win. Multiple patterns within one filter category are OR.
Different include categories are AND. Folder filters match either an individual
folder component or the relative folder path beneath Root.

.EXAMPLE
.\Enumerate-Files.ps1 -Root 'C:\Data' -Format Both -Zip

.EXAMPLE
.\Enumerate-Files.ps1 -Root 'C:\Data' `
  -IncludeFileType pdf,docx `
  -ExcludeFolderName node_modules,'.git' `
  -ExcludeFileName '~$*','*.tmp' `
  -Format Both -ZipOnly
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Root,

    [Alias('IncludeExt', 'IncludeType')]
    [string[]]$IncludeFileType,

    [Alias('ExcludeExt', 'ExcludeType')]
    [string[]]$ExcludeFileType,

    [Alias('IncludeName')]
    [string[]]$IncludeFileName,

    [Alias('ExcludeName')]
    [string[]]$ExcludeFileName,

    [Alias('IncludeFolder')]
    [string[]]$IncludeFolderName,

    [Alias('ExcludeFolder')]
    [string[]]$ExcludeFolderName,

    [ValidateSet('Txt', 'Csv', 'Both')]
    [string]$Format = 'Both',

    [string]$OutputDirectory = (Get-Location).Path,

    [string]$BaseName,

    [ValidateSet('Full', 'Relative')]
    [string]$TxtPathMode = 'Full',

    [switch]$Zip,

    [switch]$ZipOnly,

    [switch]$FollowLinks,

    [switch]$CaseSensitive,

    [switch]$Quiet
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

function Expand-FilterValues {
    param([string[]]$Values)

    $expanded = [System.Collections.Generic.List[string]]::new()
    foreach ($rawValue in @($Values)) {
        if ([string]::IsNullOrWhiteSpace($rawValue)) {
            continue
        }
        foreach ($value in ($rawValue -split ',')) {
            $trimmed = $value.Trim()
            if (-not [string]::IsNullOrWhiteSpace($trimmed)) {
                $expanded.Add($trimmed)
            }
        }
    }
    return $expanded.ToArray()
}

function Normalize-Extension {
    param([string]$Value)

    $normalized = $Value.Trim()
    if ($normalized -in @('<none>', 'none', '[none]')) {
        return ''
    }
    if ($normalized.StartsWith('*.')) {
        $normalized = $normalized.Substring(1)
    }
    elseif ($normalized.StartsWith('*')) {
        $normalized = $normalized.Substring(1)
    }
    if ($normalized -and -not $normalized.StartsWith('.')) {
        $normalized = ".$normalized"
    }
    return $normalized
}

function Test-WildcardMatch {
    param(
        [string[]]$Candidates,
        [string[]]$Patterns,
        [bool]$UseCaseSensitive
    )

    foreach ($candidate in @($Candidates)) {
        foreach ($pattern in @($Patterns)) {
            if ($UseCaseSensitive) {
                if ($candidate -clike $pattern) {
                    return $true
                }
            }
            elseif ($candidate -like $pattern) {
                return $true
            }
        }
    }
    return $false
}

function Get-RelativePathPortable {
    param(
        [string]$BasePath,
        [string]$TargetPath
    )

    $baseFull = [System.IO.Path]::GetFullPath($BasePath).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
    $targetComparable = $targetFull.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    if ([string]::Equals($baseFull, $targetComparable, [System.StringComparison]::OrdinalIgnoreCase)) {
        return ''
    }
    $baseUri = [System.Uri]::new($baseFull + [System.IO.Path]::DirectorySeparatorChar)
    $targetUri = [System.Uri]::new($targetFull)
    $relativeUri = $baseUri.MakeRelativeUri($targetUri)
    return [System.Uri]::UnescapeDataString($relativeUri.ToString()).Replace('/', [System.IO.Path]::DirectorySeparatorChar)
}

function Get-FolderCandidates {
    param([string]$RelativeFolder)

    if ([string]::IsNullOrWhiteSpace($RelativeFolder) -or $RelativeFolder -eq '.') {
        return @()
    }
    $normalized = $RelativeFolder.Replace([System.IO.Path]::DirectorySeparatorChar, '/')
    $parts = $normalized -split '/'
    return @($normalized) + @($parts)
}

try {
    $resolvedRoot = (Resolve-Path -LiteralPath $Root).Path
    if (-not [System.IO.Directory]::Exists($resolvedRoot)) {
        throw "Root path is not a directory: $resolvedRoot"
    }

    $resolvedOutput = [System.IO.Path]::GetFullPath($OutputDirectory)
    [System.IO.Directory]::CreateDirectory($resolvedOutput) | Out-Null

    $includeTypesRaw = Expand-FilterValues -Values $IncludeFileType
    $excludeTypesRaw = Expand-FilterValues -Values $ExcludeFileType
    $includeNames = Expand-FilterValues -Values $IncludeFileName
    $excludeNames = Expand-FilterValues -Values $ExcludeFileName
    $includeFolders = Expand-FilterValues -Values $IncludeFolderName
    $excludeFolders = Expand-FilterValues -Values $ExcludeFolderName

    $includeTypes = @($includeTypesRaw | ForEach-Object { Normalize-Extension -Value $_ })
    $excludeTypes = @($excludeTypesRaw | ForEach-Object { Normalize-Extension -Value $_ })
    if (-not $CaseSensitive) {
        $includeTypes = @($includeTypes | ForEach-Object { $_.ToLowerInvariant() })
        $excludeTypes = @($excludeTypes | ForEach-Object { $_.ToLowerInvariant() })
    }

    if ($ZipOnly) {
        $Zip = $true
    }

    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    if ([string]::IsNullOrWhiteSpace($BaseName)) {
        $BaseName = "file_inventory_$timestamp"
    }
    if ([System.IO.Path]::GetFileName($BaseName) -ne $BaseName) {
        throw 'BaseName must be a file name, not a path.'
    }

    $excludedOutputPaths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($candidateOutput in @(
        (Join-Path $resolvedOutput "$BaseName.txt"),
        (Join-Path $resolvedOutput "$BaseName.csv"),
        (Join-Path $resolvedOutput "${BaseName}_errors.txt"),
        (Join-Path $resolvedOutput "$BaseName.zip")
    )) {
        [void]$excludedOutputPaths.Add([System.IO.Path]::GetFullPath($candidateOutput))
    }

    $records = [System.Collections.Generic.List[object]]::new()
    $errors = [System.Collections.Generic.List[string]]::new()
    $stack = [System.Collections.Generic.Stack[System.IO.DirectoryInfo]]::new()
    $stack.Push([System.IO.DirectoryInfo]::new($resolvedRoot))

    while ($stack.Count -gt 0) {
        $currentDirectory = $stack.Pop()
        $relativeFolder = Get-RelativePathPortable -BasePath $resolvedRoot -TargetPath $currentDirectory.FullName
        if ($relativeFolder -eq '.') {
            $relativeFolder = ''
        }
        $parentCandidates = Get-FolderCandidates -RelativeFolder $relativeFolder

        try {
            foreach ($childDirectory in $currentDirectory.EnumerateDirectories()) {
                $childRelative = Get-RelativePathPortable -BasePath $resolvedRoot -TargetPath $childDirectory.FullName
                $childCandidates = Get-FolderCandidates -RelativeFolder $childRelative

                if ($excludeFolders.Count -gt 0 -and (Test-WildcardMatch -Candidates $childCandidates -Patterns $excludeFolders -UseCaseSensitive $CaseSensitive.IsPresent)) {
                    continue
                }

                $isReparsePoint = ($childDirectory.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0
                if ($isReparsePoint -and -not $FollowLinks) {
                    continue
                }

                $stack.Push($childDirectory)
            }
        }
        catch {
            $errors.Add("DIRECTORY ERROR: $($currentDirectory.FullName): $($_.Exception.Message)")
        }

        try {
            foreach ($file in $currentDirectory.EnumerateFiles()) {
                try {
                    if ($excludedOutputPaths.Contains([System.IO.Path]::GetFullPath($file.FullName))) {
                        continue
                    }
                    $extension = $file.Extension
                    $comparableExtension = if ($CaseSensitive) { $extension } else { $extension.ToLowerInvariant() }

                    $extensionIsExcluded = if ($CaseSensitive) {
                        $excludeTypes -ccontains $comparableExtension
                    }
                    else {
                        $excludeTypes -contains $comparableExtension
                    }
                    $extensionIsIncluded = if ($CaseSensitive) {
                        $includeTypes -ccontains $comparableExtension
                    }
                    else {
                        $includeTypes -contains $comparableExtension
                    }

                    if ($excludeTypes.Count -gt 0 -and $extensionIsExcluded) {
                        continue
                    }
                    if ($includeTypes.Count -gt 0 -and -not $extensionIsIncluded) {
                        continue
                    }
                    if ($excludeNames.Count -gt 0 -and (Test-WildcardMatch -Candidates @($file.Name) -Patterns $excludeNames -UseCaseSensitive $CaseSensitive.IsPresent)) {
                        continue
                    }
                    if ($includeNames.Count -gt 0 -and -not (Test-WildcardMatch -Candidates @($file.Name) -Patterns $includeNames -UseCaseSensitive $CaseSensitive.IsPresent)) {
                        continue
                    }
                    if ($excludeFolders.Count -gt 0 -and (Test-WildcardMatch -Candidates $parentCandidates -Patterns $excludeFolders -UseCaseSensitive $CaseSensitive.IsPresent)) {
                        continue
                    }
                    if ($includeFolders.Count -gt 0 -and -not (Test-WildcardMatch -Candidates $parentCandidates -Patterns $includeFolders -UseCaseSensitive $CaseSensitive.IsPresent)) {
                        continue
                    }

                    $relativePath = Get-RelativePathPortable -BasePath $resolvedRoot -TargetPath $file.FullName
                    $relativePathNormalized = $relativePath.Replace([System.IO.Path]::DirectorySeparatorChar, '/')
                    $parentNormalized = $relativeFolder.Replace([System.IO.Path]::DirectorySeparatorChar, '/')
                    $isLink = ($file.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0

                    $records.Add([pscustomobject][ordered]@{
                        relative_path = $relativePathNormalized
                        full_path = $file.FullName
                        name = $file.Name
                        extension = $extension
                        parent_relative = $parentNormalized
                        size_bytes = $file.Length
                        modified_utc = $file.LastWriteTimeUtc.ToString('yyyy-MM-ddTHH:mm:ssZ')
                        is_symlink = $isLink
                    })
                }
                catch {
                    $errors.Add("FILE ERROR: $($file.FullName): $($_.Exception.Message)")
                }
            }
        }
        catch {
            $errors.Add("DIRECTORY FILE ENUMERATION ERROR: $($currentDirectory.FullName): $($_.Exception.Message)")
        }
    }

    $sortedRecords = @($records | Sort-Object -Property @{ Expression = { $_.relative_path.ToLowerInvariant() } })
    $generatedUtc = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    $generatedFiles = [System.Collections.Generic.List[string]]::new()

    if ($Format -in @('Txt', 'Both')) {
        $txtPath = Join-Path $resolvedOutput "$BaseName.txt"
        $lines = [System.Collections.Generic.List[string]]::new()
        $lines.Add("# Root: $resolvedRoot")
        $lines.Add("# Generated UTC: $generatedUtc")
        $lines.Add("# File count: $($sortedRecords.Count)")
        $lines.Add("# TXT path mode: $TxtPathMode")
        foreach ($record in $sortedRecords) {
            if ($TxtPathMode -eq 'Full') {
                $lines.Add([string]$record.full_path)
            }
            else {
                $lines.Add([string]$record.relative_path)
            }
        }
        [System.IO.File]::WriteAllLines($txtPath, $lines.ToArray(), [System.Text.UTF8Encoding]::new($false))
        $generatedFiles.Add($txtPath)
    }

    if ($Format -in @('Csv', 'Both')) {
        $csvPath = Join-Path $resolvedOutput "$BaseName.csv"
        if ($sortedRecords.Count -gt 0) {
            $sortedRecords | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8
        }
        else {
            $csvHeader = '"relative_path","full_path","name","extension","parent_relative","size_bytes","modified_utc","is_symlink"' + [Environment]::NewLine
            [System.IO.File]::WriteAllText($csvPath, $csvHeader, [System.Text.UTF8Encoding]::new($true))
        }
        $generatedFiles.Add($csvPath)
    }

    if ($errors.Count -gt 0) {
        $errorsPath = Join-Path $resolvedOutput "${BaseName}_errors.txt"
        [System.IO.File]::WriteAllLines($errorsPath, $errors.ToArray(), [System.Text.UTF8Encoding]::new($false))
        $generatedFiles.Add($errorsPath)
    }

    $zipPath = $null
    if ($Zip) {
        $zipPath = Join-Path $resolvedOutput "$BaseName.zip"
        if (Test-Path -LiteralPath $zipPath) {
            Remove-Item -LiteralPath $zipPath -Force
        }
        $filesToArchive = $generatedFiles.ToArray()
        Compress-Archive -LiteralPath $filesToArchive -DestinationPath $zipPath -CompressionLevel Optimal
        if ($ZipOnly) {
            foreach ($generatedFile in $generatedFiles) {
                Remove-Item -LiteralPath $generatedFile -Force
            }
        }
    }

    if (-not $Quiet) {
        Write-Host "Root: $resolvedRoot"
        Write-Host "Files matched: $($sortedRecords.Count)"
        Write-Host "Errors: $($errors.Count)"
        if (-not $ZipOnly) {
            foreach ($generatedFile in $generatedFiles) {
                Write-Host "Created: $generatedFile"
            }
        }
        if ($null -ne $zipPath) {
            Write-Host "Created: $zipPath"
        }
    }

    if ($errors.Count -gt 0) {
        $global:LASTEXITCODE = 2
        return
    }
    $global:LASTEXITCODE = 0
    return
}
catch {
    [Console]::Error.WriteLine("ERROR: $($_.Exception.Message)")
    $global:LASTEXITCODE = 1
    return
}
