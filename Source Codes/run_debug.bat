@echo off
cd /d "%~dp0"
echo Starting VerseFlow with debug output...
python main.py > debug_output.log 2>&1
echo Process ended.
pause
