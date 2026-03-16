# v20260309-1
$projectPath = "D:\Projects\home_finder_agents"
$appPoolUser = "IIS AppPool\HomeFinderAgents"

if (-not (Test-Path $projectPath)) {
    Write-Error "Path not found: $projectPath"
    exit 1
}

Write-Host "Setting permissions on: $projectPath" -ForegroundColor Cyan
Write-Host "App pool identity:      $appPoolUser" -ForegroundColor Cyan

$acl  = Get-Acl $projectPath
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $appPoolUser,
    "ReadAndExecute",
    "ContainerInherit,ObjectInherit",
    "None",
    "Allow"
)
$acl.SetAccessRule($rule)
Set-Acl -Path $projectPath -AclObject $acl
Write-Host "OK - ReadAndExecute granted on project folder" -ForegroundColor Green

$instancePath = Join-Path $projectPath "instance"
if (Test-Path $instancePath) {
    $acl2  = Get-Acl $instancePath
    $rule2 = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $appPoolUser,
        "Modify",
        "ContainerInherit,ObjectInherit",
        "None",
        "Allow"
    )
    $acl2.SetAccessRule($rule2)
    Set-Acl -Path $instancePath -AclObject $acl2
    Write-Host "OK - Modify granted on instance folder (SQLite write access)" -ForegroundColor Green
} else {
    Write-Host "WARN - instance folder not found, create it before first run" -ForegroundColor Yellow
}

Import-Module WebAdministration -ErrorAction SilentlyContinue
if (Get-Module WebAdministration) {
    Write-Host "Recycling app pool HomeFinderAgents..." -ForegroundColor Cyan
    Restart-WebAppPool -Name "HomeFinderAgents"
    Write-Host "OK - App pool recycled" -ForegroundColor Green
} else {
    Write-Host "WARN - Recycle the HomeFinderAgents pool manually in IIS Manager" -ForegroundColor Yellow
}

Write-Host "Done. Try the site again." -ForegroundColor Green
