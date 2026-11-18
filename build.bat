@echo off
title PyClean Pro - Compilador de Binarios e Instalador
cls
echo ========================================================
echo        PyClean Pro - Compilacion para Windows
echo ========================================================
echo.
echo Selecciona una opcion de compilacion:
echo.
echo  [1] Compilar Ejecutable Portable (PyCleanPro.exe)
echo  [2] Compilar Instalador Oficial Setup (PyCleanPro-Setup.exe)
echo  [3] Compilar Ambos (Portable + Instalador)
echo  [4] Salir
echo.
set /p opt="Opcion [1-4]: "

if "%opt%"=="1" goto build_exe
if "%opt%"=="2" goto build_setup
if "%opt%"=="3" goto build_all
if "%opt%"=="4" goto end
goto menu_end

:build_exe
echo.
python build_exe.py
goto menu_end

:build_setup
echo.
python build_installer.py
goto menu_end

:build_all
echo.
python build_exe.py
python build_installer.py
goto menu_end

:menu_end
echo.
pause
:end
