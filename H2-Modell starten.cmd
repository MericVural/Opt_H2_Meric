@echo off
setlocal
set "H2_GUI_PYTHON=%~dp0.venv-gui\Scripts\python.exe"
if not exist "%H2_GUI_PYTHON%" (
  echo Die lokale GUI-Umgebung fehlt: .venv-gui
  echo Hinweise stehen in H2-GUI-START.md und GUI_BEDIENUNGSANLEITUNG.md.
  pause
  exit /b 1
)
"%H2_GUI_PYTHON%" "%~dp0gui\start_local_gui.py" %*
if errorlevel 1 pause
