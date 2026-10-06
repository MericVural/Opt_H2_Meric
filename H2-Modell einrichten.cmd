@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-gui\Scripts\python.exe" (
  py -3.11 -m venv .venv-gui
  if errorlevel 1 goto failed
)
".venv-gui\Scripts\python.exe" -m pip install -r requirements-h2-gui.txt
if errorlevel 1 goto failed
".venv-gui\Scripts\python.exe" -B gui\restore_shared_data.py
if errorlevel 1 goto failed
echo Einrichtung abgeschlossen. Jetzt H2-Modell starten.cmd oeffnen.
pause
exit /b 0
:failed
echo Einrichtung fehlgeschlagen. Hinweise stehen in GUI_UEBERGABE.md.
pause
exit /b 1
