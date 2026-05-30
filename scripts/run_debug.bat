@echo off
setlocal

:: Root of the src tree
set SRC=%~dp0..\src

:: Add all subdirectories to PYTHONPATH so bare imports resolve
set PYTHONPATH=%SRC%;%SRC%\ui;%SRC%\core;%SRC%\display;%SRC%\db;%SRC%\ndi;%SRC%\utils

echo Starting VerseFlow with debug output...
python "%SRC%\main.py"
echo Process ended.
pause
endlocal
