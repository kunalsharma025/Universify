@echo off
cd /d %~dp0
if not exist Universify.spec (
  cd ..
  if not exist Universify.spec (
    echo Put build_exe.bat in the main flac player folder, next to main.py, not in src.
    pause
    exit /b 1
  )
)
echo Building Universify.exe - this takes a few minutes, do not close this window.
python -m pip install pyinstaller
if errorlevel 1 (
  echo pip install pyinstaller failed. Check your internet and try again.
  pause
  exit /b 1
)
python -m PyInstaller Universify.spec --clean --noconfirm
if errorlevel 1 (
  echo Build failed. Scroll up for the red error.
  pause
  exit /b 1
)
if exist dist\Universify.exe (
  echo.
  echo Done - Universify.exe is in the dist folder.
  echo IMPORTANT: VLC app must stay installed on this PC, or songs will not play.
  echo Your music folders are saved in library.json next to the exe.
) else (
  echo Build finished but dist\Universify.exe was not found.
)
pause
