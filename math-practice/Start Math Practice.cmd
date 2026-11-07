@echo off
setlocal
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 "%~dp0runtime\launch_math_practice.py"
goto done
:use_python
python "%~dp0runtime\launch_math_practice.py"
:done
if not errorlevel 1 exit /b 0
echo.
echo Math Practice could not start. The error above explains what to check.
pause
exit /b 1
