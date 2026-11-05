@echo off
echo ========================================
echo  Building NSE OI Scanner (Windows)
echo ========================================

python -m pip install --upgrade pip
pip install PySide6 loguru pandas numpy SQLAlchemy requests websockets aiosqlite python-dateutil pytz plyer
pip install dhanhq
pip install pyinstaller

echo.
echo Verifying...
python -c "import PySide6; print('PySide6', PySide6.__version__)"
python -c "import loguru; print('loguru OK')"

echo.
echo Building (please wait)...
pyinstaller --noconfirm --clean NSE_OI_Scanner.spec

echo.
echo ========================================
echo  Done!
echo  Run: dist\NSE_OI_Scanner\NSE_OI_Scanner.exe
echo ========================================
dir dist\NSE_OI_Scanner
pause
