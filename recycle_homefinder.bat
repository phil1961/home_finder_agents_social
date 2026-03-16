@echo off
REM v20260309-1
echo Recycling HomeFinder app pool...
%windir%\system32\inetsrv\appcmd recycle apppool /apppool.name:"HomeFinderAgents"
if %errorlevel% == 0 (
    echo.
    echo SUCCESS - HomeFinderAgents recycled.
) else (
    echo.
    echo FAILED - Try running as Administrator.
)
echo.
pause
