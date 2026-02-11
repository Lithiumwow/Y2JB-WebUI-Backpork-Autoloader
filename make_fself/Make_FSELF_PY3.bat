@echo off
echo.
echo PS5 Make Fake Self Script By EchoStretch
echo Requires LightningMods_ Updated Make Fself By Flatz
echo.

set "fself="make_fself.py""

cd /d %~1

FOR /R %%i IN ("*.sprx" "*.prx" "*.elf" "*.self" "*eboot.bin") DO (
echo Encrypting %%i...
echo.
python %fself% "%%i" "%%i.estemp"
REN "%%i" "%%~nxi.esbak"
echo.
)

echo.
echo Renaming Temporary Files...
echo.

FOR /R %%i IN (*.estemp) DO (
REN "%%i" "%%~ni"
)
pause
