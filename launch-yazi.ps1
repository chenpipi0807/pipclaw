$env:PATH = 'C:\Program Files\Git\usr\bin;' + $env:PATH

$stateFile = "$HOME\.pipclaw\current-project.txt"

# 先删旧文件，等 pipclaw 写入新的项目路径（最多等 15 秒）
if (Test-Path $stateFile) { Remove-Item $stateFile }

$waited = 0
while (-not (Test-Path $stateFile) -and $waited -lt 30) {
    Start-Sleep -Milliseconds 500
    $waited++
}

if (Test-Path $stateFile) {
    $projectPath = (Get-Content $stateFile -Encoding UTF8).Trim()
    if (Test-Path $projectPath) {
        Set-Location $projectPath
    }
}

yazi
