@echo off
setlocal
cd /d "%~dp0"

echo.
echo === Kaggriculture TOP49 replay downloader ===
echo Using the same Python interpreter that has Kaggle installed.
echo.

python -c "import kaggle; print('Kaggle Python package:', kaggle.__file__)"
if errorlevel 1 (
    echo.
    echo Kaggle package is not installed for this Python.
    echo Run:
    echo   python -m pip install -U kaggle
    echo.
    pause
    exit /b 1
)

python download_top49_replays.py --top-n 12 --replays-per-team 9 --delay 0.2
if errorlevel 1 (
    echo.
    echo Download failed.
    echo The script is resumable; fix the problem and run it again.
    pause
    exit /b 1
)

echo.
echo Finished. TOP50.zip should now be in this folder.
pause
