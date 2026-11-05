@echo off
echo ========================================
echo  Building NSE OI Scanner Windows EXE
echo ========================================

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --noconfirm --windowed --name "NSE_OI_Scanner" ^
  --add-data "config;config" ^
  --add-data "ui;ui" ^
  --add-data "core;core" ^
  --hidden-import=loguru ^
  --hidden-import=core.logger ^
  --hidden-import=PySide6.QtCore ^
  --hidden-import=PySide6.QtGui ^
  --hidden-import=PySide6.QtWidgets ^
  --hidden-import=sqlalchemy ^
  --hidden-import=pandas ^
  --hidden-import=numpy ^
  --hidden-import=requests ^
  --hidden-import=websockets ^
  --collect-all=loguru ^
  --collect-all=PySide6 ^
  main.py

echo.
echo Build finished. EXE is in: dist\NSE_OI_Scanner\
pause
