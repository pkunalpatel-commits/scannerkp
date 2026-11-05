@echo off
echo ========================================
echo  Building NSE OI Scanner (with .spec)
echo ========================================

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Verifying packages...
python -c "import PySide6; print('PySide6', PySide6.__version__)"
python -c "import loguru; print('loguru OK')"

echo.
echo Building (this may take a few minutes)...
pyinstaller --noconfirm --clean NSE_OI_Scanner.spec

echo.
echo ========================================
echo  Done! Run:
echo  dist\NSE_OI_Scanner\NSE_OI_Scanner.exe
echo ========================================
dir dist\NSE_OI_Scanner
pause
