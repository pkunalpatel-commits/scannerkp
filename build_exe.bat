@echo off
echo ========================================
echo  Building NSE OI Scanner Windows EXE
echo ========================================

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Building folder version (recommended)...
pyinstaller --noconfirm --windowed --name "NSE_OI_Scanner" ^
  --add-data "config;config" ^
  --add-data "ui;ui" ^
  --add-data "core;core" ^
  --hidden-import=loguru ^
  --hidden-import=core.logger ^
  --hidden-import=PySide6 ^
  --hidden-import=PySide6.QtCore ^
  --hidden-import=PySide6.QtGui ^
  --hidden-import=PySide6.QtWidgets ^
  --collect-all=loguru ^
  --collect-all=PySide6 ^
  main.py

echo.
echo ========================================
echo  Build finished!
echo  Run: dist\NSE_OI_Scanner\NSE_OI_Scanner.exe
echo ========================================
pause
